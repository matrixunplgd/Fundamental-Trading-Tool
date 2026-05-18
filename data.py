"""
data.py  —  FX Dashboard data layer (V9.5 - WTI/CAD Correlation Pro)
Moteur macro avec intégration de la corrélation Pétrole (WTI) / Dollar Canadien (CAD).
"""

import json
import sqlite3
import os
import yfinance as yf
from datetime import datetime, timezone

DB = "fx_data.db"

# Liste explicite des paires utilisées par l'app (format BASE/QUOTE) - nettoyée et validée
PAIRS = [
    "EUR/CAD",
    "EUR/CHF",
    "EUR/GBP",
    "NZD/USD",
    "AUD/USD",
    "AUD/CHF",
    "AUD/NZD",
    "AUD/CAD",
    "NZD/CHF",
    "NZD/CAD",
    "AUD/JPY",
    "NZD/JPY",
    "GBP/USD",
    "GBP/CAD",
    "GBP/CHF",
    "USD/CHF",
    "CAD/CHF",
    "CAD/JPY",
    "CHF/JPY",
    "EUR/USD",
    "USD/CHF",
    "USD/CAD",
    "USD/JPY"
]

# Données macro minimales requises pour les devises utilisées
# (adapte les valeurs réelles selon tes sources)
_MACRO_BASELINE = {
    "USD": {"name": "United States", "cb": "Federal Reserve", "rate": 4.00, "rate_prev": 4.25, "gdp": 0.5, "gdp_prev": 2.8, "cpi": 330.293, "cpi_prev": 2.9, "core_cpi": 2.8, "unem": 4.3, "unem_prev": 4.1, "wages": 37.38, "retail": 752063.0, "conf": 53.3, "ca": -3.2, "pmi": 51.4, "next_mtg": "30 Apr 2026", "bias": "Neutral / Hawkish", "score": 0, "color": "#3b82f6", "yield_10y": 4.15},
    "EUR": {"name": "Euro Area", "cb": "European Central Bank", "rate": 2.00, "rate_prev": 2.25, "gdp": 0.91, "gdp_prev": 1.2, "cpi": 2.5, "cpi_prev": 2.3, "core_cpi": 2.3, "unem": 6.33, "unem_prev": 6.5, "wages": 3.2, "retail": 0.3, "conf": -14.2, "ca": 1.8, "pmi": 50.9, "next_mtg": "5 Jun 2026", "bias": "Neutral / Cautious", "score": 0, "color": "#8b5cf6", "yield_10y": 2.45},
    "GBP": {"name": "United Kingdom", "cb": "Bank of England", "rate": 3.75, "rate_prev": 4.00, "gdp": 1.13, "gdp_prev": 0.9, "cpi": 3.27, "cpi_prev": 3.0, "core_cpi": 3.1, "unem": 4.75, "unem_prev": 5.1, "wages": 5.6, "retail": 0.4, "conf": -19.0, "ca": -3.8, "pmi": 50.8, "next_mtg": "30 Apr 2026", "bias": "Hawkish Near-Term", "score": 0, "color": "#10b981", "yield_10y": 3.85},
    "JPY": {"name": "Japan", "cb": "Bank of Japan", "rate": 0.75, "rate_prev": 0.50, "gdp": 0.1, "gdp_prev": 0.8, "cpi": 2.74, "cpi_prev": 2.1, "core_cpi": 1.6, "unem": 2.45, "unem_prev": 2.7, "wages": 3.8, "retail": -0.2, "conf": 35.0, "ca": 3.2, "pmi": 49.8, "next_mtg": "28 Apr 2026", "bias": "Hawkish Pivot", "score": 0, "color": "#f43f5e", "yield_10y": 0.95},
    "CAD": {"name": "Canada", "cb": "Bank of Canada", "rate": 2.75, "rate_prev": 3.00, "gdp": 1.55, "gdp_prev": 1.3, "cpi": 2.38, "cpi_prev": 1.9, "core_cpi": 2.2, "unem": 6.91, "unem_prev": 6.3, "wages": 4.2, "retail": -0.1, "conf": 47.0, "ca": -1.2, "pmi": 48.9, "next_mtg": "4 Jun 2026", "bias": "Dovish", "score": 0, "color": "#f97316", "yield_10y": 3.35},
    "AUD": {"name": "Australia", "cb": "Reserve Bank of Australia", "rate": 3.60, "rate_prev": 3.85, "gdp": 1.37, "gdp_prev": 1.8, "cpi": 3.17, "cpi_prev": 3.6, "core_cpi": 3.2, "unem": 4.09, "unem_prev": 4.2, "wages": 4.5, "retail": 0.5, "conf": 85.0, "ca": 1.5, "pmi": 51.2, "next_mtg": "6 May 2026", "bias": "Hawkish", "score": 0, "color": "#eab308", "yield_10y": 4.25},
    "NZD": {"name": "New Zealand", "cb": "Reserve Bank of New Zealand", "rate": 3.50, "rate_prev": 3.75, "gdp": 1.29, "gdp_prev": -1.1, "cpi": 2.92, "cpi_prev": 3.0, "core_cpi": 3.0, "unem": 5.08, "unem_prev": 5.5, "wages": 3.5, "retail": 0.2, "conf": 102.0, "ca": -6.5, "pmi": 50.1, "next_mtg": "27 May 2026", "bias": "Hawkish Surprise", "score": 0, "color": "#06b6d4", "yield_10y": 4.40},
    "CHF": {"name": "Switzerland", "cb": "Swiss National Bank", "rate": 0.25, "rate_prev": 0.50, "gdp": 1.3, "gdp_prev": 1.3, "cpi": 1.06, "cpi_prev": 1.1, "core_cpi": 1.1, "unem": 4.87, "unem_prev": 2.5, "wages": 2.0, "retail": 0.1, "conf": -8.0, "ca": 8.5, "pmi": 50.5, "next_mtg": "19 Jun 2026", "bias": "Safe Haven", "score": 0, "color": "#a855f7", "yield_10y": 0.70}
}

