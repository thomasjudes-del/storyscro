from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))

from prepare_planner_input import prepare  # noqa: E402
from plan import build_input, load_json, validate_provenance, validate_story  # noqa: E402


def main():
    evidence = {
        'document': {'source_file':'fixture.pdf','sha256':'abc','page_count':2,'language':'en'},
        'style_profile': {'body_font_size':10},
        'title_candidates': [{'block_id':'p1-b1','page':1,'text':'A useful report title','font_size':24,'score':5,'bbox':[40,40,400,70]}],
        'repeated_margin_elements': [{'key':'chapter #','kind':'header','pages':[1,2],'examples':['Chapter 1','Chapter 2']}],
        'assets': [], 'statistics': {},
        'pages': [
            {'number':1,'height':842,'blocks':[
                {'id':'p1-b1','page':1,'bbox':[40,40,400,70],'text':'A useful report title','semantic_type':'heading_1','style':{'max_font_size':24}},
                {'id':'p1-b2','page':1,'bbox':[40,90,300,112],'text':'Chapter 1','semantic_type':'header','style':{'max_font_size':22}},
                {'id':'p1-b3','page':1,'bbox':[40,140,500,180],'text':'Evidence paragraph.','semantic_type':'paragraph','style':{'max_font_size':10}},
            ],'derived':[]},
            {'number':2,'height':842,'blocks':[
                {'id':'p2-b1','page':2,'bbox':[40,90,300,112],'text':'Chapter 2','semantic_type':'header','style':{'max_font_size':22}},
                {'id':'p2-b2','page':2,'bbox':[40,140,500,180],'text':'Second evidence paragraph.','semantic_type':'paragraph','style':{'max_font_size':10}},
            ],'derived':[]},
        ]
    }
    planner = prepare(evidence)
    corrected = {x['block_id'] for x in planner['classification_corrections']}
    assert {'p1-b2','p2-b1'} <= corrected
    titles = [s['title'] for s in planner['document_candidates']['sections']]
    assert 'Chapter 1' in titles and 'Chapter 2' in titles

    grammar = load_json(ROOT / 'engine' / 'narrative-grammar.json')
    request = build_input(planner, grammar, 'Use adaptive fidelity.', None)
    assert request[0]['role'] == 'user'
    assert request[0]['content'][0]['type'] == 'input_text'
    assert 'SOURCE-GROUNDED PLANNER INPUT' in request[0]['content'][0]['text']

    schema = load_json(ROOT / 'engine' / 'story.schema.json')
    story = load_json(ROOT / 'v3' / 'story.json')
    validate_story(story, schema)
    validate_provenance(story)
    print('Planner contract smoke OK: evidence repair + prompt contract + v3 Story Model validation.')


if __name__ == '__main__':
    main()
