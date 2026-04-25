"""
data.py  —  FX Dashboard data layer
Auto-updates after London close (17:00 UTC) and New York close (22:00 UTC)
All static data + rate expectations + scheduler
"""

import json, sqlite3, threading, time, os
from datetime import datetime, timezone, timedelta

# ─────────────────────────────────────────────────────────────────
# MACRO FUNDAMENTALS  (source: IMF WEO Apr 2026, central banks)
# ─────────────────────────────────────────────────────────────────
MACRO = {
    "USD": {
        "name": "United States", "cb": "Federal Reserve",
        "rate": 4.00, "rate_prev": 4.25,
        "gdp": 0.5,   "gdp_prev": 2.8,
        "cpi": 330.293,   "cpi_prev": 2.9,   "core_cpi": 2.8,
        "unem": 4.3,  "unem_prev": 4.1,
        "wages": 37.38, "retail": 752063.0,
        "conf": 53.3, "ca": -3.2, "pmi": 51.4,
        "next_mtg": "30 Apr 2026",
        "bias": "Neutral / Hawkish", "score": 0,
        "color": "#3b82f6",
        "updated": "22 Apr 2026",
        "news": [
            "US-Iran talks collapsed — safe-haven USD demand elevated",
            "Kevin Warsh (Fed nominee) strikes unexpected hawkish tone",
            "CPI 3.2% — Fed on hold through at least June 2026",
            "NFP +50K Dec — labour market softening gradually",
        ],
        "view": "Dollar supported by rate differential and geopolitical tensions. Downside risk if US data disappoints or Middle East de-escalates.",
    },
    "EUR": {
        "name": "Euro Area", "cb": "European Central Bank",
        "rate": 2.00, "rate_prev": 2.25,
        "gdp": 0.91,   "gdp_prev": 1.2,
        "cpi": 2.5,   "cpi_prev": 2.3,   "core_cpi": 2.3,
        "unem": 6.33,  "unem_prev": 6.5,
        "wages": 3.2, "retail": 0.3,
        "conf": -14.2, "ca": 1.8, "pmi": 50.9,
        "next_mtg": "5 Jun 2026",
        "bias": "Neutral / Cautious", "score": -1,
        "color": "#8b5cf6",
        "updated": "22 Apr 2026",
        "news": [
            "ZEW Germany collapsed to -17.2 (prev -0.5) — recessionary signal",
            "Flash CPI March 2.5% — Iran energy shock feeding through",
            "ECB holds at 2.00% — resisting pressure to hike",
            "PMI Composite 50.9 — fragile expansion",
        ],
        "view": "Euro penalised by energy dependence and German weakness. Recovery conditional on sustained Hormuz reopening.",
    },
    "GBP": {
        "name": "United Kingdom", "cb": "Bank of England",
        "rate": 3.75, "rate_prev": 4.00,
        "gdp": 1.13,   "gdp_prev": 0.9,
        "cpi": 3.27,   "cpi_prev": 3.0,   "core_cpi": 3.1,
        "unem": 4.75,  "unem_prev": 5.1,
        "wages": 5.6, "retail": 0.4,
        "conf": -19.0, "ca": -3.8, "pmi": 50.8,
        "next_mtg": "30 Apr 2026",
        "bias": "Hawkish Near-Term", "score": 2,
        "color": "#10b981",
        "updated": "22 Apr 2026",
        "news": [
            "CPI March 3.3% — services at 4.5% : persistent domestic pressures",
            "Transport +4.9% YoY — fuel the primary driver (Iran war)",
            "Unemployment 4.9% — beat expectations of 5.2%",
            "BoE Apr 30 meeting — rates on hold, hawkish tone expected",
        ],
        "view": "GBP well supported by persistent inflation and hawkish BoE stance. Services CPI at 4.5% prevents any near-term easing.",
    },
    "JPY": {
        "name": "Japan", "cb": "Bank of Japan",
        "rate": 0.75, "rate_prev": 0.50,
        "gdp": 0.1,   "gdp_prev": 0.8,
        "cpi": 2.74,   "cpi_prev": 2.1,   "core_cpi": 1.6,
        "unem": 2.45,  "unem_prev": 2.7,
        "wages": 3.8, "retail": -0.2,
        "conf": 35.0, "ca": 3.2, "pmi": 49.8,
        "next_mtg": "28 Apr 2026",
        "bias": "Hawkish Pivot", "score": 2,
        "color": "#f43f5e",
        "updated": "22 Apr 2026",
        "news": [
            "BoJ Apr 28 meeting — 78% probability of +25bp hike",
            "Ueda signals: yen weakness + inflation justify action",
            "USD/JPY at 159.36 — major reversal risk if BoJ hikes",
            "Wage growth +3.8% — underpins policy normalisation case",
        ],
        "view": "JPY at a critical inflection point. BoJ expected to hike Apr 28. Confirmed hike could trigger USD/JPY move toward 153-155.",
    },
    "CAD": {
        "name": "Canada", "cb": "Bank of Canada",
        "rate": 2.75, "rate_prev": 3.00,
        "gdp": 1.55,   "gdp_prev": 1.3,
        "cpi": 2.38,   "cpi_prev": 1.9,   "core_cpi": 2.2,
        "unem": 6.91,  "unem_prev": 6.3,
        "wages": 4.2, "retail": -0.1,
        "conf": 47.0, "ca": -1.2, "pmi": 48.9,
        "next_mtg": "4 Jun 2026",
        "bias": "Dovish", "score": -2,
        "color": "#f97316",
        "updated": "22 Apr 2026",
        "news": [
            "WTI crude -12% this week — CAD primary driver removed",
            "Speculative positioning firmly short CAD (CFTC data)",
            "Canada CPI Friday — key catalyst for BoC rate path",
            "BoC likely to cut earlier as energy revenues decline",
        ],
        "view": "CAD losing its primary support (oil). Dual pressure from falling energy prices and expected BoC easing — structurally bearish near-term.",
    },
    "AUD": {
        "name": "Australia", "cb": "Reserve Bank of Australia",
        "rate": 3.60, "rate_prev": 3.85,
        "gdp": 1.37,   "gdp_prev": 1.8,
        "cpi": 3.17,   "cpi_prev": 3.6,   "core_cpi": 3.2,
        "unem": 4.09,  "unem_prev": 4.2,
        "wages": 4.5, "retail": 0.5,
        "conf": 85.0, "ca": 1.5, "pmi": 51.2,
        "next_mtg": "6 May 2026",
        "bias": "Hawkish", "score": 2,
        "color": "#eab308",
        "updated": "22 Apr 2026",
        "news": [
            "CPI 3.8% — above RBA 2-3% target band",
            "Labour market tight — unemployment steady at 4.1%",
            "AUD/USD V-shaped recovery from 0.5912 low",
            "RBA rate hike possible as early as Q2 if inflation persists",
        ],
        "view": "AUD well positioned — hawkish RBA, tight labour market, commodity tailwinds, positive China correlation.",
    },
    "NZD": {
        "name": "New Zealand", "cb": "Reserve Bank of New Zealand",
        "rate": 3.50, "rate_prev": 3.75,
        "gdp": 1.29,   "gdp_prev": -1.1,
        "cpi": 2.92,   "cpi_prev": 3.0,   "core_cpi": 3.0,
        "unem": 5.08,  "unem_prev": 5.5,
        "wages": 3.5, "retail": 0.2,
        "conf": 102.0, "ca": -6.5, "pmi": 50.1,
        "next_mtg": "27 May 2026",
        "bias": "Hawkish Surprise", "score": 2,
        "color": "#06b6d4",
        "updated": "21 Apr 2026",
        "news": [
            "CPI Q1 3.1% vs 2.9% expected — NZD surged on release",
            "Electricity +12.5% YoY — inflation above RBNZ target",
            "Business confidence at 30-year high",
            "Markets now pricing 62% probability of May RBNZ hike",
        ],
        "view": "RBNZ hawkish surprise post-CPI beat. Inflation above target and confidence recovering — bullish NZD near-term.",
    },
    "CHF": {
        "name": "Switzerland", "cb": "Swiss National Bank",
        "rate": 0.25, "rate_prev": 0.50,
        "gdp": 1.3,   "gdp_prev": 1.3,
        "cpi": 1.06,   "cpi_prev": 1.1,   "core_cpi": 1.1,
        "unem": 4.87,  "unem_prev": 2.5,
        "wages": 2.0, "retail": 0.1,
        "conf": -8.0, "ca": 8.5, "pmi": 50.5,
        "next_mtg": "19 Jun 2026",
        "bias": "Safe Haven / Neutral", "score": 1,
        "color": "#a855f7",
        "updated": "22 Apr 2026",
        "news": [
            "Safe haven demand elevated — US-Iran talks breakdown",
            "EUR/CHF near lows — SNB cannot counter structural strength",
            "CPI 1.0% — far from peers, no inflation problem",
            "SNB unlikely to act before June",
        ],
        "view": "CHF remains the primary safe haven. SNB structurally limited. As long as geopolitical tensions persist, CHF stays bid.",
    },
}

