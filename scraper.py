"""
scraper.py — FX Dashboard Auto-Updater
=======================================
Sources gratuites qui fonctionnent sur GitHub Actions :

  FX Rates    → Frankfurter API (ECB official, AUCUNE clé)
  Bond yields → FRED API (St Louis Fed, clé GRATUITE en 2 min)
  Macro data  → World Bank API (AUCUNE clé)
  Fallback FX → Alpha Vantage (clé GRATUITE, optionnelle)

Clés à obtenir (gratuites) :
  FRED_KEY  → https://fred.stlouisfed.org/docs/api/api_key.html
  AV_KEY    → https://www.alphavantage.co/support/#api-key (optionnel)

Ajouter dans GitHub Secrets :
  FRED_API_KEY      = ta clé FRED
  ALPHAVANTAGE_KEY  = ta clé AV (optionnel)

Usage local :
  python scraper.py              # scrape tout maintenant
  python scraper.py --schedule   # scheduler London + NY close
  python scraper.py --test       # test rapide FX uniquement
"""

import os, re, sys, time, json, logging, argparse, types, importlib.util
from datetime import datetime, timezone, timedelta
from pathlib import Path
from news_scraper import fetch_financial_juice
import requests

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scraper.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("fx_scraper")

# ── Config ────────────────────────────────────────────────────────
DATA_FILE = Path(__file__).parent / "data.py"
FRED_KEY  = os.getenv("FRED_API_KEY", "")
AV_KEY    = os.getenv("ALPHAVANTAGE_KEY", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "NZD", "CHF"]


# ── HTTP helper ───────────────────────────────────────────────────
def _get(url, params=None, retries=3, delay=3):
    for i in range(retries):
        try:
            r = SESSION.get(url, params=params, timeout=15)
            if r.status_code == 200:
                return r
            if r.status_code == 429:
                time.sleep(delay * (i + 2))
            else:
                log.debug(f"HTTP {r.status_code}: {url[:60]}")
                time.sleep(delay)
        except requests.RequestException as e:
            log.debug(f"Attempt {i+1}: {e}")
            time.sleep(delay)
    return None


# ══════════════════════════════════════════════════════════════════
# SOURCE 1 — FRANKFURTER (ECB FX, no key, 100% reliable)
# https://www.frankfurter.app
# ══════════════════════════════════════════════════════════════════

def scrape_fx_frankfurter():
    """ECB official FX rates via Frankfurter. No key needed."""
    log.info("[FX] Frankfurter (ECB)...")
    r = _get("https://api.frankfurter.app/latest", params={"from": "USD"})
    if not r:
        log.error("[FX] Frankfurter failed")
        return {}

    ecb = r.json().get("rates", {})
    # ecb = {"EUR": 0.928, "GBP": 0.791, "JPY": 154.2, ...} (per 1 USD)

    def rate(ccy, direct):
        v = ecb.get(ccy)
        if v is None:
            return None
        return round(v, 5) if direct else round(1 / v, 5)

    pairs = {
        "EUR/USD": rate("EUR", False),
        "GBP/USD": rate("GBP", False),
        "USD/JPY": rate("JPY", True),
        "USD/CAD": rate("CAD", True),
        "AUD/USD": rate("AUD", False),
        "NZD/USD": rate("NZD", False),
        "USD/CHF": rate("CHF", True),
    }
    pairs = {k: v for k, v in pairs.items() if v is not None}

    # Cross pairs
    def cross(a, b, op="mul"):
        av, bv = pairs.get(a), pairs.get(b)
        if av and bv:
            return round(av * bv if op == "mul" else av / bv, 5)
        return None

    extras = {
        "EUR/GBP": cross("EUR/USD", "GBP/USD", "div") if pairs.get("EUR/USD") and pairs.get("GBP/USD") else None,
        "GBP/JPY": cross("GBP/USD", "USD/JPY", "mul"),
        "EUR/CAD": cross("EUR/USD", "USD/CAD", "mul"),
        "GBP/CAD": cross("GBP/USD", "USD/CAD", "mul"),
        "EUR/CHF": cross("EUR/USD", "USD/CHF", "mul"),
        "AUD/NZD": cross("AUD/USD", "NZD/USD", "div") if pairs.get("AUD/USD") and pairs.get("NZD/USD") else None,
    }
    if pairs.get("USD/CAD") and pairs.get("USD/CHF"):
        extras["CAD/CHF"] = round((1 / pairs["USD/CAD"]) * pairs["USD/CHF"], 5)

    result = {}
    for pair, v in {**pairs, **extras}.items():
        if v:
            result[pair] = {"rate": v, "chg": 0.0, "wchg": 0.0}

    # Daily change — compare with yesterday
    try:
        today    = datetime.now(timezone.utc).date()
        weekday  = today.weekday()
        prev_day = today - timedelta(days=1 if weekday > 0 else 3)
        r2 = _get(f"https://api.frankfurter.app/{prev_day}", params={"from": "USD"})
        if r2:
            prev = r2.json().get("rates", {})
            for pair, (ccy, direct) in {
                "EUR/USD": ("EUR", False), "GBP/USD": ("GBP", False),
                "USD/JPY": ("JPY", True),  "USD/CAD": ("CAD", True),
                "AUD/USD": ("AUD", False), "NZD/USD": ("NZD", False),
                "USD/CHF": ("CHF", True),
            }.items():
                if pair in result and ccy in prev and ccy in ecb:
                    curr_usd = ecb[ccy]
                    prev_usd = prev[ccy]
                    chg = (curr_usd - prev_usd) / prev_usd * 100
                    if not direct:
                        chg = -chg
                    result[pair]["chg"]  = round(chg, 2)
                    result[pair]["wchg"] = round(chg * 4, 1)
    except Exception as e:
        log.debug(f"FX change calc: {e}")

    log.info(f"[FX] {len(result)} pairs scraped")
    return result


