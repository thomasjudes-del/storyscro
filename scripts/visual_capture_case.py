from pathlib import Path
import json
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE = os.environ.get('STORYSCRO_BASE', 'http://127.0.0.1:4174/ccc-2025/')
OUT = Path(os.environ.get('STORYSCRO_OUT', 'visual-artifacts-case'))
OUT.mkdir(parents=True, exist_ok=True)
MIN_SCENES = int(os.environ.get('STORYSCRO_MIN_SCENES', '5'))


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


def wait_ready(driver):
    driver.get(BASE)
    for _ in range(40):
        ready = driver.execute_script("return !!document.querySelector('.story-scene') && !document.querySelector('#loading')")
        if ready:
            return
        time.sleep(.25)
    raise RuntimeError('StoryScro renderer did not finish loading')


def scene_ids(driver):
    return driver.execute_script("return [...document.querySelectorAll('.story-scene')].map(x=>x.id)")


def inspect_layout(driver, scene_id):
    dims = driver.execute_script("""
      const w=window.innerWidth;
      const offenders=[...document.querySelectorAll('*')].map(el=>{
        const r=el.getBoundingClientRect(), cs=getComputedStyle(el);
        return {tag:el.tagName.toLowerCase(),id:el.id||'',cls:el.className?.toString?.()||'',left:r.left,right:r.right,width:r.width,display:cs.display,position:cs.position};
      }).filter(x=>x.display!=='none' && x.width>0 && (x.right>w+5 || x.left<-5) && !String(x.cls).includes('horizontal-track') && !String(x.cls).includes('deliverable-track'));
      return {
        w:window.innerWidth,h:window.innerHeight,sw:document.documentElement.scrollWidth,sh:document.documentElement.scrollHeight,
        activeDots:document.querySelectorAll('.micro-dot.active').length,
        activeLabels:[...document.querySelectorAll('.micro-dot.active .micro-scene-label')].map(x=>x.textContent.trim()),
        scrubber:!!document.querySelector('.micro-scrub-handle'),
        chapter:document.querySelector('.chapter-nav a.active')?.textContent?.trim()||'',
        offenders:offenders.slice(0,30)
      };
    """)
    if dims['sw'] > dims['w'] + 5:
        raise RuntimeError(f'Horizontal page overflow at {scene_id}: {dims}')
    if dims['activeDots'] != 1:
        raise RuntimeError(f'Expected one active micro-nav scene at {scene_id}, got {dims["activeDots"]}')
    if not dims['scrubber']:
        raise RuntimeError('Generic draggable scrubber is missing')
    return dims


def capture(label, width, height):
    driver = driver_for(width, height)
    report = {'base': BASE, 'viewport': [width,height], 'shots': [], 'console': []}
    try:
        wait_ready(driver)
        ids = scene_ids(driver)
        if len(ids) < MIN_SCENES:
            raise RuntimeError(f'Expected at least {MIN_SCENES} scenes, got {len(ids)}')
        for scene_id in ids:
            result = driver.execute_script("""
              const el=document.getElementById(arguments[0]);
              const top=el.getBoundingClientRect().top+window.scrollY;
              const span=Math.max(1,el.offsetHeight-window.innerHeight);
              window.scrollTo(0,top+span*.5);
              return {top,span,height:el.offsetHeight};
            """, scene_id)
            time.sleep(.35)
            dims = inspect_layout(driver, scene_id)
            out = OUT / f'{label}-{scene_id}.png'
            if not driver.save_screenshot(str(out)):
                raise RuntimeError(f'Screenshot failed: {scene_id}')
            report['shots'].append({'scene':scene_id,'scroll':result,'dims':dims,'file':str(out)})

        if width >= 1000:
            first_dot = driver.find_element('css selector','.micro-dot')
            driver.execute_script("arguments[0].scrollIntoView({block:'center'})", first_dot)
            time.sleep(.1)
            driver.execute_script("arguments[0].click()", first_dot)
            time.sleep(.2)
            if not driver.execute_script("return !!document.querySelector('.micro-scene-label')"):
                raise RuntimeError('Clickable micro-navigation text labels were not generated')

        console = driver.get_log('browser')
        report['console'] = console
        severe = [x for x in console if x.get('level') == 'SEVERE' and 'favicon' not in x.get('message','').lower()]
        if severe:
            raise RuntimeError('Browser console errors: ' + json.dumps(severe, ensure_ascii=False))
    finally:
        driver.quit()
        (OUT / f'report-{label}.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')


capture('desktop', 1440, 1000)
capture('mobile', 390, 844)
print(f'Generic case visual QA OK for {BASE}: desktop + mobile, navigation labels + scrubber, no severe console errors.')
