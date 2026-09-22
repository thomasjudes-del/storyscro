from pathlib import Path
import json
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE = os.environ.get('STORYSCRO_BASE', 'http://127.0.0.1:4174/stories/sete-impact-ai/')
OUT = Path(os.environ.get('STORYSCRO_OUT', 'visual-artifacts-story'))
OUT.mkdir(parents=True, exist_ok=True)
MIN_SCENES = int(os.environ.get('STORYSCRO_MIN_SCENES', '5'))
EXPECT_SOURCE = os.environ.get('STORYSCRO_EXPECT_SOURCE_VISIBLE', '0') == '1'
EXPECT_SOURCE_SUBSTRING = os.environ.get('STORYSCRO_EXPECT_SOURCE_SUBSTRING', '')


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
    for _ in range(50):
        ready = driver.execute_script("return !!document.querySelector('.story-scene') && !document.querySelector('#loading')")
        if ready:
            driver.execute_script("document.documentElement.style.scrollBehavior='auto'; document.body.style.scrollBehavior='auto';")
            return
        time.sleep(.25)
    detail = driver.execute_script("return {error:document.querySelector('.error')?.innerText||'',body:document.body.innerText.slice(0,1800)}")
    raise RuntimeError('Renderer did not finish loading: ' + json.dumps(detail, ensure_ascii=False))


def inspect(driver, scene_id):
    return driver.execute_script("""
      const scene=document.getElementById(arguments[0]),w=window.innerWidth,h=window.innerHeight;
      const rect=scene?.getBoundingClientRect();
      const h1=scene?.querySelector('h1'),h2=scene?.querySelector('h2'),header=document.querySelector('.story-header');
      const visible=el=>{if(!el)return false;const r=el.getBoundingClientRect(),cs=getComputedStyle(el);return cs.display!=='none'&&cs.visibility!=='hidden'&&Number(cs.opacity||1)>.16&&r.width>0&&r.height>0};
      const textNodes=[...scene?.querySelectorAll('h1,h2,h3,p,strong,.big-number-value')||[]].filter(visible);
      const collisions=[];
      for(let i=0;i<textNodes.length;i++)for(let j=i+1;j<textNodes.length;j++){
        const a=textNodes[i].getBoundingClientRect(),b=textNodes[j].getBoundingClientRect();
        if(a.left<b.right-4&&a.right>b.left+4&&a.top<b.bottom-4&&a.bottom>b.top+4)collisions.push([textNodes[i].tagName,textNodes[j].tagName]);
      }
      return {
        width:w,height:h,scrollWidth:document.documentElement.scrollWidth,
        sceneHeight:rect?.height||0,sceneTop:rect?.top||0,
        activeDots:document.querySelectorAll('.micro-dot.active').length,
        activeTarget:document.querySelector('.micro-dot.active')?.dataset.target||'',
        activeChapter:document.querySelector('.chapter-nav a.active')?.dataset.chapter||'',
        expectedChapter:scene?.dataset.chapter||'',
        titleHeight:(h1||h2)?.getBoundingClientRect().height||0,
        titleTop:(h1||h2)?.getBoundingClientRect().top||0,
        headerBottom:header?.getBoundingClientRect().bottom||0,
        collisionCount:collisions.length,
        chartCount:scene?.querySelectorAll('.story-chart').length||0,
        chartWidth:scene?.querySelector('.story-chart')?.getBoundingClientRect().width||0
      };
    """, scene_id)


def validate_external_assets(driver):
    return driver.execute_async_script("""
      const done=arguments[arguments.length-1];
      fetch('story.json').then(r=>r.json()).then(story=>{
        const urls=(story.assets||[]).filter(a=>a.type==='image'&&/^https?:/.test(a.uri||'')).map(a=>({id:a.id,uri:a.uri}));
        Promise.all(urls.map(a=>new Promise(resolve=>{
          const img=new Image(),timer=setTimeout(()=>resolve({id:a.id,ok:false,reason:'timeout'}),10000);
          img.onload=()=>{clearTimeout(timer);resolve({id:a.id,ok:true,w:img.naturalWidth,h:img.naturalHeight})};
          img.onerror=()=>{clearTimeout(timer);resolve({id:a.id,ok:false,reason:'load-error'})};
          img.src=a.uri;
        }))).then(done).catch(err=>done([{id:'<story>',ok:false,reason:String(err)}]));
      }).catch(err=>done([{id:'<story>',ok:false,reason:String(err)}]));
    """)