# ══════════════════════════════════════════════════════════════════

#def patch_news(news_list):
 #   """Save news to a separate JSON file."""
 #   import json
 #   news_file = DATA_FILE.parent / "news_cache.json"
 #   try:
 #       with open(news_file, "w", encoding="utf-8") as f:
 #           json.dump(news_list, f, ensure_ascii=False, indent=2)
 #       log.info(f"✓ NEWS saved to news_cache.json — {len(news_list)} articles")
 #       return True
 #   except Exception as e:
 #       log.error(f"✗ NEWS save error: {e}")
 #       return False
# ══════════════════════════════════════════════════════════════════
# SOURCE 2 — FRED (St Louis Fed, free key, best quality)
# https://fred.stlouisfed.org/docs/api/api_key.html
# ══════════════════════════════════════════════════════════════════

def fred(series_id):
    """Fetch latest FRED series value."""
    if not FRED_KEY:
        return None
    time.sleep(0.4)
    r = _get("https://api.stlouisfed.org/fred/series/observations", params={
        "series_id": series_id, "api_key": FRED_KEY,
        "limit": 3, "sort_order": "desc", "file_type": "json",
    })
    if not r:
        return None
    try:
        for obs in r.json()["observations"]:
            v = obs.get("value", ".")
            if v not in (".", "", None):
                val = round(float(v), 3)
                log.info(f"  FRED {series_id} = {val} ({obs['date']})")
                return val
    except Exception as e:
        log.debug(f"FRED {series_id}: {e}")
    return None


def scrape_fred_all():
    """Scrape all FRED series — macro + yields."""
    if not FRED_KEY:
        log.warning("[FRED] No API key. Get free key at fred.stlouisfed.org")
        return {}, {}

    log.info("\n[FRED] Scraping macro + yields...")

    macro = {}
    # USD macro
    usd = {}
    for field, sid in [
        ("cpi",    "CPIAUCSL"),
        ("unem",   "UNRATE"),
        ("gdp",    "A191RL1Q225SBEA"),
        ("wages",  "CES0500000003"),
        ("retail", "RSAFS"),
        ("conf",   "UMCSENT"),
    ]:
        v = fred(sid)
        if v is not None:
            usd[field] = v
    if usd:
        macro["USD"] = usd

    # Yields
    yields = {}

    # USD Treasuries
    usd_y = {}
    y2  = fred("DGS2")
    y10 = fred("DGS10")
    if y2:  usd_y["yield_2y"]  = y2
    if y10: usd_y["yield_10y"] = y10
    if y2 and y10:
        usd_y["curve_slope"] = round(y10 - y2, 2)
    if usd_y:
        yields["USD"] = usd_y

    # Other country 10Y yields (FRED has OECD series)
    intl_10y = {
        "EUR": "IRLTLT01EZM156N",
        "GBP": "IRLTLT01GBM156N",
        "JPY": "IRLTLT01JPM156N",
        "CAD": "IRLTLT01CAM156N",
        "AUD": "IRLTLT01AUM156N",
        "CHF": "IRLTLT01CHM156N",
    }
    for ccy, sid in intl_10y.items():
        v = fred(sid)
        if v is not None:
            entry = {"yield_10y": v}
            # Compute spread vs USD 10Y
            if y10:
                entry["spread_10y_vs_usd"] = round(v - y10, 2)
            yields[ccy] = entry

    log.info(f"[FRED] macro:{sum(len(v) for v in macro.values())} fields | yields:{len(yields)} ccys")
    return macro, yields


