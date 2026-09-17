from pathlib import Path
import json
import sys
import tempfile

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
from ingest import ingest  # noqa: E402


def make_fixture(path: Path, image_path: Path):
    Image.new('RGB', (320, 180), (70, 130, 170)).save(image_path)
    doc = fitz.open()
    for page_no in range(1, 4):
        page = doc.new_page(width=595, height=842)
        page.insert_text((48, 60), 'Synthetic StoryScro Report' if page_no == 1 else f'Chapter {page_no - 1}', fontsize=24 if page_no == 1 else 22, fontname='hebo')
        if page_no == 1:
            page.insert_text((48, 95), 'Evidence-grounded ingestion fixture', fontsize=13, fontname='hebo')
            page.insert_text((48, 135), 'This report tests headings, numbers, images and source positions.', fontsize=10)
            page.insert_image(fitz.Rect(48, 180, 368, 360), filename=str(image_path))
        elif page_no == 2:
            page.insert_text((48, 115), 'Key result', fontsize=12, fontname='hebo')
            page.insert_text((48, 145), 'Adoption reached 42% in 2026 across the pilot group.', fontsize=10)
            page.insert_text((48, 180), '• First evidence point', fontsize=10)
            page.insert_text((48, 205), '• Second evidence point', fontsize=10)
        else:
            page.insert_text((48, 115), 'Simple evidence table', fontsize=12, fontname='hebo')
            x0, y0, cell_w, cell_h = 48, 150, 180, 42
            for r in range(3):
                page.draw_line((x0, y0 + r * cell_h), (x0 + 2 * cell_w, y0 + r * cell_h))
            for c in range(3):
                page.draw_line((x0 + c * cell_w, y0), (x0 + c * cell_w, y0 + 2 * cell_h))
            page.insert_text((x0 + 8, y0 + 26), 'Metric', fontsize=9, fontname='hebo')
            page.insert_text((x0 + cell_w + 8, y0 + 26), 'Value', fontsize=9, fontname='hebo')
            page.insert_text((x0 + 8, y0 + cell_h + 26), 'Coverage', fontsize=9)
            page.insert_text((x0 + cell_w + 8, y0 + cell_h + 26), '88%', fontsize=9)
        page.insert_text((48, 812), 'StoryScro ingestion regression fixture', fontsize=8)
        page.insert_text((540, 812), str(page_no), fontsize=8)
    doc.save(path)
    doc.close()


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        pdf = tmp / 'fixture.pdf'
        image = tmp / 'fixture.png'
        out = tmp / 'evidence.json'
        assets = tmp / 'assets'
        make_fixture(pdf, image)
        data = ingest(pdf, out, assets, ocr_fallback=False)
        assert data['document']['page_count'] == 3
        assert data['document']['language'] == 'en'
        assert data['statistics']['unique_image_assets'] >= 1
        assert data['statistics']['numbers'] >= 3
        assert any(x['kind'] == 'footer' and len(x['pages']) >= 2 for x in data['repeated_margin_elements'])
        assert any(s['level'] == 1 for s in data['sections'])
        assert any(x['type'] == 'table' for p in data['pages'] for x in p['derived'])
        assert any(x['type'] == 'number' and '%' in x['text'] for p in data['pages'] for x in p['derived'])
        assert all(len(b['bbox']) == 4 for p in data['pages'] for b in p['blocks'])
        parsed = json.loads(out.read_text(encoding='utf-8'))
        assert parsed['document']['sha256'] == data['document']['sha256']
        print('PDF ingestion smoke OK:', json.dumps(data['statistics'], sort_keys=True))


if __name__ == '__main__':
    main()