# ─────────────────────────────────────────────────────────────────
# RATE EXPECTATIONS — based on government bond yield spreads vs USD
# ─────────────────────────────────────────────────────────────────
RATE_EXP = {
    "USD": {
        "current": 4.00, "end_year": 3.50,
        "cuts": 2, "hikes": 0, "bias": "dovish",
        "yield_2y": 3.83, "yield_10y": 4.34,
        "spread_2y_vs_usd":  0.00, "spread_10y_vs_usd": 0.00,
        "curve_slope": 0.51,
        "yield_2y_hist":  [4.6, 4.55, 4.52, 3.83, 3.83, 3.83],
        "yield_10y_hist": [4.78, 4.75, 4.72, 4.34, 4.34, 4.34],
        "ois": {"1m": 4.05, "3m": 3.95, "6m": 3.78, "12m": 3.52},
        "comment": "Benchmark currency. 2Y UST 4.52%, curve +20bps. Markets price 2 cuts H2 2026. USD yield advantage vs peers is narrowing — key risk to dollar strength.",
        "meetings": [
            {"label":"FOMC 30 Apr","chg": 0,  "rate":4.00,"hold":90,"cut": 5,"hike": 5},
            {"label":"FOMC 18 Jun","chg":-25, "rate":3.75,"hold":38,"cut":59,"hike": 3},
            {"label":"FOMC 30 Jul","chg": 0,  "rate":3.75,"hold":55,"cut":43,"hike": 2},
            {"label":"FOMC 17 Sep","chg":-25, "rate":3.50,"hold":52,"cut":46,"hike": 2},
        ],
    },
    "EUR": {
        "current": 2.00, "end_year": 2.25,
        "cuts": 0, "hikes": 1, "bias": "hawkish_risk",
        "yield_2y": 2.38, "yield_10y": 3.221,
        "spread_2y_vs_usd":  -2.14, "spread_10y_vs_usd": -1.12,
        "curve_slope": 0.34,
        "yield_2y_hist":  [2.10, 2.15, 2.20, 2.25, 2.32, 2.38],
        "yield_10y_hist": [2.52, 2.62, 2.72, 3.22, 3.22, 3.22],
        "ois": {"1m": 2.02, "3m": 2.10, "6m": 2.18, "12m": 2.24},
        "comment": "2Y Bund -214bps vs UST — large negative spread keeps EUR structurally weak vs USD. Rising 2Y yields (+28bps in 6m) signal ECB hike risk from energy shock. Steepening curve (+34bps) = growth expectations intact.",
        "meetings": [
            {"label":"ECB 5 Jun",  "chg": 0,  "rate":2.00,"hold":55,"cut":10,"hike":35},
            {"label":"ECB 24 Jul", "chg":+25, "rate":2.25,"hold":48,"cut":10,"hike":42},
            {"label":"ECB 12 Sep", "chg": 0,  "rate":2.25,"hold":60,"cut":10,"hike":30},
            {"label":"ECB 29 Oct", "chg": 0,  "rate":2.25,"hold":70,"cut":10,"hike":20},
        ],
    },
    "GBP": {
        "current": 3.75, "end_year": 3.25,
        "cuts": 2, "hikes": 0, "bias": "neutral_hawkish",
        "yield_2y": 4.28, "yield_10y": 4.701,
        "spread_2y_vs_usd":  -0.24, "spread_10y_vs_usd": 0.36,
        "curve_slope": 0.20,
        "yield_2y_hist":  [4.55, 4.48, 4.38, 4.32, 4.30, 4.28],
        "yield_10y_hist": [4.5, 4.48, 4.48, 4.7, 4.7, 4.7],
        "ois": {"1m": 3.76, "3m": 3.72, "6m": 3.58, "12m": 3.30},
        "comment": "2Y Gilt only -24bps vs UST — tightest spread in G8. Near parity with US yields provides GBP strong relative support. Services CPI 4.5% keeping 2Y sticky. BoE cannot ease aggressively without widening the spread.",
        "meetings": [
            {"label":"BoE 30 Apr", "chg": 0,  "rate":3.75,"hold":80,"cut": 5,"hike":15},
            {"label":"BoE 21 May", "chg": 0,  "rate":3.75,"hold":72,"cut": 8,"hike":20},
            {"label":"BoE 7 Aug",  "chg":-25, "rate":3.50,"hold":45,"cut":45,"hike":10},
            {"label":"BoE 18 Sep", "chg":-25, "rate":3.25,"hold":50,"cut":45,"hike": 5},
        ],
    },
    "JPY": {
        "current": 0.75, "end_year": 1.25,
        "cuts": 0, "hikes": 2, "bias": "hawkish",
        "yield_2y": 0.98, "yield_10y": 2.345,
        "spread_2y_vs_usd":  -3.54, "spread_10y_vs_usd": -1.99,
        "curve_slope": 0.57,
        "yield_2y_hist":  [0.38, 0.45, 0.55, 0.68, 0.82, 0.98],
        "yield_10y_hist": [1.22, 1.38, 1.55, 2.35, 2.35, 2.35],
        "ois": {"1m": 0.92, "3m": 1.05, "6m": 1.15, "12m": 1.28},
        "comment": "2Y JGB -354bps vs UST — explains USD/JPY 159. BUT: 2Y JGB up +60bps in 6m = fastest rise in G8. Spread narrowing rapidly. BoJ hike Apr 28 will accelerate convergence. Steepest curve (+57bps) = most aggressive normalisation priced in G8.",
        "meetings": [
            {"label":"BoJ 28 Apr", "chg":+25,"rate":1.00,"hold":20,"cut": 2,"hike":78},
            {"label":"BoJ 19 Jun", "chg": 0, "rate":1.00,"hold":72,"cut": 3,"hike":25},
            {"label":"BoJ 31 Jul", "chg":+25,"rate":1.25,"hold":50,"cut": 5,"hike":45},
            {"label":"BoJ 25 Sep", "chg": 0, "rate":1.25,"hold":75,"cut": 5,"hike":20},
        ],
    },
    "CAD": {
        "current": 2.75, "end_year": 2.25,
        "cuts": 2, "hikes": 0, "bias": "dovish",
        "yield_2y": 3.05, "yield_10y": 3.44,
        "spread_2y_vs_usd":  -1.47, "spread_10y_vs_usd": -0.9,
        "curve_slope": 0.33,
        "yield_2y_hist":  [3.55, 3.40, 3.28, 3.20, 3.12, 3.05],
        "yield_10y_hist": [3.5, 3.44, 3.38, 3.44, 3.44, 3.44],
        "ois": {"1m": 2.72, "3m": 2.58, "6m": 2.38, "12m": 2.22},
        "comment": "2Y Canada -147bps vs UST, widening (was -120bps 3m ago). Falling 2Y yields as oil collapse reduces BoC hawkish bias. Widening negative spread = persistent CAD weakness. Momentum clearly bearish.",
        "meetings": [
            {"label":"BoC 4 Jun",  "chg":-25,"rate":2.50,"hold":40,"cut":55,"hike": 5},
            {"label":"BoC 16 Jul", "chg":-25,"rate":2.25,"hold":45,"cut":52,"hike": 3},
            {"label":"BoC 10 Sep", "chg": 0, "rate":2.25,"hold":70,"cut":25,"hike": 5},
            {"label":"BoC 29 Oct", "chg": 0, "rate":2.25,"hold":75,"cut":20,"hike": 5},
        ],
    },
    "AUD": {
        "current": 3.60, "end_year": 3.85,
        "cuts": 0, "hikes": 1, "bias": "hawkish",
        "yield_2y": 3.95, "yield_10y": 4.9,
        "spread_2y_vs_usd":  -0.57, "spread_10y_vs_usd": 0.56,
        "curve_slope": 0.40,
        "yield_2y_hist":  [3.65, 3.70, 3.78, 3.82, 3.88, 3.95],
        "yield_10y_hist": [4.25, 4.3, 4.35, 4.9, 4.9, 4.9],
        "ois": {"1m": 3.62, "3m": 3.72, "6m": 3.80, "12m": 3.75},
        "comment": "2Y ACGB -57bps vs UST, narrowing (was -85bps 6m ago). Rising 2Y yields reflect RBA hawkish bias. Spread convergence = AUD positive. Steepening curve (+40bps) signals durable growth expectations supported by commodities.",
        "meetings": [
            {"label":"RBA 6 May",  "chg": 0, "rate":3.60,"hold":65,"cut": 5,"hike":30},
            {"label":"RBA 17 Jun", "chg":+25,"rate":3.85,"hold":52,"cut": 8,"hike":40},
            {"label":"RBA 5 Aug",  "chg": 0, "rate":3.85,"hold":70,"cut":10,"hike":20},
            {"label":"RBA 15 Sep", "chg": 0, "rate":3.85,"hold":72,"cut":13,"hike":15},
        ],
    },
    "NZD": {
        "current": 3.50, "end_year": 3.75,
        "cuts": 0, "hikes": 1, "bias": "hawkish",
        "yield_2y": 3.82, "yield_10y": 4.28,
        "spread_2y_vs_usd":  -0.70, "spread_10y_vs_usd": -0.44,
        "curve_slope": 0.46,
        "yield_2y_hist":  [3.50, 3.55, 3.62, 3.68, 3.75, 3.82],
        "yield_10y_hist": [3.95, 4.02, 4.10, 4.18, 4.22, 4.28],
        "ois": {"1m": 3.55, "3m": 3.68, "6m": 3.75, "12m": 3.68},
        "comment": "2Y NZGB -70bps vs UST, rising sharply post CPI 3.1% beat (+32bps in 6m). Market pricing RBNZ tightening. Spread narrowing = NZD support. 62% probability of May hike now reflected in bond pricing.",
        "meetings": [
            {"label":"RBNZ 27 May","chg":+25,"rate":3.75,"hold":35,"cut": 3,"hike":62},
            {"label":"RBNZ 9 Jul", "chg": 0, "rate":3.75,"hold":70,"cut": 5,"hike":25},
            {"label":"RBNZ 27 Aug","chg": 0, "rate":3.75,"hold":75,"cut":10,"hike":15},
            {"label":"RBNZ 15 Oct","chg": 0, "rate":3.75,"hold":75,"cut":15,"hike":10},
        ],
    },
    "CHF": {
        "current": 0.25, "end_year": 0.00,
        "cuts": 1, "hikes": 0, "bias": "neutral_dovish",
        "yield_2y": 0.38, "yield_10y": 0.4,
        "spread_2y_vs_usd":  -4.14, "spread_10y_vs_usd": -3.94,
        "curve_slope": 0.34,
        "yield_2y_hist":  [0.62, 0.55, 0.50, 0.45, 0.42, 0.38],
        "yield_10y_hist": [0.78, 0.75, 0.72, 0.4, 0.4, 0.4],
        "ois": {"1m": 0.23, "3m": 0.18, "6m": 0.10, "12m": 0.02},
        "comment": "2Y Swiss -414bps vs UST — widest negative spread in G8. CHF strength is NOT yield-driven: it is pure safe-haven flow and current account surplus (+8.5% GDP). Falling 2Y yields (-24bps in 6m) confirm SNB dovish path.",
        "meetings": [
            {"label":"SNB 19 Jun", "chg": 0, "rate":0.25,"hold":82,"cut":10,"hike": 8},
            {"label":"SNB 25 Sep", "chg":-25,"rate":0.00,"hold":50,"cut":45,"hike": 5},
            {"label":"SNB 12 Dec", "chg": 0, "rate":0.00,"hold":60,"cut":35,"hike": 5},
            {"label":"SNB Mar 27", "chg": 0, "rate":0.00,"hold":65,"cut":30,"hike": 5},
        ],
    },
}