_MARKET_ASSETS_BASELINE = {
    "GOLD": {"price": 2345.80, "chg": 0.45},
    "WTI_CRUDE": {"price": 79.24, "chg": 1.15},
    "US_500": {"price": 5214.30, "chg": 0.28},
    "VIX": {"price": 13.50, "chg": -2.10}
}

def _load_json_cache(filename, baseline):
    filepath = os.path.join(os.path.dirname(__file__), filename)
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(baseline, f, indent=4, ensure_ascii=False)
    except Exception:
        pass
    return baseline

# Charger MACRO et MARKET_ASSETS depuis cache si présent, sinon baseline
MACRO = _load_json_cache("macro_cache.json", _MACRO_BASELINE)
MARKET_ASSETS = _load_json_cache("market_assets_cache.json", _MARKET_ASSETS_BASELINE)

# Mois et historique des taux (exemples)
MONTHS = ["Oct 25", "Nov 25", "Dec 25", "Jan 26", "Feb 26", "Mar 26", "Apr 26"]
HIST_RATE = {
    "USD": [5.0, 4.75, 4.5, 4.25, 4.0],
    "EUR": [2.5, 2.25, 2.15, 2.0, 2.0],
    "GBP": [4.75, 4.5, 3.75, 3.75, 3.75],
    "JPY": [0.25, 0.25, 0.50, 0.50, 0.75],
    "CAD": [3.75, 3.5, 3.25, 3.0, 2.75],
    "AUD": [4.10, 3.85, 3.60, 3.60, 3.60],
    "NZD": [4.75, 4.25, 3.75, 3.50, 3.50],
    "CHF": [1.0, 0.75, 0.50, 0.25, 0.25]
}

def compute_score(country_data):
    """Calcule un score fondamental pondéré."""
    score = (
        (country_data.get("rate", 0) * 0.4) +
        (country_data.get("yield_10y", 0) * 0.3) -
        (country_data.get("unem", 0) * 0.3)
    )
    return round(score, 2)

# Mettre à jour les scores dans MACRO
for ccy, info in MACRO.items():
    try:
        info["score"] = compute_score(info)
    except Exception:
        info["score"] = 0

