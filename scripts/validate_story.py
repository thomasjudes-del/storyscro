#!/usr/bin/env python3
"""Validate a renderer-independent StoryScro story.json without calling any model."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_schema(story, schema):
    errors = sorted(Draft202012Validator(schema).iter_errors(story), key=lambda e: list(e.path))
    if errors:
        lines = []
        for error in errors[:30]:
            where = ".".join(str(p) for p in error.path) or "<root>"
            lines.append(f"{where}: {error.message}")
        raise ValueError("Story schema validation failed:\n" + "\n".join(lines))


def validate_provenance(story):
    evidence_ids = {e.get("id") for e in story.get("evidence", [])}
    if not evidence_ids:
        raise ValueError("Story contains no evidence objects")
    problems = []
    scene_count = 0
    for chapter in story.get("chapters", []):
        for scene in chapter.get("scenes", []):
            scene_count += 1
            refs = scene.get("source_evidence_ids", [])
            direct = scene.get("source_refs", [])
            if not refs and not direct:
                problems.append(f"{scene.get('id')}: no source evidence or page refs")
            for ref in refs:
                if ref not in evidence_ids:
                    problems.append(f"{scene.get('id')}: unknown evidence id {ref}")
            if not scene.get("transformations"):
                problems.append(f"{scene.get('id')}: missing transformation trail")
    if scene_count < 3:
        problems.append(f"story has only {scene_count} scenes")
    if problems:
        raise ValueError("Story provenance validation failed:\n" + "\n".join(problems[:40]))


def validate_editorial_sanity(story):
    problems = []
    seen_assets = set()
    for chapter in story.get("chapters", []):
        nav = (chapter.get("nav_label") or chapter.get("title") or "").strip()
        if not nav or nav.isdigit():
            problems.append(f"{chapter.get('id')}: weak chapter navigation label {nav!r}")
        for scene in chapter.get("scenes", []):
            title = str(scene.get("title") or scene.get("message") or "")
            if len(title) > 140:
                problems.append(f"{scene.get('id')}: title too long ({len(title)} chars)")
            for media in scene.get("media", []):
                aid = media.get("asset_id")
                if aid and aid in seen_assets and scene.get("primitive") not in {"comparison", "reveal"}:
                    problems.append(f"{scene.get('id')}: repeated asset {aid}")
                if aid:
                    seen_assets.add(aid)
    if problems:
        raise ValueError("Story editorial sanity validation failed:\n" + "\n".join(problems[:40]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("story", type=Path)
    parser.add_argument("--schema", type=Path, default=Path("engine/story.schema.json"))
    args = parser.parse_args()
    story = load(args.story)
    schema = load(args.schema)
    validate_schema(story, schema)
    validate_provenance(story)
    validate_editorial_sanity(story)
    scenes = sum(len(c.get("scenes", [])) for c in story.get("chapters", []))
    print(json.dumps({"story": str(args.story), "chapters": len(story.get("chapters", [])), "scenes": scenes, "evidence": len(story.get("evidence", [])), "status": "ok"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
