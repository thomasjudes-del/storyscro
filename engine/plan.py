#!/usr/bin/env python3
"""Generate a renderer-independent StoryScro story.json from planner input.

Requires OPENAI_API_KEY for live calls. `--dry-run` validates and prints the
request contract without sending any source material.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import sys
from typing import Any

from jsonschema import Draft202012Validator
from openai import OpenAI

ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL = os.environ.get("STORYSCRO_MODEL", "gpt-5.6-terra")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_input(planner_input: dict[str, Any], grammar: dict[str, Any], user_instruction: str | None, source_pdf: Path | None):
    prompt = (ROOT / "PLANNER_PROMPT.md").read_text(encoding="utf-8")
    compact_grammar = {
        "principles": grammar.get("principles", {}),
        "editorial_policy": grammar.get("editorial_policy", {}),
        "navigation": grammar.get("navigation", {}),
        "text_emphasis": grammar.get("text_emphasis", {}),
        "effects": grammar.get("effects", {}),
        "primitives": grammar.get("primitives", {}),
        "selection_rules": grammar.get("selection_rules", []),
        "media_policy": grammar.get("media_policy", {}),
        "motion_policy": grammar.get("motion_policy", {}),
        "source_design_policy": grammar.get("source_design_policy", {}),
        "scene_lifecycle": grammar.get("scene_lifecycle", {}),
        "interaction_policy": grammar.get("interaction_policy", {}),
        "presentation_dimensions": grammar.get("presentation_dimensions", {}),
        "presentation_presets": grammar.get("presentation_presets", {}),
        "presentation_rules": grammar.get("presentation_rules", []),
    }
    content: list[dict[str, Any]] = [
        {
            "type": "input_text",
            "text": (
                prompt
                + "\n\n--- NARRATIVE GRAMMAR ---\n"
                + json.dumps(compact_grammar, ensure_ascii=False)
                + "\n\n--- SOURCE-GROUNDED PLANNER INPUT ---\n"
                + json.dumps(planner_input, ensure_ascii=False)
                + ("\n\n--- USER INSTRUCTION ---\n" + user_instruction if user_instruction else "")
            ),
        }
    ]
    if source_pdf:
        encoded = base64.b64encode(source_pdf.read_bytes()).decode("ascii")
        content.append({
            "type": "input_file",
            "filename": source_pdf.name,
            "file_data": f"data:application/pdf;base64,{encoded}",
        })
    return [{"role": "user", "content": content}]


def validate_story(story: dict[str, Any], schema: dict[str, Any]) -> None:
    errors = sorted(Draft202012Validator(schema).iter_errors(story), key=lambda e: list(e.path))
    if errors:
        lines = []
        for error in errors[:20]:
            path = ".".join(str(p) for p in error.path) or "<root>"
            lines.append(f"{path}: {error.message}")
        raise ValueError("Story Model schema validation failed:\n" + "\n".join(lines))


def validate_provenance(story: dict[str, Any]) -> None:
    evidence_ids = {e.get("id") for e in story.get("evidence", [])}
    if not evidence_ids:
        raise ValueError("Story Model contains no evidence objects")
    problems = []
    for chapter in story.get("chapters", []):
        for scene in chapter.get("scenes", []):
            refs = scene.get("source_evidence_ids", [])
            direct = scene.get("source_refs", [])
            if not refs and not direct:
                problems.append(f"{scene.get('id')}: no source evidence or source refs")
            for ref in refs:
                if ref not in evidence_ids:
                    problems.append(f"{scene.get('id')}: unknown evidence id {ref}")
            if not scene.get("transformations"):
                problems.append(f"{scene.get('id')}: missing transformation trail")
    if problems:
        raise ValueError("Story provenance validation failed:\n" + "\n".join(problems[:30]))


def extract_json(response) -> dict[str, Any]:
    text = getattr(response, "output_text", None)
    if not text:
        raise RuntimeError("Planner returned no output_text")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Planner returned invalid JSON: {exc}") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate StoryScro story.json with the AI Story Planner")
    parser.add_argument("planner_input", type=Path)
    parser.add_argument("--out", type=Path, default=Path("story.json"))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--source-pdf", type=Path, default=None, help="Optionally provide the source PDF so the planner can inspect visual structure in addition to deterministic evidence")
    parser.add_argument("--instruction", default=None, help="Optional audience/fidelity/compression instruction")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    planner_input = load_json(args.planner_input)
    schema = load_json(ROOT / "story.schema.json")
    grammar = load_json(ROOT / "narrative-grammar.json")
    if planner_input.get("kind") != "storyscro_planner_input":
        raise ValueError("Expected a storyscro_planner_input JSON")
    if args.source_pdf and not args.source_pdf.exists():
        raise FileNotFoundError(args.source_pdf)

    input_items = build_input(planner_input, grammar, args.instruction, args.source_pdf)
    request_summary = {
        "model": args.model,
        "input_items": len(input_items),
        "source_pdf": args.source_pdf.name if args.source_pdf else None,
        "structured_output": "story.schema.json",
        "fidelity": planner_input.get("constraints", {}).get("default_fidelity"),
        "compression": planner_input.get("constraints", {}).get("default_compression"),
    }
    if args.dry_run:
        print(json.dumps(request_summary, ensure_ascii=False, indent=2))
        return 0

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for a live planning call")

    client = OpenAI()
    response = client.responses.create(
        model=args.model,
        reasoning={"effort": "high"},
        input=input_items,
        text={
            "format": {
                "type": "json_schema",
                "name": "storyscro_story_model",
                "description": "Renderer-independent StoryScro Story Model",
                "schema": schema,
                "strict": False,
            }
        },
    )
    story = extract_json(response)
    validate_story(story, schema)
    validate_provenance(story)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({**request_summary, "out": str(args.out), "response_id": getattr(response, "id", None)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