# Taux spot par défaut (exemples) — utile pour l'affichage des KPI
FX_RATES = {
    "EUR/CAD": {"rate": 1.45, "chg": +0.12},
    "EUR/CHF": {"rate": 1.07, "chg": -0.02},
    "EUR/GBP": {"rate": 0.86, "chg": +0.01},
    "NZD/USD": {"rate": 0.5874, "chg": +0.14},
    "AUD/USD": {"rate": 0.7144, "chg": +0.05},
    "AUD/CHF": {"rate": 0.79, "chg": +0.03},
    "AUD/NZD": {"rate": 1.08, "chg": -0.01},
    "AUD/CAD": {"rate": 0.98, "chg": +0.02},
    "NZD/CHF": {"rate": 0.46, "chg": +0.04},
    "NZD/CAD": {"rate": 0.80, "chg": +0.02},
    "AUD/JPY": {"rate": 88.5, "chg": +0.10},
    "NZD/JPY": {"rate": 37.2, "chg": +0.08},
    "GBP/USD": {"rate": 1.3493, "chg": -0.03},
    "GBP/CAD": {"rate": 1.85, "chg": +0.05},
    "GBP/CHF": {"rate": 1.05, "chg": -0.02},
    "USD/CHF": {"rate": 0.7854, "chg": +0.10},
    "CAD/CHF": {"rate": 0.69, "chg": -0.05},
}

def update_live_fx_rates():
    """
    Met à jour FX_RATES et MARKET_ASSETS via yfinance.
    Mapping minimal des tickers utilisés par l'app.
    """
    mapping = {
        "EURUSD=X": "EUR/USD",
        "GBPUSD=X": "GBP/USD",
        "JPY=X": "USD/JPY",
        "CAD=X": "USD/CAD",
        "AUDUSD=X": "AUD/USD",
        "NZDUSD=X": "NZD/USD",
        "CHF=X": "USD/CHF"
    }
    assets_mapping = {"GC=F": "GOLD", "CL=F": "WTI_CRUDE", "^GSPC": "US_500", "^VIX": "VIX"}
    try:
        tickers = list(mapping.keys()) + list(assets_mapping.keys())
        data = yf.download(tickers, period="5d", progress=False)
        if data.empty:
            return False
        for yf_ticker, app_pair in mapping.items():
            if yf_ticker not in data['Close']:
                continue
            close_series = data['Close'][yf_ticker].dropna()
            if len(close_series) < 1:
                continue
            live_p = float(close_series.iloc[-1])
            open_p = float(data['Open'][yf_ticker].dropna().iloc[-1])
            FX_RATES[app_pair] = {"rate": round(live_p, 4), "chg": round(((live_p - open_p) / open_p) * 100, 2)}
        for yf_ticker, asset_name in assets_mapping.items():
            if yf_ticker not in data['Close']:
                continue
            series = data['Close'][yf_ticker].dropna()
            if len(series) < 1:
                continue
            c_p = float(series.iloc[-1])
            o_p = float(data['Open'][yf_ticker].dropna().iloc[-1])
            MARKET_ASSETS[asset_name] = {"price": c_p, "chg": round(((c_p - o_p) / o_p) * 100, 2)}
        return True
    except Exception:
        return False

# Essayer une mise à jour live au démarrage (silencieuse)
try:
    update_live_fx_rates()
except Exception:
    pass

import threading
import time
from datetime import datetime

_UPDATE_INTERVAL_SECONDS = 60  # intervalle de mise à jour en secondes (ajuste ici)

