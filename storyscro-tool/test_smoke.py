import json, os, time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

BASE=os.environ.get("STORYSCRO_TOOL_BASE","http://127.0.0.1:4182/storyscro-tool/")
PDF=os.environ["STORYSCRO_TOOL_PDF"]
OUT=Path(os.environ.get("STORYSCRO_TOOL_OUT","tool-artifacts")); OUT.mkdir(parents=True,exist_ok=True)

def driver_for(width,height):
    opts=Options()
    opts.add_argument("--headless=new"); opts.add_argument("--no-sandbox"); opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument(f"--window-size={width},{height}")
    opts.set_capability("goog:loggingPrefs",{"browser":"ALL"})
    return webdriver.Chrome(options=opts)

def run(label,width,height):
    d=driver_for(width,height)
    try:
        d.get(BASE)
        WebDriverWait(d,30).until(EC.presence_of_element_located((By.ID,"pdfInput")))
        d.find_element(By.ID,"pdfInput").send_keys(PDF)
        def done(driver):
            return driver.execute_script("return !document.getElementById('storyView').hidden || !document.getElementById('errorToast').hidden")
        WebDriverWait(d,240).until(done)
        err=d.execute_script("return document.getElementById('errorToast').hidden ? '' : document.getElementById('errorText').innerText")
        if err: raise RuntimeError("Tool error: "+err)
        stats=d.execute_script("""
          const e=window.__storyscro?.getEvidence?.(), s=window.__storyscro?.getStory?.();
          return {
            pages:e?.stats?.pages||0,
            paragraphs:e?.stats?.paragraphs||0,
            numbers:e?.stats?.numbers||0,
            sections:e?.stats?.sections||0,
            chapters:s?.chapters?.length||0,
            scenes:(s?.chapters||[]).reduce((n,c)=>n+(c.scenes||[]).length,0),
            title:s?.document?.title||'',
            primary:s?.design_system?.palette?.primary||'',
            sourceLink:document.querySelector('.story-actions a')?.href||'',
            overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
            microDots:document.querySelectorAll('.micro-dot').length,
            sourceButtons:document.querySelectorAll('.source-chip').length
          }
        """)
        assert stats["pages"] >= 8, stats
        assert stats["paragraphs"] >= 10, stats
        assert stats["chapters"] >= 2 and stats["scenes"] >= 4, stats
        assert stats["title"], stats
        assert stats["primary"].startswith("#"), stats
        assert stats["sourceLink"].startswith("blob:"), stats
        assert stats["overflow"] <= 2, stats
        assert stats["microDots"] == stats["scenes"], stats
        assert stats["sourceButtons"] >= stats["scenes"]-1, stats
        if label == "desktop":
            payload=d.execute_script("""
              const e=window.__storyscro.getEvidence(), s=window.__storyscro.getStory();
              const cleanE=JSON.parse(JSON.stringify(e,(k,v)=>k.startsWith('_')?undefined:(k==='snapshots'?Object.fromEntries(Object.keys(v||{}).map(p=>[p,'[asset]'])):v)));
              const cleanS=JSON.parse(JSON.stringify(s,(k,v)=>k==='uri'&&String(v).startsWith('data:')?'[asset]':v));
              return {evidence:cleanE,story:cleanS};
            """)
            (OUT/"browser-evidence.json").write_text(json.dumps(payload["evidence"],indent=2),encoding="utf-8")
            (OUT/"browser-story.json").write_text(json.dumps(payload["story"],indent=2),encoding="utf-8")
        d.save_screenshot(str(OUT/f"{label}-hero.png"))
        scrolly=d.find_elements(By.CSS_SELECTOR,".story-scene.scrolly")
        if scrolly:
            d.execute_script("arguments[0].scrollIntoView({block:'start'}); window.scrollBy(0, arguments[0].offsetHeight*0.32)",scrolly[min(1,len(scrolly)-1)])
            time.sleep(.7)
            d.save_screenshot(str(OUT/f"{label}-scrolly.png"))
        severe=[x for x in d.get_log("browser") if x.get("level")=="SEVERE" and "favicon.ico" not in x.get("message","")]
        if severe: raise RuntimeError("Browser console errors: "+json.dumps(severe))
        print(json.dumps({"label":label,**stats},indent=2))
        return stats
    finally:
        d.quit()

desktop=run("desktop",1440,1000)
mobile=run("mobile",390,844)
(Path(OUT/"report.json")).write_text(json.dumps({"desktop":desktop,"mobile":mobile},indent=2),encoding="utf-8")
