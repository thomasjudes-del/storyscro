from pathlib import Path
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

OUT = Path("visual-artifacts")
OUT.mkdir(exist_ok=True)
BASE = "http://127.0.0.1:4173/v2/"

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1440,1000")
options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

driver = webdriver.Chrome(options=options)

desktop_shots = [
    ("00-hero", None, 0.0),
    ("01-decisions-a", "decisions", 0.10),
    ("02-decisions-c", "decisions", 0.78),
    ("03-vulnerabilities-grid", "vulnerabilities", 0.05),
    ("04-vulnerabilities-focus", "vulnerabilities", 0.58),
    ("05-arbitrage", "matrix", 0.70),
    ("06-method", "method", 0.55),
    ("07-planning", "planning", 0.82),
    ("08-workshops", "workshops", 0.70),
    ("09-deliverables", "deliverables", 0.64),
    ("10-proof", "proof", 0.68),
]

mobile_shots = [
    ("m00-hero", None, 0.0),
    ("m01-decisions", "decisions", 0.72),
    ("m02-vulnerabilities", "vulnerabilities", 0.58),
    ("m03-arbitrage", "matrix", 0.70),
    ("m04-method", "method", 0.55),
    ("m05-planning", "planning", 0.82),
    ("m06-workshops", "workshops", 0.70),
    ("m07-deliverables", "deliverables", 0.64),
    ("m08-proof", "proof", 0.68),
]

report = {"sets": [], "shots": [], "console": []}

def capture_set(label, width, height, shots):
    driver.set_window_size(width, height)
    driver.get(BASE)
    time.sleep(2.0)
    actual = driver.execute_script("return [window.innerWidth, window.innerHeight]")
    report["sets"].append({"label": label, "requested": [width, height], "actual": actual})

    for name, scene, progress in shots:
        if scene is None:
            driver.execute_script("window.scrollTo(0,0)")
        else:
            result = driver.execute_script(
                """
                const scene = arguments[0], p = arguments[1];
                const el = document.querySelector(`[data-scene="${scene}"]`);
                if (!el) return {ok:false, scene};
                const span = Math.max(1, el.offsetHeight - window.innerHeight);
                window.scrollTo(0, el.offsetTop + span * p);
                return {ok:true, scene, top:el.offsetTop, height:el.offsetHeight, span};
                """,
                scene,
                progress,
            )
            if not result or not result.get("ok"):
                raise RuntimeError(f"Scene not found: {scene}")
        time.sleep(0.65)
        dims = driver.execute_script(
            """
            return {
              scrollY: window.scrollY,
              innerWidth: window.innerWidth,
              innerHeight: window.innerHeight,
              scrollWidth: document.documentElement.scrollWidth,
              scrollHeight: document.documentElement.scrollHeight
            };
            """
        )
        if dims["scrollWidth"] > dims["innerWidth"] + 3:
            raise RuntimeError(f"Horizontal overflow at {name}: {dims}")
        path = OUT / f"{name}.png"
        if not driver.save_screenshot(str(path)):
            raise RuntimeError(f"Screenshot failed: {name}")
        report["shots"].append({"set": label, "name": name, "scene": scene, "progress": progress, "dims": dims})

try:
    capture_set("desktop", 1440, 1000, desktop_shots)
    capture_set("mobile", 390, 844, mobile_shots)

    console = driver.get_log("browser")
    report["console"] = console
    severe = [x for x in console if x.get("level") == "SEVERE" and "favicon" not in x.get("message", "").lower()]
    if severe:
        raise RuntimeError("Browser console errors: " + json.dumps(severe, ensure_ascii=False))
finally:
    (OUT / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    driver.quit()

print(f"Visual capture OK: {len(report['shots'])} desktop/mobile viewports, no horizontal overflow or severe console errors.")
