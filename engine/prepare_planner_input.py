#!/usr/bin/env python3
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
from typing import Any

VERSION = '0.3.0'
GENERIC_TITLES = {
    'memoire technique', 'mémoire technique', 'technical report', 'report', 'rapport',
    'proposal', 'proposition', 'presentation', 'présentation'
}


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def compact_block(block: dict[str, Any]) -> dict[str, Any]:
    return {k: block[k] for k in ('id', 'page', 'bbox', 'semantic_type', 'text') if k in block}


def repair_large_margin_headings(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    """Recover genuine chapter headings that happen to repeat near the top margin.

    Repeated-header detection intentionally normalises digits. A document containing
    'Chapter 1', 'Chapter 2', ... can therefore look like a repeated running header.
    Large typography is stronger evidence of a chapter heading than repetition at
    the page margin, so repair this before editorial planning and record the change.
    """
    body = float(evidence.get('style_profile', {}).get('body_font_size') or 10)
    corrections = []
    for page in evidence.get('pages', []):
        height = float(page.get('height') or 1)
        for block in page.get('blocks', []):
            if block.get('semantic_type') not in {'header', 'footer'}:
                continue
            max_size = float(block.get('style', {}).get('max_font_size') or 0)
            text = block.get('text', '')
            y0, y1 = (block.get('bbox') or [0, 0, 0, 0])[1], (block.get('bbox') or [0, 0, 0, 0])[3]
            near_top = y1 <= height * .16
            if near_top and max_size >= body * 1.45 and len(text) <= 150:
                ratio = max_size / max(body, .1)
                new_type = 'heading_1' if ratio >= 1.9 else 'heading_2'
                corrections.append({'block_id': block.get('id'), 'from': block['semantic_type'], 'to': new_type, 'reason': 'large-font repeated top-margin heading'})
                block['semantic_type'] = new_type
    return corrections


def choose_title(evidence: dict[str, Any]) -> dict[str, Any] | None:
    candidates = evidence.get('title_candidates', [])
    if not candidates:
        return None
    def score(candidate):
        text = candidate.get('text', '').strip()
        generic = text.lower() in GENERIC_TITLES
        descriptive = min(len(text), 90) / 45
        first = 1.2 if candidate.get('page') == 1 else 0
        return candidate.get('score', 0) + descriptive + first - (3.5 if generic else 0)
    return max(candidates, key=score)


def build_sections(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    sections, preface = [], []
    current = None
    for page in evidence.get('pages', []):
        for block in page.get('blocks', []):
            if block.get('semantic_type') in {'header', 'footer'}:
                continue
            if block.get('semantic_type') == 'heading_1':
                current = {'id': f"section-{len(sections)+1}", 'title': block['text'], 'heading_block_id': block['id'], 'page_start': block['page'], 'page_end': block['page'], 'blocks': [compact_block(block)]}
                sections.append(current)
            elif current is None:
                preface.append(compact_block(block))
            else:
                current['blocks'].append(compact_block(block)); current['page_end'] = block['page']
    if preface:
        sections.insert(0, {'id':'preface','title':'Front matter','page_start':preface[0]['page'],'page_end':preface[-1]['page'],'blocks':preface})
    for section in sections:
        section['text'] = '\n'.join(b['text'] for b in section['blocks'])
        section['headings'] = [b for b in section['blocks'] if b.get('semantic_type','').startswith('heading_')]
        section['paragraph_count'] = sum(1 for b in section['blocks'] if b.get('semantic_type') == 'paragraph')
    return sections


def derive_candidates(evidence: dict[str, Any]):
    numbers, tables, images, vectors, quotes = [], [], [], [], []
    assets = {a['id']: a for a in evidence.get('assets', []) if a.get('id')}
    for page in evidence.get('pages', []):
        for block in page.get('blocks', []):
            if block.get('semantic_type') == 'quote_candidate': quotes.append(compact_block(block))
        for item in page.get('derived', []):
            typ = item.get('type')
            if typ == 'number': numbers.append(item)
            elif typ == 'table': tables.append({k:item.get(k) for k in ('id','page','bbox','role','rows','row_count','column_count','caption') if item.get(k) is not None})
            elif typ == 'image_placement':
                a = assets.get(item.get('asset_id'), {})
                images.append({**{k:item.get(k) for k in ('id','page','bbox','area_ratio','asset_id','caption') if item.get(k) is not None}, 'asset':{k:a.get(k) for k in ('id','sha256','dhash','width','height','extension','file') if a.get(k) is not None}})
            elif typ == 'vector_region_candidate' and item.get('semantic_hint') == 'chart_or_diagram_candidate':
                a = assets.get(item.get('asset_id'), {})
                vectors.append({**{k:item.get(k) for k in ('id','page','bbox','area_ratio','semantic_hint','caption','asset_id') if item.get(k) is not None}, 'asset':{k:a.get(k) for k in ('id','origin','sha256','dhash','width','height','extension','file','kind') if a.get(k) is not None}})
    return numbers, tables, images, vectors, quotes


def prepare(evidence: dict[str, Any]) -> dict[str, Any]:
    evidence = copy.deepcopy(evidence)
    corrections = repair_large_margin_headings(evidence)
    title = choose_title(evidence)
    sections = build_sections(evidence)
    numbers, tables, images, vectors, quotes = derive_candidates(evidence)
    return {
        'version': VERSION, 'kind': 'storyscro_planner_input',
        'source': {'file':evidence['document']['source_file'],'sha256':evidence['document']['sha256'],'page_count':evidence['document']['page_count'],'language':evidence['document'].get('language','und')},
        'document_candidates': {'preferred_title':title,'title_candidates':evidence.get('title_candidates',[]),'sections':[{k:s[k] for k in ('id','title','page_start','page_end','text','headings','paragraph_count')} for s in sections]},
        'evidence_candidates': {'numbers':numbers,'tables':tables,'images':images,'vector_visuals':vectors,'quotes':quotes,'repeated_margin_elements':evidence.get('repeated_margin_elements',[])},
        'classification_corrections': corrections,
        'style_profile': evidence.get('style_profile',{}),
        'design_profile': evidence.get('design_profile',{}),
        'ingestion_statistics': evidence.get('statistics',{}),
        'constraints': {'source_grounded':True,'source_refs_required':True,'allowed_statuses':['VERIFIED','INFERENCE','HYPOTHESIS','TO_CONFIRM','NOT_FOUND'],'default_fidelity':'adaptive','default_compression':'balanced'}
    }


def main():
    parser=argparse.ArgumentParser(description='Prepare a compact, source-grounded input for the StoryScro AI planner')
    parser.add_argument('evidence',type=Path); parser.add_argument('--out',type=Path,default=Path('planner-input.json')); args=parser.parse_args()
    output=prepare(load(args.evidence)); args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'out':str(args.out),'sections':len(output['document_candidates']['sections']),'numbers':len(output['evidence_candidates']['numbers']),'tables':len(output['evidence_candidates']['tables']),'images':len(output['evidence_candidates']['images']),'vectors':len(output['evidence_candidates']['vector_visuals']),'classification_corrections':len(output['classification_corrections'])},ensure_ascii=False,indent=2))

if __name__ == '__main__': main()