def capture(label, width, height):
    d=driver_for(width,height)
    report={'base':BASE,'viewport':[width,height],'shots':[]}
    try:
        wait_ready(d)
        ids=d.execute_script("return [...document.querySelectorAll('.story-scene')].map(x=>x.id)")
        if len(ids)<MIN_SCENES:
            raise RuntimeError(f'Expected at least {MIN_SCENES} scenes, got {len(ids)}')
        assets=validate_external_assets(d)
        failed=[x for x in assets if not x.get('ok')]
        if failed:
            raise RuntimeError('External image failures: '+json.dumps(failed,ensure_ascii=False))
        report['external_assets']=assets
        source=d.execute_script("const a=document.getElementById('sourcePdfLink');return {visible:!!a&&!a.hidden,href:a?.href||''}")
        if EXPECT_SOURCE and not source['visible']:
            raise RuntimeError('Expected visible original PDF link')
        if EXPECT_SOURCE_SUBSTRING and EXPECT_SOURCE_SUBSTRING not in source['href']:
            raise RuntimeError('Unexpected original PDF link: '+json.dumps(source))
        report['source_pdf_link']=source
        for scene_id in ids:
            meta=d.execute_script("""
              const el=document.getElementById(arguments[0]),top=el.getBoundingClientRect().top+scrollY,span=Math.max(1,el.offsetHeight-innerHeight);
              return {top,span,scrolly:el.classList.contains('scrolly')};
            """,scene_id)
            progress=.52 if meta['scrolly'] else .5
            d.execute_script("window.scrollTo({top:arguments[0]+arguments[1]*arguments[2],behavior:'auto'})",meta['top'],meta['span'],progress)
            time.sleep(.15)
            dims=inspect(d,scene_id)
            if dims['scrollWidth']>dims['width']+6:
                raise RuntimeError(f'Horizontal overflow at {scene_id}: {dims}')
            if dims['activeDots']!=1 or dims['activeTarget']!=scene_id:
                raise RuntimeError(f'Navigation mismatch at {scene_id}: {dims}')
            if dims['activeChapter']!=dims['expectedChapter']:
                raise RuntimeError(f'Chapter mismatch at {scene_id}: {dims}')
            if dims['titleHeight']>dims['height']*.48:
                raise RuntimeError(f'Title too tall at {scene_id}: {dims}')
            if dims['collisionCount']>0:
                raise RuntimeError(f'Visible text collision at {scene_id}: {dims}')
            # A long non-sticky reading scene may naturally scroll its heading behind the fixed
            # header. Treat overlap as a defect only while the scene itself is at its arrival frame
            # or when the scene is sticky/scrolly and the heading is expected to remain composed.
            sticky_or_arriving = meta['scrolly'] or dims['sceneTop'] >= -8
            if sticky_or_arriving and dims['titleTop'] and dims['titleTop']<dims['headerBottom']-2:
                raise RuntimeError(f'Title/header collision at {scene_id}: {dims}')
            out=OUT/f'{label}-{scene_id}.png'
            d.save_screenshot(str(out))
            report['shots'].append({'scene':scene_id,'dims':dims,'file':str(out)})
        severe=[x for x in d.get_log('browser') if x.get('level')=='SEVERE' and 'favicon' not in x.get('message','').lower()]
        if severe:
            raise RuntimeError('Browser console errors: '+json.dumps(severe,ensure_ascii=False))
    finally:
        d.quit()
        (OUT/f'report-{label}.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')


capture('desktop',1440,1000)
capture('mobile',390,844)
print(f'Generic StoryScro visual QA OK for {BASE}')
