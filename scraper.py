"""
scraper.py — FX Dashboard Auto-Updater
"""
import os, re, sys, time, json, logging, argparse, types, importlib.util
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("scraper.log", encoding="utf-8")],
)
log = logging.getLogger("fx_scraper")

DATA_FILE = Path(__file__).parent / "data.py"
FRED_KEY  = os.getenv("FRED_API_KEY", "")
AV_KEY    = os.getenv("ALPHAVANTAGE_KEY", "")
GNEWS_KEY = os.getenv("GNEWS_API_KEY", "a2530359ee05f25e94ec6ebc10eff403")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept": "application/json, text/html, */*"}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)
CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "NZD", "CHF"]

def _get(url, params=None, retries=3, delay=3):
    for i in range(retries):
        try:
            r = SESSION.get(url, params=params, timeout=15)
            if r.status_code == 200: return r
            if r.status_code == 429: time.sleep(delay * (i + 2))
            else: time.sleep(delay)
        except requests.RequestException: time.sleep(delay)
    return None

def scrape_fx_frankfurter():
    log.info("[FX] Frankfurter (ECB)...")
    r = _get("https://api.frankfurter.app/latest", params={"from": "USD"})
    if not r: return {}
    ecb = r.json().get("rates", {})
    def rate(ccy, direct):
        v = ecb.get(ccy)
        return None if v is None else (round(v, 5) if direct else round(1/v, 5))
    pairs = {k: rate(c, d) for k, (c, d) in {
        "EUR/USD":("EUR",False),"GBP/USD":("GBP",False),"USD/JPY":("JPY",True),
        "USD/CAD":("CAD",True),"AUD/USD":("AUD",False),"NZD/USD":("NZD",False),"USD/CHF":("CHF",True)
    }.items()}
    pairs = {k: v for k, v in pairs.items() if v}
    def cross(a, b, op="mul"):
        av, bv = pairs.get(a), pairs.get(b)
        return round(av*bv if op=="mul" else av/bv, 5) if av and bv else None
    extras = {"EUR/GBP":cross("EUR/USD","GBP/USD","div"),"GBP/JPY":cross("GBP/USD","USD/JPY"),
               "EUR/CAD":cross("EUR/USD","USD/CAD"),"GBP/CAD":cross("GBP/USD","USD/CAD"),
               "EUR/CHF":cross("EUR/USD","USD/CHF"),"AUD/NZD":cross("AUD/USD","NZD/USD","div")}
    if pairs.get("USD/CAD") and pairs.get("USD/CHF"):
        extras["CAD/CHF"] = round((1/pairs["USD/CAD"])*pairs["USD/CHF"], 5)
    result = {p: {"rate":v,"chg":0.0,"wchg":0.0} for p,v in {**pairs,**extras}.items() if v}
    try:
        today = datetime.now(timezone.utc).date()
        prev_day = today - timedelta(days=1 if today.weekday()>0 else 3)
        r2 = _get(f"https://api.frankfurter.app/{prev_day}", params={"from": "USD"})
        if r2:
            prev = r2.json().get("rates", {})
            for pair, (ccy, direct) in {"EUR/USD":("EUR",False),"GBP/USD":("GBP",False),"USD/JPY":("JPY",True),"USD/CAD":("CAD",True),"AUD/USD":("AUD",False),"NZD/USD":("NZD",False),"USD/CHF":("CHF",True)}.items():
                if pair in result and ccy in prev and ccy in ecb:
                    chg = (ecb[ccy]-prev[ccy])/prev[ccy]*100
                    if not direct: chg = -chg
                    result[pair]["chg"] = round(chg, 2)
                    result[pair]["wchg"] = round(chg*4, 1)
    except Exception as e: log.debug(f"FX change: {e}")
    log.info(f"[FX] {len(result)} pairs scraped")
    return result

def fred(series_id):
    if not FRED_KEY: return None
    time.sleep(0.4)
    r = _get("https://api.stlouisfed.org/fred/series/observations", params={"series_id":series_id,"api_key":FRED_KEY,"limit":3,"sort_order":"desc","file_type":"json"})
    if not r: return None
    try:
        for obs in r.json()["observations"]:
            v = obs.get("value",".")
            if v not in (".","",None):
                val = round(float(v),3)
                log.info(f"  FRED {series_id} = {val} ({obs['date']})")
                return val
    except Exception as e: log.debug(f"FRED {series_id}: {e}")
    return None

def scrape_fred_all():
    if not FRED_KEY: log.warning("[FRED] No API key."); return {}, {}
    log.info("\n[FRED] Scraping macro + yields...")
    macro = {}
    usd = {}
    for field, sid in [("cpi","CPIAUCSL"),("unem","UNRATE"),("gdp","A191RL1Q225SBEA"),("wages","CES0500000003"),("retail","RSAFS"),("conf","UMCSENT")]:
        v = fred(sid)
        if v is not None: usd[field] = v
    if usd: macro["USD"] = usd
    yields = {}
    usd_y = {}
    y2, y10 = fred("DGS2"), fred("DGS10")
    if y2: usd_y["yield_2y"] = y2
    if y10: usd_y["yield_10y"] = y10
    if y2 and y10: usd_y["curve_slope"] = round(y10-y2, 2)
    if usd_y: yields["USD"] = usd_y
    for ccy, sid in {"EUR":"IRLTLT01EZM156N","GBP":"IRLTLT01GBM156N","JPY":"IRLTLT01JPM156N","CAD":"IRLTLT01CAM156N","AUD":"IRLTLT01AUM156N","CHF":"IRLTLT01CHM156N"}.items():
        v = fred(sid)
        if v is not None:
            entry = {"yield_10y": v}
            if y10: entry["spread_10y_vs_usd"] = round(v-y10, 2)
            yields[ccy] = entry
    log.info(f"[FRED] macro:{sum(len(v) for v in macro.values())} | yields:{len(yields)} ccys")
    return macro, yields

WB_ISO = {"USD":"US","EUR":"XC","GBP":"GB","JPY":"JP","CAD":"CA","AUD":"AU","NZD":"NZ","CHF":"CH"}
WB_INDICATORS = {"cpi":"FP.CPI.TOTL.ZG","unem":"SL.UEM.TOTL.ZS","gdp":"NY.GDP.MKTP.KD.ZG"}

def worldbank(iso, indicator):
    time.sleep(0.8)
    r = _get(f"https://api.worldbank.org/v2/country/{iso}/indicator/{indicator}", params={"format":"json","mrv":3,"per_page":5})
    if not r: return None
    try:
        for obs in r.json()[1]:
            v = obs.get("value")
            if v is not None:
                val = round(float(v),2)
                log.info(f"  WorldBank {iso}/{indicator} = {val} ({obs.get('date')})")
                return val
    except: pass
    return None

def scrape_worldbank_all():
    log.info("\n[WorldBank] Scraping macro (annual)...")
    macro = {}
    for ccy in CURRENCIES:
        iso = WB_ISO.get(ccy)
        if not iso: continue
        d = {}
        for field, ind in WB_INDICATORS.items():
            v = worldbank(iso, ind)
            if v is not None: d[field] = v
        if d: macro[ccy] = d
    log.info(f"[WorldBank] {sum(len(v) for v in macro.values())} fields across {len(macro)} ccys")
    return macro

def scrape_news():
    """Fetch news via GNews — saved to JSON file, NO regex patching."""
    if not GNEWS_KEY: log.info("[News] No GNews key"); return []
    log.info("[News] Fetching via GNews...")
    try:
        r = _get("https://gnews.io/api/v4/search", params={
            "q": "Fed OR ECB OR BoJ OR BoE OR RBA OR inflation OR interest rate",
            "lang":"en","max":10,"apikey":GNEWS_KEY,"sortby":"publishedAt"
        })
        if not r: return []
        articles = r.json().get("articles", [])
        result = []
        for art in articles:
            ts = art.get("publishedAt","")
            try: ts = datetime.fromisoformat(ts.replace("Z","+00:00")).strftime("%d %b %H:%M")
            except: ts = datetime.now(timezone.utc).strftime("%d %b %H:%M")
            title = art.get("title","")[:120]
            body  = art.get("description","")[:400]
            text  = (title+" "+body).lower()
            ccys = []
            if any(k in text for k in ["fed","powell","dollar","usd"]): ccys.append("USD")
            if any(k in text for k in ["ecb","lagarde","euro"]):        ccys.append("EUR")
            if any(k in text for k in ["boe","bailey","sterling"]):     ccys.append("GBP")
            if any(k in text for k in ["boj","ueda","yen"]):            ccys.append("JPY")
            if any(k in text for k in ["rba","australia"]):             ccys.append("AUD")
            if any(k in text for k in ["rbnz","zealand"]):              ccys.append("NZD")
            if any(k in text for k in ["boc","canada"]):                ccys.append("CAD")
            if any(k in text for k in ["snb","swiss"]):                 ccys.append("CHF")
            if not ccys: ccys = ["USD"]
            direction = "positive" if any(k in text for k in ["hike","hawkish","beat","surge"]) else "negative" if any(k in text for k in ["cut","dovish","miss","collapse"]) else "mixed"
            cat = "Central Bank" if any(k in text for k in ["fed","ecb","boj","boe","rba","rbnz","boc","snb"]) else "Geopolitics"
            result.append({"ts":ts,"title":title,"body":body,"cat":cat,"ccys":list(set(ccys)),"dir":direction})
        log.info(f"[News] {len(result)} articles")
        return result
    except Exception as e: log.error(f"[News] {e}"); return []

def save_news_cache(news_list):
    """Write news to JSON file — completely avoids regex and unicode issues."""
    if not news_list: return
    news_file = DATA_FILE.parent / "news_cache.json"
    try:
        with open(news_file, "w", encoding="utf-8") as f:
            json.dump(news_list, f, ensure_ascii=False, indent=2)
        log.info(f"✓ news_cache.json — {len(news_list)} articles")
    except Exception as e: log.error(f"✗ news cache: {e}")

def _patch_value(content, dict_name, ccy, key, new_val):
    val_str = str(round(new_val,4)) if isinstance(new_val,float) else str(new_val)
    pattern = re.compile(rf'({re.escape(dict_name)}\s*=\s*\{{.*?"{re.escape(ccy)}"\s*:\s*\{{)(.*?)(\n    \}},)', re.DOTALL)
    m = pattern.search(content)
    if not m: return content, False
    block = m.group(2)
    kpat  = re.compile(rf'("{re.escape(key)}"\s*:\s*)(-?[\d.]+)')
    replaced = [False]
    def replacer(km):
        if replaced[0]: return km.group(0)
        replaced[0] = True
        return km.group(1) + val_str
    new_block = kpat.sub(replacer, block, count=1)
    if replaced[0]:
        return content[:m.start()] + m.group(1) + new_block + m.group(3) + content[m.end():], True
    return content, False

def patch_dict(dict_name, updates, label=""):
    try:
        content = DATA_FILE.read_text(encoding="utf-8")
        original = content
        count = 0
        for ccy, fields in updates.items():
            for key, val in fields.items():
                if val is None: continue
                content, ok = _patch_value(content, dict_name, ccy, key, val)
                if ok: count += 1
                else: log.warning(f"  Could not patch {dict_name}[{ccy}][{key}]")
        if content != original: DATA_FILE.write_text(content, encoding="utf-8")
        log.info(f"✓ {dict_name} patched — {count} fields {label}")
        return count
    except Exception as e: log.error(f"✗ {dict_name}: {e}"); return 0

def patch_yield_history(yield_updates):
    try:
        content = DATA_FILE.read_text(encoding="utf-8")
        original = content
        count = 0
        for ccy, updates in yield_updates.items():
            for hist_key, val_key in [("yield_2y_hist","yield_2y"),("yield_10y_hist","yield_10y")]:
                if val_key not in updates: continue
                new_val = round(updates[val_key], 2)
                pat = re.compile(rf'(RATE_EXP\s*=\s*\{{.*?"{re.escape(ccy)}"\s*:\s*\{{.*?"{re.escape(hist_key)}"\s*:\s*\[)([^\]]+)(\])', re.DOTALL)
                m = pat.search(content)
                if m:
                    old = [float(x.strip()) for x in m.group(2).split(",") if x.strip()]
                    new = old[1:] + [new_val]
                    repl = m.group(1) + ", ".join(str(v) for v in new) + m.group(3)
                    content = content[:m.start()] + repl + content[m.end():]
                    count += 1
        if content != original: DATA_FILE.write_text(content, encoding="utf-8")
        log.info(f"✓ Yield history updated — {count} arrays")
    except Exception as e: log.error(f"✗ Yield history: {e}")

def run_full_scrape(currencies=None):
    start = datetime.now(timezone.utc)
    log.info(f"\n{'='*55}")
    log.info(f"FX Scraper — {start.strftime('%Y-%m-%d %H:%M UTC')}")
    log.info(f"FRED key:  {'SET' if FRED_KEY  else 'MISSING'}")
    log.info(f"GNews key: {'SET' if GNEWS_KEY else 'not set'}")
    log.info(f"{'='*55}")

    fx_data              = scrape_fx_frankfurter()
    fred_macro, fred_yields = scrape_fred_all()
    wb_macro             = scrape_worldbank_all()

    all_macro = {}
    for ccy in CURRENCIES:
        merged = {}
        merged.update(wb_macro.get(ccy, {}))
        merged.update(fred_macro.get(ccy, {}))
        if merged: all_macro[ccy] = merged

    log.info(f"\n── Patching data.py ──")
    patch_dict("MACRO",    all_macro,   f"({sum(len(v) for v in all_macro.values())} total fields)")
    patch_dict("RATE_EXP", fred_yields, f"({len(fred_yields)} currencies)")
    patch_yield_history(fred_yields)
    patch_dict("FX_RATES", fx_data,     f"({len(fx_data)} pairs)")

    log.info(f"\n── News ──")
    save_news_cache(scrape_news())

    try:
        spec = importlib.util.spec_from_file_location("data", DATA_FILE)
        mod  = types.ModuleType("data")
        spec.loader.exec_module(mod)
        mod.save_snapshot("scraper")
        log.info("✓ DB snapshot saved")
    except Exception as e: log.warning(f"DB snapshot: {e}")

    elapsed = round((datetime.now(timezone.utc)-start).total_seconds(), 1)
    log.info(f"\n{'='*55}")
    log.info(f"Completed in {elapsed}s")
    log.info(f"{'='*55}\n")

def run_scheduler():
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger
    log.info("Scheduler: London 17:05 UTC + NY 22:05 UTC (Mon-Fri)")
    run_full_scrape()
    sched = BlockingScheduler(timezone="UTC")
    sched.add_job(run_full_scrape, CronTrigger(day_of_week="mon-fri", hour=17, minute=5), id="london", misfire_grace_time=600)
    sched.add_job(run_full_scrape, CronTrigger(day_of_week="mon-fri", hour=22, minute=5), id="ny",     misfire_grace_time=600)
    try: sched.start()
    except (KeyboardInterrupt, SystemExit): log.info("Stopped.")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--schedule", action="store_true")
    p.add_argument("--test",     action="store_true")
    p.add_argument("--fx-only",  action="store_true")
    args = p.parse_args()
    if args.schedule: run_scheduler()
    elif args.test:
        fx = scrape_fx_frankfurter()
        for pair, d in list(fx.items())[:6]: log.info(f"  {pair}: {d['rate']} ({d['chg']:+.2f}%)")
    elif args.fx_only: patch_dict("FX_RATES", scrape_fx_frankfurter())
    else: run_full_scrape()
