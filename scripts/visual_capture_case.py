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
            driver.execute_script("document.documentElement.style.scrollBehavior='auto'; document.body.style.scrollBehavior='auto';")
            return
        time.sleep(.25)
    raise RuntimeError('StoryScro renderer did not finish loading')


def scene_ids(driver):
    return driver.execute_script("return [...document.querySelectorAll('.story-scene')].map(x=>x.id)")


def inspect_layout(driver, scene_id):
    dims = driver.execute_script("""
      const w=window.innerWidth;
      const scene=document.getElementById(arguments[0]);
      const marker=window.innerHeight*.46;
      const offenders=[...document.querySelectorAll('*')].map(el=>{
        const r=el.getBoundingClientRect(), cs=getComputedStyle(el);
        return {tag:el.tagName.toLowerCase(),id:el.id||'',cls:el.className?.toString?.()||'',left:r.left,right:r.right,width:r.width,display:cs.display,position:cs.position};
      }).filter(x=>x.display!=='none' && x.width>0 && (x.right>w+5 || x.left<-5) && !String(x.cls).includes('horizontal-track') && !String(x.cls).includes('deliverable-track'));
      const horizontalCopies = scene ? [...scene.querySelectorAll('.panel-copy')] : [];
      const visibleCopies = horizontalCopies.filter(el => {
        const r=el.getBoundingClientRect(), cs=getComputedStyle(el);
        return Number(cs.opacity) > .2 && r.right > 0 && r.left < window.innerWidth && r.bottom > 0 && r.top < window.innerHeight;
      });
      const activeHorizontalRect = visibleCopies[0] ? (()=>{const r=visibleCopies[0].getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height};})() : null;
      return {
        w:window.innerWidth,h:window.innerHeight,sw:document.documentElement.scrollWidth,sh:document.documentElement.scrollHeight,
        scrollY:window.scrollY,marker,
        sceneRects:[...document.querySelectorAll('.story-scene')].map(el=>{const r=el.getBoundingClientRect();return {id:el.id,chapter:el.dataset.chapter,top:r.top,bottom:r.bottom,height:r.height,offsetTop:el.offsetTop};}),
        activeDots:document.querySelectorAll('.micro-dot.active').length,
        activeTarget:document.querySelector('.micro-dot.active')?.dataset.target||'',
        activeLabels:[...document.querySelectorAll('.micro-dot.active .micro-scene-label')].map(x=>x.textContent.trim()),
        scrubber:!!document.querySelector('.micro-scrub-handle'),
        chapter:document.querySelector('.chapter-nav a.active')?.textContent?.trim()||'',
        activeChapter:document.querySelector('.chapter-nav a.active')?.dataset.chapter||'',
        expectedChapter:scene?.dataset.chapter||'',
        totalHorizontalCopies:horizontalCopies.length,
        visibleHorizontalCopies:visibleCopies.length,
        activeHorizontalRect,
        collisions:(()=>{
          const visible=el=>{ if(!el) return false; const r=el.getBoundingClientRect(),cs=getComputedStyle(el); return cs.display!=='none'&&cs.visibility!=='hidden'&&Number(cs.opacity||1)>.16&&r.width>0&&r.height>0; };
          const hit=(a,b)=>{ if(!visible(a)||!visible(b)) return false; const x=a.getBoundingClientRect(),y=b.getBoundingClientRect(); return x.left<y.right+4&&x.right+4>y.left&&x.top<y.bottom+4&&x.bottom+4>y.top; };
          const pairs=[['.proof-title','.proof-copy'],['.horizontal-heading','.panel-copy'],['.deliverable-heading','.delivery-copy'],['.network-title','.workshop-copy']];
          return pairs.filter(([a,b])=>scene&&hit(scene.querySelector(a),scene.querySelector(b))).map(x=>x.join(' vs '));
        })(),
        proofCopyOpacity:scene?.querySelector('.proof-copy')?Number(getComputedStyle(scene.querySelector('.proof-copy')).opacity):null,
        progressiveActiveTiles:scene?.querySelectorAll('.mosaic.progressive .mosaic-tile.active').length??null,
        progressiveVisibleTiles:scene?.querySelector('.mosaic.progressive')?[...scene.querySelectorAll('.mosaic.progressive .mosaic-tile')].filter(el=>Number(getComputedStyle(el).opacity)>.16).length:null,
        sourceDeep:getComputedStyle(document.documentElement).getPropertyValue('--deep').trim(),
        offenders:offenders.slice(0,30)
      };
    """, scene_id)
    if dims['sw'] > dims['w'] + 5:
        raise RuntimeError(f'Horizontal page overflow at {scene_id}: {dims}')
    if dims['activeDots'] != 1:
        raise RuntimeError(f'Expected one active micro-nav scene at {scene_id}, got {dims["activeDots"]}: {json.dumps(dims)}')
    if dims['activeTarget'] != scene_id:
        raise RuntimeError(f'Micro-navigation lag at {scene_id}: active target is {dims["activeTarget"]}: {json.dumps(dims)}')
    if dims['activeChapter'] != dims['expectedChapter']:
        raise RuntimeError(f'Chapter navigation lag at {scene_id}: expected {dims["expectedChapter"]}, got {dims["activeChapter"]}: {json.dumps(dims)}')
    if dims['totalHorizontalCopies'] and dims['visibleHorizontalCopies'] > 1:
        raise RuntimeError(f'Horizontal narrative focus failure at {scene_id}: more than one panel copy visible ({dims["visibleHorizontalCopies"]})')
    if dims['activeHorizontalRect'] and (dims['activeHorizontalRect']['left'] < -5 or dims['activeHorizontalRect']['right'] > dims['w'] + 5):
        raise RuntimeError(f'Clipped horizontal narrative copy at {scene_id}: {dims["activeHorizontalRect"]}')
    if dims.get('collisions'):
        raise RuntimeError(f'Visible narrative text collision at {scene_id}: {dims["collisions"]}')
    if dims.get('progressiveVisibleTiles') is not None and dims['progressiveVisibleTiles'] > 1:
        raise RuntimeError(f'Progressive scene visually overlaps states at {scene_id}: {dims["progressiveVisibleTiles"]} visible tiles')
    if not dims['scrubber']:
        raise RuntimeError('Generic draggable scrubber is missing')
    return dims


