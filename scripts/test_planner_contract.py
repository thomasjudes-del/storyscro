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

    # Regression: branded reports often make a TOC label or KPI callout visually
    # larger than the cover title. They must not hijack document identity or chapters.
    noisy = {
        'document': {'source_file':'branded.pdf','sha256':'def','page_count':3,'language':'fr'},
        'style_profile': {'body_font_size':10},
        'title_candidates': [
            {'block_id':'p1-b1','page':1,'text':'Rapport Développement Durable 2024','font_size':28,'score':6.8,'bbox':[40,700,400,800]},
            {'block_id':'p2-b1','page':2,'text':'sommaire','font_size':60,'score':12.0,'bbox':[600,80,900,170]},
        ],
        'repeated_margin_elements': [], 'assets': [], 'statistics': {},
        'pages': [
            {'number':1,'height':842,'blocks':[
                {'id':'p1-b1','page':1,'bbox':[40,700,400,800],'text':'Rapport Développement Durable 2024','semantic_type':'heading_1','style':{'max_font_size':28}},
            ],'derived':[]},
            {'number':2,'height':842,'blocks':[
                {'id':'p2-b1','page':2,'bbox':[600,80,900,170],'text':'sommaire','semantic_type':'heading_1','style':{'max_font_size':60}},
                {'id':'p2-b2','page':2,'bbox':[40,240,180,300],'text':'43%','semantic_type':'heading_1','style':{'max_font_size':44}},
                {'id':'p2-b3','page':2,'bbox':[40,320,240,380],'text':'+ de 2,7 millions','semantic_type':'heading_1','style':{'max_font_size':38}},
                {'id':'p2-b4','page':2,'bbox':[40,420,500,470],'text':'Réduire notre empreinte carbone','semantic_type':'heading_1','style':{'max_font_size':28}},
            ],'derived':[
                {'id':'layout-table','type':'table','page':2,'bbox':[40,500,400,560],'role':'data_table','rows':[['Président',''],['','de France']],'row_count':2,'column_count':2},
            ]},
            {'number':3,'height':842,'blocks':[
                {'id':'p3-b1','page':3,'bbox':[40,60,500,100],'text':'Evidence paragraph.','semantic_type':'paragraph','style':{'max_font_size':10}},
            ],'derived':[]},
        ]
    }
    noisy_planner = prepare(noisy)
    assert noisy_planner['document_candidates']['preferred_title']['text'] == 'Rapport Développement Durable 2024'
    noisy_titles = [x['title'] for x in noisy_planner['document_candidates']['sections']]
    assert 'sommaire' not in noisy_titles and '43%' not in noisy_titles and '+ de 2,7 millions' not in noisy_titles
    assert 'Réduire notre empreinte carbone' in noisy_titles
    assert noisy_planner['evidence_candidates']['tables'] == []

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
