#!/usr/bin/env python3
"""StoryScro deterministic PDF ingestion.

Extracts source-grounded layout/content into a renderer-independent evidence package.
No editorial summarisation is performed here.
"""
from __future__ import annotations

import argparse
import collections
import colorsys
import hashlib
import io
import json
import math
from pathlib import Path
import re
import statistics
import unicodedata
from typing import Any

import fitz  # PyMuPDF
from PIL import Image

VERSION = "0.2.0"

BULLET_RE = re.compile(r"^\s*(?:[•·▪◦‣⁃*-]|(?:\d{1,2}|[A-Za-z])[.)])\s+")
NUMBER_RE = re.compile(
    r"(?<![\w])(?:\d{1,3}(?:[ .\u202f]\d{3})+|\d+(?:[,.]\d+)?)"
    r"(?:\s*(?:%|€|EUR|USD|GBP|k€|K€|M€|bn|million(?:s)?|milliard(?:s)?|km²|km2|km|m²|m2|m|cm|mm|°C|tCO2e?|MtCO2e?|ktCO2e?|kg|g|MW|GW|kW|MWh|GWh|TWh|ha|jours?|semaines?|mois|ans?)(?![A-Za-zÀ-ÿ]))?",
    re.I,
)
FIGURE_CAPTION_RE = re.compile(r"^\s*(?:figure|fig\.?|graphique|chart|source\s*:|tableau|table\s+\d+)", re.I)
QUOTE_MARKS = ('«', '»', '“', '”', '"')


def norm_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    return re.sub(r"\s+", " ", text).strip()


def norm_margin_key(text: str) -> str:
    text = norm_text(text).lower()
    text = re.sub(r"\d+", "#", text)
    return text


def bbox_list(bbox) -> list[float]:
    return [round(float(x), 2) for x in bbox]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def image_dhash(data: bytes, size: int = 8) -> str | None:
    try:
        img = Image.open(io.BytesIO(data)).convert("L").resize((size + 1, size))
        px = list(img.get_flattened_data()) if hasattr(img, "get_flattened_data") else list(img.getdata())
        bits = []
        for y in range(size):
            row = y * (size + 1)
            for x in range(size):
                bits.append(1 if px[row + x] > px[row + x + 1] else 0)
        value = 0
        for bit in bits:
            value = (value << 1) | bit
        return f"{value:0{size*size//4}x}"
    except Exception:
        return None


def rgb_hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(v))) for v in rgb)