# ══════════════════════════════════════════════════════════════════
# SOURCE 3 — WORLD BANK (no key, annual data)
# https://api.worldbank.org
# ══════════════════════════════════════════════════════════════════

WB_ISO = {
    "USD":"US","EUR":"XC","GBP":"GB","JPY":"JP",
    "CAD":"CA","AUD":"AU","NZD":"NZ","CHF":"CH",
}
WB_INDICATORS = {
    "cpi":  "FP.CPI.TOTL.ZG",
    "unem": "SL.UEM.TOTL.ZS",
    "gdp":  "NY.GDP.MKTP.KD.ZG",
}

def worldbank(iso, indicator):
    time.sleep(0.8)
    r = _get(f"https://api.worldbank.org/v2/country/{iso}/indicator/{indicator}",
             params={"format": "json", "mrv": 3, "per_page": 5})
    if not r:
        return None
    try:
        for obs in r.json()[1]:
            v = obs.get("value")
            if v is not None:
                val = round(float(v), 2)
                log.info(f"  WorldBank {iso}/{indicator} = {val} ({obs.get('date')})")
                return val
    except Exception as e:
        log.debug(f"WorldBank {iso}/{indicator}: {e}")
    return None

def scrape_worldbank_all():
    log.info("\n[WorldBank] Scraping macro (annual)...")
    macro = {}
    for ccy in CURRENCIES:
        iso = WB_ISO.get(ccy)
        if not iso:
            continue
        ccy_data = {}
        for field, indicator in WB_INDICATORS.items():
            v = worldbank(iso, indicator)
            if v is not None:
                ccy_data[field] = v
        if ccy_data:
            macro[ccy] = ccy_data
    log.info(f"[WorldBank] {sum(len(v) for v in macro.values())} fields across {len(macro)} ccys")
    return macro


# ══════════════════════════════════════════════════════════════════
# PATCH data.py
# ══════════════════════════════════════════════════════════════════

def _patch_value(content, dict_name, ccy, key, new_val):
    """Replace a numeric value inside dict_name["ccy"]["key"]."""
    val_str = str(round(new_val, 4)) if isinstance(new_val, float) else str(new_val)

    pattern = re.compile(
        rf'({re.escape(dict_name)}\s*=\s*\{{.*?"{re.escape(ccy)}"\s*:\s*\{{)(.*?)(\n    \}},)',
        re.DOTALL
    )
    m = pattern.search(content)
    if not m:
        return content, False
    block = m.group(2)
    kpat  = re.compile(rf'("{re.escape(key)}"\s*:\s*)(-?[\d.]+)')

    # Use lambda to avoid re.sub treating val_str as a replacement template
    # (fixes bad escape \u error when val_str contains backslashes)
    replaced = [False]
    def replacer(km):
        if replaced[0]:
            return km.group(0)
        replaced[0] = True
        return km.group(1) + val_str

    new_block = kpat.sub(replacer, block, count=1)
    n = 1 if replaced[0] else 0
    if n:
        new_content = content[:m.start()] + m.group(1) + new_block + m.group(3) + content[m.end():]
        return new_content, True
    return content, False

def patch_dict(dict_name, updates, label=""):
    try:
        content  = DATA_FILE.read_text(encoding="utf-8")
        original = content
        count    = 0
        for ccy, fields in updates.items():
            for key, val in fields.items():
                if val is None:
                    continue
                content, ok = _patch_value(content, dict_name, ccy, key, val)
                if ok:
                    count += 1
                    log.debug(f"  {dict_name}[{ccy}][{key}] = {val}")
                else:
                    log.warning(f"  Could not patch {dict_name}[{ccy}][{key}]")
        if content != original:
            DATA_FILE.write_text(content, encoding="utf-8")
        log.info(f"✓ {dict_name} patched — {count} fields {label}")
        return count
    except Exception as e:
        log.error(f"✗ {dict_name} patch error: {e}")
        return 0