def validate_external_assets(driver):
    result = driver.execute_async_script("""
      const done=arguments[arguments.length-1];
      fetch('story.json').then(r=>r.json()).then(story=>{
        const urls=(story.assets||[]).filter(a=>a.type==='image'&&/^https?:/.test(a.uri||'')).map(a=>({id:a.id,uri:a.uri}));
        Promise.all(urls.map(a=>new Promise(resolve=>{
          const img=new Image();
          const timer=setTimeout(()=>resolve({id:a.id,ok:false,reason:'timeout'}),10000);
          img.onload=()=>{clearTimeout(timer);resolve({id:a.id,ok:true,w:img.naturalWidth,h:img.naturalHeight});};
          img.onerror=()=>{clearTimeout(timer);resolve({id:a.id,ok:false,reason:'load-error'});};
          img.src=a.uri;
        }))).then(done).catch(err=>done([{id:'<story>',ok:false,reason:String(err)}]));
      }).catch(err=>done([{id:'<story>',ok:false,reason:String(err)}]));
    """)
    failed=[x for x in result if not x.get('ok')]
    if failed:
        raise RuntimeError('External image asset failure: '+json.dumps(failed,ensure_ascii=False))
    return result


def capture(label, width, height):
    driver = driver_for(width, height)
    report = {'base': BASE, 'viewport': [width,height], 'shots': [], 'console': []}
    try:
        wait_ready(driver)
        ids = scene_ids(driver)
        report['external_assets'] = validate_external_assets(driver)
        if len(ids) < MIN_SCENES:
            raise RuntimeError(f'Expected at least {MIN_SCENES} scenes, got {len(ids)}')
        for scene_id in ids:
            result = driver.execute_script("""
              const el=document.getElementById(arguments[0]);
              const top=el.getBoundingClientRect().top+window.scrollY;
              const span=Math.max(1,el.offsetHeight-window.innerHeight);
              return {top,span,height:el.offsetHeight,scrolly:el.classList.contains('scrolly')};
            """, scene_id)
            checks = [0.08,0.22,0.55,0.82] if result.get('scrolly') else [0.5]
            state_checks=[]
            for q in checks:
                driver.execute_script("window.scrollTo({top:arguments[0]+arguments[1]*arguments[2],behavior:'auto'})",result['top'],result['span'],q)
                time.sleep(.09)
                dims=inspect_layout(driver,scene_id)
                if q < .12 and dims.get('proofCopyOpacity') is not None and dims['proofCopyOpacity'] > .2:
                    raise RuntimeError(f'Proof scene reveals step copy before settle phase at {scene_id}: opacity={dims["proofCopyOpacity"]}')
                if q < .12 and dims.get('progressiveActiveTiles') not in (None,0):
                    raise RuntimeError(f'Progressive mosaic spoils future items during intro at {scene_id}')
                if q >= .22 and dims.get('totalHorizontalCopies') and dims.get('visibleHorizontalCopies') != 1:
                    raise RuntimeError(f'Horizontal narrative must reveal exactly one panel after settle phase at {scene_id}: got {dims.get("visibleHorizontalCopies")}')
                state_checks.append({'progress':q,'dims':dims})
            driver.execute_script("window.scrollTo({top:arguments[0]+arguments[1]*.55,behavior:'auto'})",result['top'],result['span'])
            time.sleep(.08)
            dims=inspect_layout(driver,scene_id)
            out = OUT / f'{label}-{scene_id}.png'
            if not driver.save_screenshot(str(out)):
                raise RuntimeError(f'Screenshot failed: {scene_id}')
            report['shots'].append({'scene':scene_id,'scroll':result,'states':state_checks,'dims':dims,'file':str(out)})

        if width >= 1000:
            first_dot = driver.find_element('css selector','.micro-dot')
            driver.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'auto'})", first_dot)
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
print(f'Generic case visual QA OK for {BASE}: desktop + mobile, navigation labels + scrubber, active scene/chapter sync, single unclipped horizontal narrative focus, no severe console errors.')