def color_metrics(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    r, g, b = (v / 255.0 for v in rgb)
    h, sat, val = colorsys.rgb_to_hsv(r, g, b)
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return sat, val, lum


def infer_design_profile(doc: fitz.Document, raw_pages: list[dict[str, Any]]) -> dict[str, Any]:
    """Infer source visual identity without editorial interpretation.

    The profile is deliberately descriptive: source fonts, text colours and a
    small palette sampled from representative rendered pages. The planner can
    preserve or adapt these cues, but ingestion does not decide the final theme.
    """
    font_counts = collections.Counter()
    text_colors = collections.Counter()
    for page in raw_pages:
        for block in page.get("blocks", []):
            for span in block.get("spans", []):
                n = max(1, len((span.get("text") or "").strip()))
                if span.get("font"):
                    font_counts[span["font"]] += n
                value = int(span.get("color", 0)) & 0xFFFFFF
                text_colors[f"#{value:06x}"] += n

    page_scores = []
    for page in raw_pages:
        vector_count = sum(1 for x in page.get("derived", []) if x.get("type") == "vector_region_candidate")
        score = float(page.get("image_area_ratio") or 0) * 3 + min(vector_count, 6) * .35
        page_scores.append((score, page["number"]))
    sample_pages = []
    for page_num in [1, 2, 3, 4]:
        if page_num <= len(raw_pages) and page_num not in sample_pages:
            sample_pages.append(page_num)
    for _, page_num in sorted(page_scores, reverse=True):
        if page_num not in sample_pages:
            sample_pages.append(page_num)
        if len(sample_pages) >= 8:
            break

    palette_counts = collections.Counter()
    for page_num in sample_pages:
        try:
            page = doc[page_num - 1]
            pix = page.get_pixmap(matrix=fitz.Matrix(.38, .38), colorspace=fitz.csRGB, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            img.thumbnail((320, 320))
            q = img.quantize(colors=12, method=Image.Quantize.MEDIANCUT)
            palette = q.getpalette() or []
            for count, idx in q.getcolors(maxcolors=256) or []:
                base = idx * 3
                if base + 2 >= len(palette):
                    continue
                rgb = tuple(palette[base:base + 3])
                # Quantise slightly so near-identical antialias colours merge.
                rgb = tuple(int(round(v / 8) * 8) if v < 252 else 255 for v in rgb)
                palette_counts[rgb_hex(rgb)] += int(count)
        except Exception:
            continue

    palette = []
    for hx, count in palette_counts.most_common(24):
        rgb = tuple(int(hx[i:i+2], 16) for i in (1, 3, 5))
        sat, val, lum = color_metrics(rgb)
        if lum > .965 and sat < .06:
            role = "background"
        elif lum < .16 and sat < .18:
            role = "ink"
        elif sat > .34:
            role = "accent"
        else:
            role = "neutral"
        palette.append({"hex": hx, "weight": count, "role_guess": role, "saturation": round(sat, 3), "luminance": round(lum, 3)})

    nonwhite = [c for c in palette if c["role_guess"] != "background"]
    accents = sorted([c for c in nonwhite if c["saturation"] >= .28], key=lambda c: (c["weight"] * (.45 + c["saturation"])), reverse=True)
    darks = sorted([c for c in nonwhite if c["luminance"] <= .42], key=lambda c: c["weight"], reverse=True)
    backgrounds = sorted([c for c in palette if c["role_guess"] == "background"], key=lambda c: c["weight"], reverse=True)
    text_ranked = [{"hex": hx, "character_count": n} for hx, n in text_colors.most_common(12)]
    primary = (darks[0]["hex"] if darks else (accents[0]["hex"] if accents else "#222222"))
    text_accent_candidates = []
    for item in text_ranked:
        hx = item["hex"]
        rgb = tuple(int(hx[i:i+2], 16) for i in (1, 3, 5))
        sat, val, lum = color_metrics(rgb)
        if sat >= .45 and lum >= .12 and hx.lower() != primary.lower():
            text_accent_candidates.append((item["character_count"] * sat, hx))
    accent = max(text_accent_candidates, default=(0, accents[0]["hex"] if accents else primary))[1]
    background = (backgrounds[0]["hex"] if backgrounds else "#ffffff")
    text = text_ranked[0]["hex"] if text_ranked else primary

    return {
        "sample_pages": sample_pages,
        "source_fonts": [{"name": name, "character_count": n} for name, n in font_counts.most_common(12)],
        "text_colors": text_ranked,
        "page_palette": palette[:12],
        "suggested_tokens": {
            "primary": primary,
            "accent": accent,
            "background": background,
            "text": text,
        },
        "status": "descriptive_source_profile",
    }


def detect_language(text: str) -> str:
    words = re.findall(r"[A-Za-zÀ-ÿ']+", text.lower())
    if not words:
        return "und"
    fr = {"le", "la", "les", "de", "des", "du", "un", "une", "et", "pour", "dans", "avec", "sur", "est", "sont", "que", "qui", "au", "aux", "par", "ce", "cette"}
    en = {"the", "a", "an", "of", "and", "to", "in", "for", "with", "on", "is", "are", "that", "which", "by", "this", "from", "as"}
    f = sum(w in fr for w in words)
    e = sum(w in en for w in words)
    if f >= max(3, e * 1.4):
        return "fr"
    if e >= max(3, f * 1.4):
        return "en"
    return "und"


def span_is_bold(span: dict[str, Any]) -> bool:
    font = (span.get("font") or "").lower()
    return "bold" in font or "black" in font or "heavy" in font or bool(int(span.get("flags", 0)) & 16)


def text_block_from_raw(block: dict[str, Any], page_num: int, block_index: int) -> dict[str, Any] | None:
    if block.get("type") != 0:
        return None
    spans = []
    lines_text = []
    for line in block.get("lines", []):
        line_parts = []
        for s in line.get("spans", []):
            txt = s.get("text", "")
            if txt:
                line_parts.append(txt)
            if txt.strip():
                spans.append({
                    "text": txt,
                    "bbox": bbox_list(s.get("bbox", (0, 0, 0, 0))),
                    "font": s.get("font"),
                    "size": round(float(s.get("size", 0)), 2),
                    "flags": int(s.get("flags", 0)),
                    "bold": span_is_bold(s),
                    "color": int(s.get("color", 0)),
                })
        if line_parts:
            lines_text.append("".join(line_parts))
    text = norm_text(" ".join(lines_text))
    if not text:
        return None
    sizes = [s["size"] for s in spans]
    char_weighted = []
    for s in spans:
        char_weighted.extend([s["size"]] * max(1, len(s["text"].strip())))
    return {
        "id": f"p{page_num}-b{block_index}",
        "type": "text_block",
        "page": page_num,
        "bbox": bbox_list(block.get("bbox", (0, 0, 0, 0))),
        "text": text,
        "raw_lines": [norm_text(x) for x in lines_text if norm_text(x)],
        "style": {
            "max_font_size": round(max(sizes), 2) if sizes else 0,
            "median_font_size": round(statistics.median(char_weighted), 2) if char_weighted else 0,
            "bold_ratio": round(
                sum(len(s["text"].strip()) for s in spans if s["bold"])
                / max(1, sum(len(s["text"].strip()) for s in spans)),
                3,
            ),
            "fonts": sorted(set(s["font"] for s in spans if s.get("font"))),
        },
        "spans": spans,
    }


def page_dict(page: fitz.Page, textpage=None) -> dict[str, Any]:
    flags = fitz.TEXTFLAGS_DICT
    if textpage is None:
        return page.get_text("dict", flags=flags, sort=True)
    return page.get_text("dict", flags=flags, sort=True, textpage=textpage)


def discover_body_size(raw_pages: list[dict[str, Any]]) -> tuple[float, dict[str, int]]:
    weights = collections.Counter()
    font_weights = collections.Counter()
    for p in raw_pages:
        for b in p["blocks"]:
            if b["type"] != "text_block":
                continue
            for s in b["spans"]:
                n = len(s["text"].strip())
                if n <= 0:
                    continue
                size = round(float(s["size"]) * 2) / 2
                if 5 <= size <= 14:
                    weights[size] += n
                if s.get("font"):
                    font_weights[s["font"]] += n
    body = float(weights.most_common(1)[0][0]) if weights else 10.0
    return body, dict(font_weights.most_common())


def detect_repeated_margin_text(raw_pages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    occurrences: dict[str, list[tuple[int, str, str, list[float]]]] = collections.defaultdict(list)
    for p in raw_pages:
        h = p["height"]
        for b in p["blocks"]:
            if b["type"] != "text_block":
                continue
            y0, y1 = b["bbox"][1], b["bbox"][3]
            kind = None
            if y1 <= h * .13:
                kind = "header"
            elif y0 >= h * .87:
                kind = "footer"
            if not kind:
                continue
            key = norm_margin_key(b["text"])
            if key:
                occurrences[key].append((p["number"], kind, b["text"], b["bbox"]))
    n_pages = len(raw_pages)
    threshold = max(2, math.ceil(n_pages * .30))
    repeated = {}
    for key, vals in occurrences.items():
        distinct_pages = len(set(v[0] for v in vals))
        if distinct_pages >= threshold:
            kind = collections.Counter(v[1] for v in vals).most_common(1)[0][0]
            repeated[key] = {
                "key": key,
                "kind": kind,
                "pages": sorted(set(v[0] for v in vals)),
                "examples": list(dict.fromkeys(v[2] for v in vals))[:4],
            }
    return repeated


def classify_text_blocks(raw_pages: list[dict[str, Any]], body_size: float, repeated: dict[str, Any]) -> None:
    for p in raw_pages:
        h = p["height"]
        for b in p["blocks"]:
            if b["type"] != "text_block":
                continue
            key = norm_margin_key(b["text"])
            if key in repeated and (b["bbox"][3] <= h * .13 or b["bbox"][1] >= h * .87):
                b["semantic_type"] = repeated[key]["kind"]
                continue
            text = b["text"]
            max_size = b["style"]["max_font_size"]
            bold = b["style"]["bold_ratio"] >= .55
            short = len(text) <= 150
            lines = len(b.get("raw_lines") or [])
            ratio = max_size / max(body_size, .1)
            if FIGURE_CAPTION_RE.match(text) and max_size <= body_size * 1.25:
                sem = "caption"
            elif BULLET_RE.match(text):
                sem = "list_item"
            elif ratio >= 2.15 and short:
                sem = "heading_1"
            elif ratio >= 1.45 and bold and short:
                sem = "heading_2"
            elif ratio >= 1.17 and bold and short and lines <= 4:
                sem = "heading_3"
            elif bold and short and text.isupper() and len(text) < 110:
                sem = "label"
            elif any(q in text for q in QUOTE_MARKS) and len(text) > 35:
                sem = "quote_candidate"
            else:
                sem = "paragraph"
            b["semantic_type"] = sem


def extract_numbers(block: dict[str, Any]) -> list[dict[str, Any]]:
    if block.get("semantic_type") in {"header", "footer"}:
        return []
    text = block["text"]
    out = []
    for i, m in enumerate(NUMBER_RE.finditer(text)):
        raw = m.group(0).strip()
        bare = re.sub(r"\D", "", raw)
        if (
            m.start() < 5
            and len(bare) <= 2
            and not re.search(r"[%€A-Za-z]", raw)
            and re.match(r"^\s*\d{1,2}\s+[A-ZÀ-ÖØ-Ý]", text)
        ):
            continue
        before = text[max(0, m.start() - 70):m.start()]
        after = text[m.end():min(len(text), m.end() + 90)]
        numeric_text = re.match(r"[\d .\u202f]+(?:[,.]\d+)?", raw)
        unit = raw[numeric_text.end():].strip() if numeric_text else ""
        normalized_num = (numeric_text.group(0) if numeric_text else raw).replace(" ", "").replace("\u202f", "").replace(",", ".")
        try:
            value = float(normalized_num)
        except Exception:
            value = None
        role = "value"
        if value is not None and not unit and value.is_integer() and 1900 <= value <= 2100:
            role = "year"
        elif "%" in unit:
            role = "percentage"
        elif "€" in unit or unit.upper() in {"EUR", "USD", "GBP", "K€", "M€"}:
            role = "currency"
        out.append({
            "id": f"{block['id']}-n{i + 1}",
            "type": "number",
            "page": block["page"],
            "text": raw,
            "value": value,
            "unit": unit or None,
            "role": role,
            "context": norm_text(before + " [" + raw + "] " + after),
            "source": {"block_id": block["id"], "page": block["page"], "bbox": block["bbox"]},
        })
    return out


def extract_links(page: fitz.Page, page_num: int) -> list[dict[str, Any]]:
    out = []
    for i, link in enumerate(page.get_links() or []):
        uri = link.get("uri")
        target_page = link.get("page")
        if not uri and (target_page is None or target_page < 0):
            continue
        out.append({
            "id": f"p{page_num}-link{i + 1}",
            "type": "link",
            "page": page_num,
            "bbox": bbox_list(link.get("from", (0, 0, 0, 0))),
            "uri": uri,
            "target_page": target_page + 1 if isinstance(target_page, int) and target_page >= 0 else None,
        })
    return out


def classify_table_role(data: list[list[str]]) -> str:
    if not data:
        return "unknown"
    rows = len(data)
    cols = max((len(r) for r in data), default=0)
    cells = [c for r in data for c in r]
    nonempty = [c for c in cells if norm_text(c)]
    density = len(nonempty) / max(1, len(cells))
    avg_len = sum(len(c) for c in nonempty) / max(1, len(nonempty))
    first = [norm_text(c).lower() for c in (data[0] if data else [])]
    if cols >= 8 and rows >= 3 and density < .55:
        return "schedule_grid_candidate"
    if cols == 4 and rows >= 3:
        short_even = []
        for row in data[:min(rows, 6)]:
            for idx in (0, 2):
                if idx < len(row) and row[idx]:
                    short_even.append(len(row[idx]))
        if short_even and statistics.median(short_even) < 24:
            return "key_value_table"
    if rows <= 3 and cols <= 3 and avg_len > 45:
        return "layout_grid"
    if any(re.fullmatch(r"s\d+", x) for x in first):
        return "schedule_grid_candidate"
    return "data_table"


def extract_tables(page: fitz.Page, page_num: int) -> list[dict[str, Any]]:
    out = []
    try:
        finder = page.find_tables()
        tables = list(finder.tables) if finder else []
    except Exception:
        tables = []
    for i, table in enumerate(tables):
        try:
            data = table.extract()
        except Exception:
            data = []
        data = [[norm_text(c or "") for c in row] for row in data]
        if not data:
            continue
        bbox = getattr(table, "bbox", None) or (0, 0, 0, 0)
        out.append({
            "id": f"p{page_num}-table{i + 1}",
            "type": "table",
            "page": page_num,
            "bbox": bbox_list(bbox),
            "rows": data,
            "row_count": len(data),
            "column_count": max((len(r) for r in data), default=0),
            "role": classify_table_role(data),
            "source": {"file_page": page_num, "bbox": bbox_list(bbox)},
        })
    return out


def extract_vector_regions(page: fitz.Page, page_num: int) -> tuple[int, list[dict[str, Any]]]:
    try:
        drawings = page.get_drawings()
    except Exception:
        drawings = []
    regions = []
    try:
        clusters = page.cluster_drawings()
    except Exception:
        clusters = []
    page_area = max(1, float(page.rect.width * page.rect.height))
    for i, rect in enumerate(clusters or []):
        area = max(0, float(rect.width * rect.height))
        ratio = area / page_area
        if ratio < .008 or ratio > .82:
            continue
        regions.append({
            "id": f"p{page_num}-vector{i + 1}",
            "type": "vector_region_candidate",
            "page": page_num,
            "bbox": bbox_list(rect),
            "area_ratio": round(ratio, 4),
            "semantic_hint": "chart_or_diagram_candidate" if ratio > .04 else "decorative_or_icon_candidate",
        })
    return len(drawings), regions


def extract_images(
    doc: fitz.Document,
    page: fitz.Page,
    page_num: int,
    asset_dir: Path | None,
    asset_cache: dict[int, dict[str, Any]],
) -> tuple[list[dict[str, Any]], float]:
    out = []
    area_sum = 0.0
    page_area = max(1, float(page.rect.width * page.rect.height))
    try:
        infos = page.get_image_info(xrefs=True)
    except Exception:
        infos = []
    for i, info in enumerate(infos):
        bbox = info.get("bbox") or (0, 0, 0, 0)
        rect = fitz.Rect(bbox)
        area_ratio = max(0, float(rect.width * rect.height)) / page_area
        area_sum += area_ratio
        xref = int(info.get("xref") or 0)
        asset_id = None
        if xref > 0:
            if xref not in asset_cache:
                try:
                    raw = doc.extract_image(xref)
                    data = raw.get("image", b"")
                    ext = raw.get("ext") or "bin"
                    digest = hashlib.sha256(data).hexdigest()
                    dhash = image_dhash(data)
                    name = f"img-{digest[:16]}.{ext}"
                    if asset_dir and data:
                        asset_dir.mkdir(parents=True, exist_ok=True)
                        fp = asset_dir / name
                        if not fp.exists():
                            fp.write_bytes(data)
                    asset_cache[xref] = {
                        "id": f"asset-{digest[:16]}",
                        "type": "image",
                        "xref": xref,
                        "sha256": digest,
                        "dhash": dhash,
                        "width": raw.get("width"),
                        "height": raw.get("height"),
                        "colorspace": raw.get("colorspace"),
                        "extension": ext,
                        "file": str((asset_dir / name).as_posix()) if asset_dir else None,
                    }
                except Exception as exc:
                    asset_cache[xref] = {"id": f"asset-xref-{xref}", "type": "image", "xref": xref, "error": str(exc)}
            asset_id = asset_cache[xref]["id"]
        out.append({
            "id": f"p{page_num}-image{i + 1}",
            "type": "image_placement",
            "page": page_num,
            "bbox": bbox_list(bbox),
            "area_ratio": round(area_ratio, 4),
            "asset_id": asset_id,
            "pixel_width": info.get("width"),
            "pixel_height": info.get("height"),
            "source": {"file_page": page_num, "bbox": bbox_list(bbox)},
        })
    return out, min(area_sum, 1.0)


def associate_captions(page_record: dict[str, Any]) -> None:
    visuals = [x for x in page_record["derived"] if x["type"] in {"image_placement", "vector_region_candidate", "table"}]
    captions = [b for b in page_record["blocks"] if b.get("semantic_type") == "caption"]
    for cap in captions:
        cx0, cy0, cx1, _ = cap["bbox"]
        best = None
        best_score = 1e9
        for visual in visuals:
            vx0, _, vx1, vy1 = visual["bbox"]
            vertical = cy0 - vy1
            overlap = max(0, min(cx1, vx1) - max(cx0, vx0)) / max(1, min(cx1 - cx0, vx1 - vx0))
            if -5 <= vertical <= 70 and overlap > .25:
                score = abs(vertical) + (1 - overlap) * 30
                if score < best_score:
                    best_score = score
                    best = visual
        if best:
            best["caption_block_id"] = cap["id"]
            best["caption"] = cap["text"]


def infer_title_candidates(raw_pages: list[dict[str, Any]], body_size: float) -> list[dict[str, Any]]:
    candidates = []
    for page in raw_pages[:min(3, len(raw_pages))]:
        for block in page["blocks"]:
            if block.get("semantic_type") in {"header", "footer", "paragraph", "list_item"}:
                continue
            if len(block["text"]) > 180:
                continue
            size = block["style"]["max_font_size"]
            if size < body_size * 1.35:
                continue
            score = (size / body_size) * 2 + (1 if page["number"] == 1 else 0) + min(len(block["text"]), 80) / 160
            candidates.append({
                "block_id": block["id"],
                "page": page["number"],
                "text": block["text"],
                "font_size": size,
                "score": round(score, 3),
                "bbox": block["bbox"],
            })
    return sorted(candidates, key=lambda x: (-x["score"], x["page"], x["bbox"][1]))[:12]


def infer_sections(raw_pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    headings = []
    for page in raw_pages:
        for block in page["blocks"]:
            if block.get("semantic_type") in {"heading_1", "heading_2"}:
                headings.append({
                    "id": block["id"],
                    "page": page["number"],
                    "level": 1 if block["semantic_type"] == "heading_1" else 2,
                    "title": block["text"],
                    "bbox": block["bbox"],
                })
    return headings


def ingest(
    pdf_path: Path,
    out_path: Path,
    assets_dir: Path | None,
    ocr_fallback: bool = True,
    ocr_language: str = "eng+fra",
) -> dict[str, Any]:
    doc = fitz.open(pdf_path)
    asset_cache: dict[int, dict[str, Any]] = {}
    raw_pages = []
    ocr_pages = []

    for page_index, page in enumerate(doc):
        page_num = page_index + 1
        plain = norm_text(page.get_text("text", sort=True))
        textpage = None
        if ocr_fallback and len(plain) < 25:
            try:
                textpage = page.get_textpage_ocr(language=ocr_language, dpi=180, full=True)
                ocr_text = norm_text(page.get_text("text", textpage=textpage, sort=True))
                if len(ocr_text) > len(plain) + 10:
                    ocr_pages.append(page_num)
                    plain = ocr_text
                else:
                    textpage = None
            except Exception:
                textpage = None

        page_data = page_dict(page, textpage)
        blocks = []
        for block_index, raw_block in enumerate(page_data.get("blocks", []), start=1):
            text_block = text_block_from_raw(raw_block, page_num, block_index)
            if text_block:
                blocks.append(text_block)

        images, image_area = extract_images(doc, page, page_num, assets_dir, asset_cache)
        tables = extract_tables(page, page_num)
        drawing_count, vectors = extract_vector_regions(page, page_num)
        links = extract_links(page, page_num)
        raw_pages.append({
            "number": page_num,
            "width": round(float(page.rect.width), 2),
            "height": round(float(page.rect.height), 2),
            "rotation": int(page.rotation),
            "text_length": len(plain),
            "ocr_used": page_num in ocr_pages,
            "image_area_ratio": round(image_area, 4),
            "drawing_count": drawing_count,
            "blocks": blocks,
            "derived": [*images, *tables, *vectors, *links],
        })

    body_size, font_weights = discover_body_size(raw_pages)
    repeated = detect_repeated_margin_text(raw_pages)
    classify_text_blocks(raw_pages, body_size, repeated)

    all_numbers = []
    all_elements = []
    for page_record in raw_pages:
        for block in page_record["blocks"]:
            all_elements.append({k: v for k, v in block.items() if k != "spans"})
            numbers = extract_numbers(block)
            all_numbers.extend(numbers)
            page_record["derived"].extend(numbers)
        associate_captions(page_record)
        all_elements.extend(page_record["derived"])

    full_text = "\n".join(
        block["text"]
        for page_record in raw_pages
        for block in page_record["blocks"]
        if block.get("semantic_type") not in {"header", "footer"}
    )
    page_count = len(doc)
    scan_pages = [p["number"] for p in raw_pages if p["text_length"] < 25 and p["image_area_ratio"] > .45]
    semantic_counts = collections.Counter(
        block.get("semantic_type", "unknown") for page_record in raw_pages for block in page_record["blocks"]
    )
    result = {
        "version": VERSION,
        "kind": "storyscro_evidence_package",
        "document": {
            "source_file": pdf_path.name,
            "source_path": str(pdf_path),
            "sha256": sha256_file(pdf_path),
            "page_count": page_count,
            "metadata": {k: v for k, v in doc.metadata.items() if v},
            "language": detect_language(full_text),
            "text_characters": len(full_text),
            "ocr_pages": ocr_pages,
            "ocr_required_pages": scan_pages,
        },
        "style_profile": {
            "body_font_size": body_size,
            "font_character_counts": font_weights,
            "semantic_block_counts": dict(semantic_counts),
        },
        "design_profile": infer_design_profile(doc, raw_pages),
        "repeated_margin_elements": list(repeated.values()),
        "title_candidates": infer_title_candidates(raw_pages, body_size),
        "sections": infer_sections(raw_pages),
        "assets": list(asset_cache.values()),
        "statistics": {
            "text_blocks": sum(len(p["blocks"]) for p in raw_pages),
            "numbers": len(all_numbers),
            "tables": sum(1 for p in raw_pages for x in p["derived"] if x["type"] == "table"),
            "table_roles": dict(collections.Counter(
                x.get("role", "unknown") for p in raw_pages for x in p["derived"] if x["type"] == "table"
            )),
            "image_placements": sum(1 for p in raw_pages for x in p["derived"] if x["type"] == "image_placement"),
            "unique_image_assets": len(asset_cache),
            "vector_regions": sum(1 for p in raw_pages for x in p["derived"] if x["type"] == "vector_region_candidate"),
            "links": sum(1 for p in raw_pages for x in p["derived"] if x["type"] == "link"),
        },
        "pages": raw_pages,
        "elements": all_elements,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract a source-grounded StoryScro evidence package from a PDF")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--out", type=Path, default=Path("evidence.json"))
    parser.add_argument("--assets-dir", type=Path, default=None)
    parser.add_argument("--no-ocr", action="store_true", help="Disable OCR fallback for text-empty pages")
    parser.add_argument("--ocr-language", default="eng+fra")
    args = parser.parse_args(argv)
    if not args.pdf.exists():
        parser.error(f"PDF not found: {args.pdf}")
    result = ingest(args.pdf, args.out, args.assets_dir, not args.no_ocr, args.ocr_language)
    print(json.dumps({
        "out": str(args.out),
        "pages": result["document"]["page_count"],
        "language": result["document"]["language"],
        **result["statistics"],
        "ocr_pages": result["document"]["ocr_pages"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