def _write_json_cache(filename, data):
    filepath = os.path.join(os.path.dirname(__file__), filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False

def _record_update_log(session="auto", trigger="scheduler", status="success", note=""):
    """
    Enregistre une ligne dans la table update_log.
    """
    try:
        init_db()
        con = _db()
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        con.execute(
            "INSERT INTO update_log (session, trigger, status, ts, note) VALUES (?, ?, ?, ?, ?)",
            (session, trigger, status, ts, note),
        )
        con.commit()
        con.close()
    except Exception:
        pass

def refresh_and_persist():
    """
    Appelle update_live_fx_rates(), met à jour les caches JSON et MARKET_ASSETS,
    et enregistre le résultat dans la DB.
    Retourne True si OK, False sinon.
    """
    try:
        ok = update_live_fx_rates()
        # sauvegarder caches JSON pour persistance
        _write_json_cache("macro_cache.json", MACRO)
        _write_json_cache("market_assets_cache.json", MARKET_ASSETS)
        if ok:
            _record_update_log(status="success", note="live update ok")
        else:
            _record_update_log(status="failed", note="yfinance returned empty or error")
        return ok
    except Exception as e:
        _record_update_log(status="failed", note=str(e))
        return False

# Background updater (thread safe minimal)
_updater_thread = None
_updater_lock = threading.Lock()
_stop_event = threading.Event()

def _updater_loop(interval_seconds=_UPDATE_INTERVAL_SECONDS):
    """
    Boucle infinie exécutée dans un thread séparé.
    """
    while not _stop_event.is_set():
        try:
            refresh_and_persist()
        except Exception:
            pass
        # attend en petits pas pour pouvoir stopper rapidement
        for _ in range(int(interval_seconds)):
            if _stop_event.is_set():
                break
            time.sleep(1)

def start_background_updater(interval_seconds=_UPDATE_INTERVAL_SECONDS):
    """
    Démarre le thread d'update si pas déjà démarré.
    Appeler depuis app.py au démarrage.
    """
    global _updater_thread
    with _updater_lock:
        if _updater_thread is None or not _updater_thread.is_alive():
            _stop_event.clear()
            _updater_thread = threading.Thread(target=_updater_loop, args=(interval_seconds,), daemon=True)
            _updater_thread.start()
            return True
    return False

def stop_background_updater():
    """
    Stoppe proprement le thread d'update.
    """
    _stop_event.set()
    global _updater_thread
    with _updater_lock:
        _updater_thread = None


def detect_market_sentiment():
    """
    Détecte un sentiment de marché simple basé sur SP500, VIX et Gold.
    Retourne (label, color).
    """
    try:
        sp500_chg = MARKET_ASSETS.get("US_500", {}).get("chg", 0.0)
        vix_price = MARKET_ASSETS.get("VIX", {}).get("price", 15.0)
        gold_chg = MARKET_ASSETS.get("GOLD", {}).get("chg", 0.0)
        if vix_price > 19 or (sp500_chg < -0.8 and gold_chg > 0.4):
            return "RISK-OFF (Aversion)", "#ef4444"
        elif sp500_chg > 0.5 and vix_price < 15:
            return "RISK-ON (Appétit)", "#10b981"
        return "NORMAL (Équilibré)", "#6366f1"
    except Exception:
        return "NORMAL (Équilibré)", "#6366f1"

def _db():
    con = sqlite3.connect(DB, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = _db()
    con.execute(
        "CREATE TABLE IF NOT EXISTS update_log (id INTEGER PRIMARY KEY AUTOINCREMENT, session TEXT, trigger TEXT, status TEXT, ts TEXT, note TEXT);"
    )
    con.commit()
    con.close()

def get_last_update():
    init_db()
    con = _db()
    row = con.execute("SELECT ts FROM update_log WHERE status='success' ORDER BY ts DESC LIMIT 1").fetchone()
    con.close()
    return dict(row) if row else {"ts": datetime.now().strftime("%Y-%m-%d %H:%M")}

def load_update_log():
    init_db()
    con = _db()
    rows = con.execute("SELECT * FROM update_log ORDER BY ts DESC LIMIT 10").fetchall()
    con.close()
    return [dict(r) for r in rows]

def score_meta(s):
    if s >= 2:
        return "#10b981", "#052e16", "BULLISH"
    if s == 1:
        return "#3b82f6", "#0c1a3a", "MILD BULLISH"
    if s == 0:
        return "#6b7280", "#111827", "NEUTRAL"
    if s == -1:
        return "#f59e0b", "#1c1100", "MILD BEARISH"
    return "#ef4444", "#1a0505", "BEARISH"
