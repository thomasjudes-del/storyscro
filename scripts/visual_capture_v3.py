from pathlib import Path
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

OUT = Path('visual-artifacts-v3')
OUT.mkdir(exist_ok=True)
BASE = 'http://127.0.0.1:4174/v3/'

shots = [
    ('hero', 0.05),
    ('core-question', 0.45),
    ('decision-path', 0.45),
    ('vulnerability-mosaic', 0.58),
    ('priority-matrix', 0.62),
    ('method-track', 0.54),
    ('gantt-12-weeks', 0.62),
    ('workshop-network', 0.57),
    ('deliverable-sequence', 0.53),
    ('references', 0.56),
    ('finale', 0.20),
]

def driver_for(width, height):
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(f'--window-size={width},{height}')
    options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
    d = webdriver.Chrome(options=options)
    d.set_window_size(width, height)
    return d

def capture(label, width, height, selected):
    driver = driver_for(width, height)
    report = {'viewport': [width, height], 'shots': [], 'console': [], 'overflowers': []}
    try:
        driver.get(BASE)
        for _ in range(30):
            ready = driver.execute_script("return !!document.querySelector('.story-scene') && !document.querySelector('#loading')")
            if ready:
                break
            time.sleep(.25)
        else:
            raise RuntimeError('Generic renderer did not finish loading')

        count = driver.execute_script("return document.querySelectorAll('.story-scene').length")
        if count < 8:
            raise RuntimeError(f'Expected multiple generated scenes, got {count}')

        for scene_id, progress in selected:
            result = driver.execute_script(
                """
                const id=arguments[0],p=arguments[1];
                const el=document.getElementById(id);
                if(!el) return {ok:false,id};
                const top=el.getBoundingClientRect().top + window.scrollY;
                const span=Math.max(1,el.offsetHeight-window.innerHeight);
                window.scrollTo(0,top+span*p);
                return {ok:true,id,top,height:el.offsetHeight,span};
                """,
                scene_id, progress
            )
            if not result or not result.get('ok'):
                raise RuntimeError(f'Scene not found: {scene_id}')
            time.sleep(.55)
            dims = driver.execute_script("""
              return {
                y:window.scrollY,w:window.innerWidth,h:window.innerHeight,
                sw:document.documentElement.scrollWidth,sh:document.documentElement.scrollHeight,
                chapter:document.querySelector('.chapter-nav a.active')?.textContent || '',
                activeDots:document.querySelectorAll('.micro-dot.active').length
              };
            """)
            if dims['sw'] > dims['w'] + 4:
                overflowers = driver.execute_script("""
                  const w=window.innerWidth;
                  return [...document.querySelectorAll('*')].map(el=>{
                    const r=el.getBoundingClientRect(), cs=getComputedStyle(el);
                    return {
                      tag:el.tagName.toLowerCase(), id:el.id||'', cls:el.className?.toString?.()||'',
                      left:Math.round(r.left*10)/10,right:Math.round(r.right*10)/10,width:Math.round(r.width*10)/10,
                      position:cs.position,overflowX:cs.overflowX,display:cs.display,
                      parentOverflowX:el.parentElement?getComputedStyle(el.parentElement).overflowX:''
                    };
                  }).filter(x=>x.display!=='none' && (x.right>w+4 || x.left<-4)).slice(0,80);
                """)
                report['overflowers'].append({'scene':scene_id,'dims':dims,'elements':overflowers})
                print('OVERFLOW_DIAGNOSTIC', json.dumps({'scene':scene_id,'dims':dims,'elements':overflowers}, ensure_ascii=False))
                raise RuntimeError(f'Horizontal overflow at {label}/{scene_id}: {dims}')
            if dims['activeDots'] != 1:
                raise RuntimeError(f'Expected one active micro-nav dot at {label}/{scene_id}, got {dims["activeDots"]}')
            out = OUT / f'{label}-{scene_id}.png'
            if not driver.save_screenshot(str(out)):
                raise RuntimeError(f'Screenshot failed: {scene_id}')
            report['shots'].append({'scene': scene_id, 'progress': progress, 'dims': dims})

        console = driver.get_log('browser')
        report['console'] = console
        severe = [x for x in console if x.get('level') == 'SEVERE' and 'favicon' not in x.get('message','').lower()]
        if severe:
            raise RuntimeError('Browser console errors: ' + json.dumps(severe, ensure_ascii=False))
    finally:
        driver.quit()
        (OUT / f'report-{label}.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')

capture('desktop', 1440, 1000, shots)
mobile = [(sid,p) for sid,p in shots if sid in {'hero','core-question','decision-path','priority-matrix','gantt-12-weeks','deliverable-sequence','finale'}]
capture('mobile', 390, 844, mobile)
print('StoryScro v3 visual QA OK: desktop + mobile, no horizontal overflow or severe console errors.')