YIELD_MONTHS = ["Oct 25", "Nov 25", "Dec 25", "Jan 26", "Feb 26", "Mar 26"]

def get_rate_expectations(): return RATE_EXP

def get_news():
    """Load news from cache file if available, else return static NEWS."""
    import json, os
    cache = os.path.join(os.path.dirname(__file__), "news_cache.json")
    if os.path.exists(cache):
        try:
            with open(cache, encoding="utf-8") as f:
                data = json.load(f)
            if data:
                return data
        except:
            pass
    return NEWS

def get_global_indicators():
    """Load live global indicators from JSON cache."""
    import json, os
    cache = os.path.join(os.path.dirname(__file__), "global_indicators.json")
    if os.path.exists(cache):
        try:
            with open(cache, encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {}

def get_live_fx_rates():
    """Load live FX rates — from news_cache scrape (Frankfurter ECB)."""
    import json, os
    # FX_RATES in data.py is patched by scraper — return it directly
    return FX_RATES

def get_risk_sentiment():
    """Load VIX-based risk sentiment from cache."""
    import json, os
    cache = os.path.join(os.path.dirname(__file__), "risk_sentiment.json")
    if os.path.exists(cache):
        try:
            with open(cache, encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return None

def get_ai_insights():
    """Load AI-generated insights from cache file."""
    import json, os
    cache = os.path.join(os.path.dirname(__file__), "ai_insights.json")
    if os.path.exists(cache):
        try:
            with open(cache, encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return None
def get_yield_months(): return YIELD_MONTHS

# FX RATES
# ─────────────────────────────────────────────────────────────────
FX_RATES = {
    "EUR/USD": {"rate": 1.1712, "chg": -0.0, "hi": 1.1820, "lo": 1.1750, "wchg": -0.0},
    "GBP/USD": {"rate": 1.3493, "chg":  -0.0, "hi": 1.3560, "lo": 1.3480, "wchg":  -0.0},
    "USD/JPY": {"rate": 159.42, "chg":  0.0, "hi": 159.80, "lo": 158.90, "wchg":  0.0},
    "USD/CAD": {"rate": 1.3681, "chg":  0.0, "hi": 1.3710, "lo": 1.3620, "wchg":  0.0},
    "AUD/USD": {"rate": 0.7144, "chg":  -0.0, "hi": 0.7150, "lo": 0.7090, "wchg":  -0.0},
    "NZD/USD": {"rate": 0.5874, "chg":  -0.0, "hi": 0.5930, "lo": 0.5870, "wchg":  -0.0},
    "USD/CHF": {"rate": 0.7854, "chg": 0.0, "hi": 0.8040, "lo": 0.7990, "wchg": 0.0},
    "EUR/GBP": {"rate": 0.868, "chg": 0.0, "hi": 0.8760, "lo": 0.8710, "wchg": 0.0},
    "GBP/JPY": {"rate": 215.0974, "chg":  0.0, "hi": 216.10, "lo": 214.80, "wchg":  0.0},
    "EUR/CAD": {"rate": 1.6023, "chg": 0.0, "hi": 1.6180, "lo": 1.6060, "wchg": 0.0},
    "GBP/CAD": {"rate": 1.8459, "chg":  0.0, "hi": 1.8560, "lo": 1.8420, "wchg":  0.0},
    "CAD/CHF": {"rate": 0.5741, "chg": 0.0, "hi": 0.5750, "lo": 0.5690, "wchg": 0.0},
    "EUR/CHF": {"rate": 0.9199, "chg": 0.0, "hi": 0.9240, "lo": 0.9190, "wchg": 0.0},
    "AUD/NZD": {"rate": 1.2163, "chg": 0.0, "hi": 1.2110, "lo": 1.2040, "wchg":  0.0},
}

# ─────────────────────────────────────────────────────────────────
# CALENDAR
# ─────────────────────────────────────────────────────────────────
CALENDAR = [
    {"date": "23 Apr", "day": "Wed", "time": "09:00", "flag": "DE", "ccy": "EUR", "event": "Germany Flash Manufacturing PMI",  "imp": "high",   "prev": "49.1", "fore": "49.8",  "act": "50.3"},
    {"date": "23 Apr", "day": "Wed", "time": "09:30", "flag": "EU", "ccy": "EUR", "event": "Eurozone Flash Composite PMI",      "imp": "high",   "prev": "50.9", "fore": "50.5",  "act": ""},
    {"date": "23 Apr", "day": "Wed", "time": "09:30", "flag": "GB", "ccy": "GBP", "event": "UK Flash Manufacturing PMI",       "imp": "high",   "prev": "49.8", "fore": "50.2",  "act": ""},
    {"date": "23 Apr", "day": "Wed", "time": "14:45", "flag": "US", "ccy": "USD", "event": "US Flash Services PMI",            "imp": "high",   "prev": "51.4", "fore": "52.0",  "act": ""},
    {"date": "24 Apr", "day": "Thu", "time": "08:00", "flag": "DE", "ccy": "EUR", "event": "IFO Business Climate Germany",     "imp": "medium", "prev": "88.6", "fore": "86.5",  "act": ""},
    {"date": "24 Apr", "day": "Thu", "time": "13:30", "flag": "US", "ccy": "USD", "event": "Initial Jobless Claims",           "imp": "medium", "prev": "220K", "fore": "225K",  "act": ""},
    {"date": "25 Apr", "day": "Fri", "time": "12:30", "flag": "CA", "ccy": "CAD", "event": "Canada CPI YoY",                  "imp": "high",   "prev": "2.0%", "fore": "2.1%",  "act": ""},
    {"date": "25 Apr", "day": "Fri", "time": "13:30", "flag": "US", "ccy": "USD", "event": "Core PCE Price Index",            "imp": "high",   "prev": "2.8%", "fore": "2.7%",  "act": ""},
    {"date": "25 Apr", "day": "Fri", "time": "15:00", "flag": "US", "ccy": "USD", "event": "Michigan Consumer Confidence",    "imp": "medium", "prev": "57.9", "fore": "53.0",  "act": ""},
    {"date": "28 Apr", "day": "Mon", "time": "03:00", "flag": "JP", "ccy": "JPY", "event": "BoJ Rate Decision + Ueda presser","imp": "high",   "prev": "0.75%","fore": "1.00%?","act": ""},
    {"date": "30 Apr", "day": "Wed", "time": "12:00", "flag": "GB", "ccy": "GBP", "event": "BoE Rate Decision",              "imp": "high",   "prev": "3.75%","fore": "3.75%", "act": ""},
    {"date": "30 Apr", "day": "Wed", "time": "19:00", "flag": "US", "ccy": "USD", "event": "FOMC Rate Decision + Powell",    "imp": "high",   "prev": "4.00%","fore": "4.00%", "act": ""},
]

# ─────────────────────────────────────────────────────────────────
# NEWS  — sera écrasé par scraper.py
# ─────────────────────────────────────────────────────────────────
NEWS = [
    {
        "ts": "24 Apr 20:11",
        "title": "Trump : « Les navires américains sont armés et prêts à partir »",
        "body": "Donald Trump a déclaré que les tensions avec l'Iran restent élevées et que la flotte américaine est prête. Le pétrole pourrait grimper.",
        "cat": "Geopolitics",
        "ccys": ["USD", "CAD"],
        "dir": "negative"
    },
    {
        "ts": "24 Apr 18:30",
        "title": "Powell (Fed) : « Pas de baisse de taux avant septembre »",
        "body": "Le président de la Fed maintient une position hawkish, les marchés repoussent les prévisions de baisse.",
        "cat": "Central Bank",
        "ccys": ["USD"],
        "dir": "positive"
    },
    {
        "ts": "24 Apr 12:00",
        "title": "BoJ : Ueda confirme une possible hausse le 28 avril",
        "body": "Le gouverneur de la BoJ indique que l'inflation et la faiblesse du yen justifient un resserrement monétaire.",
        "cat": "Central Bank",
        "ccys": ["JPY"],
        "dir": "positive"
    },
    {
        "ts": "23 Apr 15:20",
        "title": "BoE : Bailey souligne la persistance de l'inflation des services",
        "body": "Le gouverneur de la Banque d'Angleterre exclut une baisse des taux dans l'immédiat.",
        "cat": "Central Bank",
        "ccys": ["GBP"],
        "dir": "positive"
    },
    {
        "ts": "23 Apr 09:45",
        "title": "ECB : Lagarde met en garde contre les chocs énergétiques",
        "body": "La présidente de la BCE craint un impact sur l'inflation en zone euro si le canal d'Ormuz reste bloqué.",
        "cat": "Central Bank",
        "ccys": ["EUR"],
        "dir": "negative"
    }
]

# ─────────────────────────────────────────────────────────────────
# HISTORICAL (7 months)
# ─────────────────────────────────────────────────────────────────
MONTHS = ["Oct 25", "Nov 25", "Dec 25", "Jan 26", "Feb 26", "Mar 26", "Apr 26"]
HIST_CPI   = {"USD":[2.6,2.7,2.9,3.0,3.1,3.2,3.2],"EUR":[1.9,2.0,2.1,2.2,2.3,2.5,2.5],
               "GBP":[2.6,2.7,3.0,3.0,3.0,3.3,3.3],"JPY":[2.5,2.4,2.1,1.5,1.3,1.3,1.3],
               "CAD":[1.9,2.0,2.0,2.0,2.0,2.0,2.0],"AUD":[3.5,3.6,3.7,3.8,3.8,3.8,3.8],
               "NZD":[3.0,3.0,3.1,3.0,3.0,3.1,3.1],"CHF":[0.8,0.9,1.0,1.0,1.0,1.0,1.0]}
HIST_RATE  = {"USD":[5.0,4.75,4.5,4.25,4.0,4.0,4.0],"EUR":[2.5,2.25,2.15,2.0,2.0,2.0,2.0],
               "GBP":[4.75,4.5,3.75,3.75,3.75,3.75,3.75],"JPY":[0.25,0.25,0.50,0.50,0.75,0.75,0.75],
               "CAD":[3.75,3.5,3.25,3.0,2.75,2.75,2.75],"AUD":[4.10,3.85,3.60,3.60,3.60,3.60,3.60],
               "NZD":[4.75,4.25,3.75,3.50,3.50,3.50,3.50],"CHF":[1.0,0.75,0.50,0.25,0.25,0.25,0.25]}
HIST_UNEM  = {"USD":[4.1,4.2,4.3,4.4,4.4,4.4,4.4],"EUR":[6.6,6.5,6.5,6.5,6.4,6.4,6.4],
               "GBP":[5.2,5.1,5.1,5.0,5.0,4.9,4.9],"JPY":[2.7,2.7,2.7,2.6,2.6,2.6,2.6],
               "CAD":[6.2,6.3,6.4,6.5,6.5,6.5,6.5],"AUD":[4.2,4.2,4.1,4.1,4.1,4.1,4.1],
               "NZD":[5.5,5.4,5.4,5.3,5.3,5.3,5.3],"CHF":[2.6,2.5,2.5,2.4,2.4,2.4,2.4]}

# ─────────────────────────────────────────────────────────────────
# SQLITE  — stores snapshots after each session close
# ─────────────────────────────────────────────────────────────────
DB = "fx_data.db"

def _db():
    con = sqlite3.connect(DB, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = _db()
    con.executescript("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session     TEXT NOT NULL,
            session_dt  TEXT NOT NULL,
            currency    TEXT NOT NULL,
            cpi         REAL, rate REAL, unem REAL, gdp REAL,
            bias_score  INTEGER, ois_3m REAL, end_year_rate REAL,
            UNIQUE(session, currency)
        );
        CREATE TABLE IF NOT EXISTS fx_snapshots (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session    TEXT NOT NULL,
            session_dt TEXT NOT NULL,
            pair       TEXT NOT NULL,
            rate       REAL, chg REAL, wchg REAL,
            UNIQUE(session, pair)
        );
        CREATE TABLE IF NOT EXISTS update_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session    TEXT NOT NULL,
            trigger    TEXT NOT NULL,
            status     TEXT NOT NULL,
            ts         TEXT NOT NULL,
            note       TEXT
        );
    """)
    con.commit()
    con.close()

def _session_key():
    """Returns e.g. '2026-04-23-NY' or '2026-04-23-LDN'"""
    now = datetime.now(timezone.utc)
    # London close ~17:00 UTC, NY close ~22:00 UTC
    if now.hour >= 22:
        return f"{(now + timedelta(days=1)).date()}-NY"
    elif now.hour >= 17:
        return f"{now.date()}-NY-pre"   # between London and NY close
    else:
        return f"{now.date()}-LDN"

def save_snapshot(trigger="auto"):
    """Save current macro + fx data to DB for the current session."""
    init_db()
    session = _session_key()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    con = _db()
    try:
        for ccy, d in MACRO.items():
            exp = RATE_EXP.get(ccy, {})
            con.execute("""
                INSERT INTO snapshots
                    (session, session_dt, currency, cpi, rate, unem, gdp,
                     bias_score, ois_3m, end_year_rate)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(session, currency) DO UPDATE SET
                    cpi=excluded.cpi, rate=excluded.rate,
                    unem=excluded.unem, gdp=excluded.gdp,
                    bias_score=excluded.bias_score,
                    ois_3m=excluded.ois_3m,
                    end_year_rate=excluded.end_year_rate
            """, (session, ts, ccy, d["cpi"], d["rate"], d["unem"],
                  d["gdp"], d["score"],
                  exp.get("ois", {}).get("3m", None),
                  exp.get("end_year", None)))

        for pair, d in FX_RATES.items():
            con.execute("""
                INSERT INTO fx_snapshots (session, session_dt, pair, rate, chg, wchg)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(session, pair) DO UPDATE SET
                    rate=excluded.rate, chg=excluded.chg, wchg=excluded.wchg
            """, (session, ts, pair, d["rate"], d["chg"], d["wchg"]))

        con.execute("INSERT INTO update_log (session, trigger, status, ts) VALUES (?,?,?,?)",
                    (session, trigger, "success", ts))
        con.commit()
        print(f"[{ts}] Snapshot saved — session: {session} | trigger: {trigger}")
        return True
    except Exception as e:
        con.execute("INSERT INTO update_log (session, trigger, status, ts, note) VALUES (?,?,?,?,?)",
                    (session, trigger, "error", ts, str(e)))
        con.commit()
        print(f"[{ts}] Snapshot ERROR: {e}")
        return False
    finally:
        con.close()

def load_history_from_db(n=8):
    """Load last N session snapshots for charts."""
    init_db()
    con = _db()
    cur = con.execute("""
        SELECT DISTINCT session, session_dt FROM snapshots
        ORDER BY session_dt DESC LIMIT ?
    """, (n,))
    sessions = [dict(r) for r in cur.fetchall()]
    sessions.reverse()

    labels = [s["session"] for s in sessions]
    data = {k: {c: [] for c in MACRO.keys()} for k in ["cpi", "rate", "unem"]}

    for s in sessions:
        cur2 = con.execute("SELECT * FROM snapshots WHERE session=?", (s["session"],))
        rows = {r["currency"]: dict(r) for r in cur2.fetchall()}
        for ccy in MACRO.keys():
            r = rows.get(ccy, {})
            data["cpi"][ccy].append(r.get("cpi", None))
            data["rate"][ccy].append(r.get("rate", None))
            data["unem"][ccy].append(r.get("unem", None))

    con.close()
    return labels, data

def load_update_log(n=30):
    init_db()
    con = _db()
    rows = con.execute(
        "SELECT * FROM update_log ORDER BY ts DESC LIMIT ?", (n,)
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]

def get_last_update():
    init_db()
    con = _db()
    row = con.execute(
        "SELECT ts, session, trigger FROM update_log WHERE status='success' ORDER BY ts DESC LIMIT 1"
    ).fetchone()
    con.close()
    return dict(row) if row else {"ts": "Never", "session": "—", "trigger": "—"}

# ─────────────────────────────────────────────────────────────────
# SCHEDULER  — London 17:00 UTC + NY 22:00 UTC
# ─────────────────────────────────────────────────────────────────
_scheduler_started = False

def start_scheduler():
    global _scheduler_started
    if _scheduler_started:
        return
    _scheduler_started = True

    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    sched = BackgroundScheduler(timezone="UTC")

    # London close — 17:00 UTC Mon-Fri
    sched.add_job(
        lambda: save_snapshot("london_close"),
        CronTrigger(day_of_week="mon-fri", hour=17, minute=0),
        id="london_close", replace_existing=True,
    )

    # New York close — 22:00 UTC Mon-Fri
    sched.add_job(
        lambda: save_snapshot("ny_close"),
        CronTrigger(day_of_week="mon-fri", hour=22, minute=0),
        id="ny_close", replace_existing=True,
    )

    sched.start()
    print("Scheduler started — London 17:00 UTC · NY 22:00 UTC")

def score_meta(s):
    if s >= 2:  return "#22c55e", "#052e16", "BULLISH"
    if s == 1:  return "#60a5fa", "#0c1a3a", "MILD BULLISH"
    if s == 0:  return "#6b7280", "#111827", "NEUTRAL"
    if s == -1: return "#f59e0b", "#1c1100", "MILD BEARISH"
    return              "#ef4444", "#1a0505", "BEARISH"