def patch_yield_history(yield_updates):
    """Shift yield history arrays and append new value."""
    try:
        content  = DATA_FILE.read_text(encoding="utf-8")
        original = content
        count    = 0
        for ccy, updates in yield_updates.items():
            for hist_key, val_key in [("yield_2y_hist","yield_2y"),("yield_10y_hist","yield_10y")]:
                if val_key not in updates:
                    continue
                new_val = round(updates[val_key], 2)
                pat = re.compile(
                    rf'(RATE_EXP\s*=\s*\{{.*?"{re.escape(ccy)}"\s*:\s*\{{.*?'
                    rf'"{re.escape(hist_key)}"\s*:\s*\[)([^\]]+)(\])',
                    re.DOTALL
                )
                m = pat.search(content)
                if m:
                    old  = [float(x.strip()) for x in m.group(2).split(",") if x.strip()]
                    new  = old[1:] + [new_val]
                    # Build replacement safely avoiding re.sub template interpretation
                    repl_str  = m.group(1) + ", ".join(str(v) for v in new) + m.group(3)
                    content   = content[:m.start()] + repl_str + content[m.end():]
                    count += 1
        if content != original:
            DATA_FILE.write_text(content, encoding="utf-8")
            log.info(f"✓ Yield history updated — {count} arrays")
    except Exception as e:
        log.error(f"✗ Yield history patch error: {e}")


# ══════════════════════════════════════════════════════════════════
# FULL SCRAPE
# ══════════════════════════════════════════════════════════════════

def run_full_scrape(currencies=None):
    start = datetime.now(timezone.utc)
    log.info(f"\n{'='*55}")
    log.info(f"FX Scraper — {start.strftime('%Y-%m-%d %H:%M UTC')}")
    log.info(f"FRED key: {'SET' if FRED_KEY else 'MISSING (yields skipped)'}")
    log.info(f"AV key:   {'SET' if AV_KEY else 'not set (optional)'}")
    log.info(f"{'='*55}")

    # 1. FX rates (no key needed)
    fx_data = scrape_fx_frankfurter()

    # 2. FRED — macro USD + bond yields
    fred_macro, fred_yields = scrape_fred_all()

    # 3. World Bank — macro all currencies (annual)
    wb_macro = scrape_worldbank_all()

    # 4. Merge macro: FRED (fresher) wins, WB fills gaps
    all_macro = {}
    for ccy in CURRENCIES:
        merged = {}
        merged.update(wb_macro.get(ccy, {}))    # WB first (annual)
        merged.update(fred_macro.get(ccy, {}))  # FRED overwrites (monthly)
        if merged:
            all_macro[ccy] = merged

    # 5. Patch data.py
    log.info(f"\n── Patching data.py ──")
    patch_dict("MACRO",    all_macro,   f"({sum(len(v) for v in all_macro.values())} total fields)")
    patch_dict("RATE_EXP", fred_yields, f"({len(fred_yields)} currencies)")
    patch_yield_history(fred_yields)
    patch_dict("FX_RATES", {p: d for p, d in fx_data.items()}, f"({len(fx_data)} pairs)")

        # 6. Récupérer les actualités
    log.info("\n── Actualités ──")
    news = fetch_financial_juice()
    if news:
        patch_news(news)
    else:
        log.warning("Aucune actualité récupérée")
    # 6. Save DB snapshot
    try:
        spec = importlib.util.spec_from_file_location("data", DATA_FILE)
        mod  = types.ModuleType("data")
        spec.loader.exec_module(mod)
        mod.save_snapshot("scraper")
        log.info("✓ DB snapshot saved")
    except Exception as e:
        log.warning(f"DB snapshot: {e}")

    elapsed = round((datetime.now(timezone.utc) - start).total_seconds(), 1)
    log.info(f"\n{'='*55}")
    log.info(f"Completed in {elapsed}s")
    log.info(f"{'='*55}\n")


# ══════════════════════════════════════════════════════════════════
# SCHEDULER
# ══════════════════════════════════════════════════════════════════

def run_scheduler():
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger

    log.info("Scheduler: London 17:05 UTC + NY 22:05 UTC (Mon-Fri)")
    run_full_scrape()

    sched = BlockingScheduler(timezone="UTC")
    sched.add_job(run_full_scrape, CronTrigger(day_of_week="mon-fri", hour=17, minute=5),
                  id="london", misfire_grace_time=600)
    sched.add_job(run_full_scrape, CronTrigger(day_of_week="mon-fri", hour=22, minute=5),
                  id="ny", misfire_grace_time=600)
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Stopped.")


# ══════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--schedule", action="store_true")
    p.add_argument("--test",     action="store_true", help="Test FX only")
    p.add_argument("--fx-only",  action="store_true")
    args = p.parse_args()

    if args.schedule:
        run_scheduler()
    elif args.test:
        fx = scrape_fx_frankfurter()
        for pair, d in list(fx.items())[:6]:
            log.info(f"  {pair}: {d['rate']} ({d['chg']:+.2f}%)")
        patch_dict("FX_RATES", fx)
    elif args.fx_only:
        patch_dict("FX_RATES", scrape_fx_frankfurter())
    else:
        run_full_scrape()
