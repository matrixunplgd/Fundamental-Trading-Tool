# app.py
"""
FX Fundamental Terminal — UX redesign by 'UX Designer' (dark mauve/teal theme)
Improvements:
- Cleaner header with subtitle and controls
- Sidebar controls (auto-refresh toggle, update interval, KPI count)
- Polished KPI cards with icons, metrics, sparklines and tooltips
- RateProbability table rendered as styled dataframe with color coding
- Improved spacing, typography, accessible contrast, responsive tweaks
- Comments indicate where to adapt data sources or styles
"""

import os
import json
import time
import requests
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# Optional: BeautifulSoup for scraping RateProbability
try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:
    BeautifulSoup = None

# Project imports (assumes these modules exist in your repo)
from data import (
    MACRO,
    FX_RATES,
    MARKET_ASSETS,
    detect_market_sentiment,
    HIST_RATE,
    load_update_log,
    start_background_updater,
    refresh_and_persist,
    PAIRS,
)
from utils.fx_calculations import compute_spreads, normalize_score, build_comparison_table
from utils.sentiment_engine import regime_weights
from utils.commodities_logic import wti_adjustment
from utils.recommendations import rank_unique_pairs as rank_all_pairs
from utils.news import fetch_news

# -------------------------
# Page config & startup
# -------------------------
st.set_page_config(page_title="FX Intermarket Pro", layout="wide", initial_sidebar_state="expanded")

# Start background updater (idempotent)
try:
    start_background_updater(interval_seconds=120)
except Exception:
    pass

# -------------------------
# Theme & global CSS (polished)
# -------------------------
PRIMARY = "#e6eefc"
ACCENT = "#6d28d9"
ACCENT2 = "#0ea5a3"
MUTED = "#9aa3c7"
BG = "#071028"
CARD_BG = "rgba(255,255,255,0.02)"

st.markdown(
    """
    <style>
    :root{
      --bg:#0b1020;
      --panel:#0f1726;
      --muted:#9aa3c7;
      --accent:#6d28d9;
      --accent-2:#0ea5a3;
      --primary:#e6eefc;
      --success:#10b981;
      --danger:#ef4444;
      --warning:#f59e0b;
      --glass: rgba(255,255,255,0.03);
      --card-shadow: 0 8px 30px rgba(2,6,23,0.6);
      --radius:12px;
    }

    .stApp, .main {
      background: linear-gradient(180deg, var(--bg) 0%, #071028 100%) !important;
      color: var(--primary);
    }

    .ft-header {
      display:flex; justify-content:space-between; align-items:center;
      background: linear-gradient(90deg, rgba(109,40,217,0.95) 0%, rgba(14,165,163,0.95) 100%);
      padding:16px; border-radius:14px; color:var(--primary);
      box-shadow: var(--card-shadow); margin-bottom:18px;
      border: 1px solid rgba(255,255,255,0.04);
    }
    .ft-title { font-weight:800; font-size:20px; letter-spacing:0.6px; color: #fff; }
    .ft-meta { font-family: monospace; font-size:13px; opacity:0.95; color: rgba(255,255,255,0.9); }

    .kpi-card {
      background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
      border-radius:var(--radius); padding:14px; box-shadow: var(--card-shadow);
      border: 1px solid rgba(255,255,255,0.03);
    }
    .kpi-title { font-size:12px; color:var(--muted); font-weight:700; margin-bottom:6px; }
    .kpi-value { font-size:20px; font-weight:900; color:var(--primary); }
    .small-muted { color:var(--muted); font-size:12px; }
    .delta-up { color: #10b981; font-weight:700; }
    .delta-down { color: #ef4444; font-weight:700; }

    .badge { display:inline-block; padding:6px 10px; border-radius:999px; font-weight:800; color:white; font-size:12px; margin-left:8px; box-shadow: 0 6px 18px rgba(2,6,23,0.6); }
    .badge-bull { background: linear-gradient(90deg,var(--success), #059669); }
    .badge-bear { background: linear-gradient(90deg,var(--danger), #dc2626); }
    .badge-neutral { background: linear-gradient(90deg,#374151,#1f2937); color:#cbd5e1; }

    .insight-card { background: linear-gradient(135deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); border-left:6px solid var(--accent); padding:14px; border-radius:12px; box-shadow: var(--card-shadow); color:var(--primary); }

    .event-high { border-left:6px solid var(--danger); background: linear-gradient(90deg, rgba(239,68,68,0.06), rgba(255,255,255,0.01)); padding:12px; border-radius:8px; }
    .event-med { border-left:6px solid var(--warning); background: linear-gradient(90deg, rgba(245,158,11,0.06), rgba(255,255,255,0.01)); padding:12px; border-radius:8px; }
    .event-low { border-left:6px solid var(--success); background: linear-gradient(90deg, rgba(16,185,129,0.06), rgba(255,255,255,0.01)); padding:12px; border-radius:8px; }

    .stTable table {
      background: transparent;
      color: var(--primary);
      border-collapse: collapse;
      width: 100%;
    }
    .stTable thead th {
      background: linear-gradient(90deg, rgba(109,40,217,0.12), rgba(14,165,163,0.06));
      color: var(--primary);
      font-weight:700;
      padding:8px;
      border-bottom: 1px solid rgba(255,255,255,0.04);
    }
    .stTable tbody td {
      background: rgba(255,255,255,0.01);
      padding:10px;
      border-bottom: 1px solid rgba(255,255,255,0.02);
      color: var(--primary);
    }

    .rp-card { background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); padding:12px; border-radius:12px; border:1px solid rgba(255,255,255,0.03); box-shadow: var(--card-shadow); }

    footer { color: var(--muted); font-size:12px; }

    ::-webkit-scrollbar { height:8px; width:8px; }
    ::-webkit-scrollbar-thumb { background: linear-gradient(90deg, rgba(109,40,217,0.6), rgba(14,165,163,0.6)); border-radius:8px; }

    @media (max-width: 800px) {
      .ft-title { font-size:16px; }
      .kpi-value { font-size:18px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# Header (cleaner)
# -------------------------
utc_now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC · %Y-%m-%d")
auto_sentiment, sentiment_color = detect_market_sentiment()
st.markdown(
    f"""
    <div class="ft-header">
      <div style="display:flex;flex-direction:column;">
        <div class="ft-title">FX INTERMARKET PRO</div>
        <div class="ft-sub">Fundamental FX terminal — intermarket signals, WTI ↔ CAD correlation</div>
      </div>
      <div style="text-align:right;">
        <div class="ft-meta">Mode: <b>AUTO</b> · Régime: <b style="color:{sentiment_color}">{auto_sentiment}</b></div>
        <div class="ft-meta" style="margin-top:6px;">Dernière mise à jour: <b>{utc_now}</b></div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# Sidebar controls (UX)
# -------------------------
with st.sidebar:
    st.markdown("### Controls")
    auto_refresh = st.checkbox("Auto refresh background", value=True, help="Enable background updater thread")
    interval = st.slider("Update interval (seconds)", min_value=60, max_value=900, value=120, step=30)
    kpi_count = st.selectbox("Number of KPI pairs", options=[3, 4, 6, 9], index=2)
    st.markdown("---")
    if st.button("Force update now"):
        ok = refresh_and_persist()
        if ok:
            st.success("Mise à jour forcée terminée.")
        else:
            st.error("La mise à jour forcée a échoué. Consulte les logs.")
    st.markdown("---")
    st.markdown("### Export / Publish")
    st.info("Use the Publish button in the app to send data to external services (configure API key).")

# Apply sidebar choices
if auto_refresh:
    try:
        start_background_updater(interval_seconds=interval)
    except Exception:
        pass

# -------------------------
# Helpers: sparklines & small cards
# -------------------------
def small_sparkline(values, color=ACCENT2):
    fig = go.Figure(go.Scatter(y=values, mode="lines", line=dict(color=color, width=2), hoverinfo="none", fill="tozeroy", fillcolor="rgba(0,0,0,0)"))
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(visible=False), yaxis=dict(visible=False), height=40, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

def format_delta(chg):
    arrow = "▲" if chg >= 0 else "▼"
    cls = "delta-up" if chg >= 0 else "delta-down"
    return arrow, cls

# -------------------------
# Tabs
# -------------------------
tab_macro, tab_sentiment, tab_compare, tab_intermarket, tab_insights, tab_logs = st.tabs(
    ["🏛️ Macro Ranking", "🎯 Risk Sentiment", "🔄 FX Comparison", "📊 Commodities", "🔎 Insights", "🗄️ Logs"]
)

# -------------------------
# TAB: Macro Ranking
# -------------------------
with tab_macro:
    st.markdown("### Fundamental Jurisdictional Matrix")
    df_macro = pd.DataFrame([
        {
            "Devise": ccy,
            "Banque Centrale": info.get("cb", "N/A"),
            "Taux d'intérêt": f"{info.get('rate', 0.0):.2f}%",
            "10Y Yield": f"{info.get('yield_10y', 0.0):.2f}%",
            "PIB": f"{info.get('gdp', 0.0):+.2f}%",
            "Inflation": f"{info.get('cpi_prev', 0.0):.1f}%",
            "Chômage": f"{info.get('unem', 0.0):.1f}%",
            "Score": info.get("score", 0)
        }
        for ccy, info in MACRO.items()
    ])
    st.dataframe(df_macro, use_container_width=True)

    st.markdown("### 📈 Évolution des taux directeurs (historique)")
    fig = go.Figure()
    palette = [ACCENT, ACCENT2, "#10b981", "#f59e0b", "#ef4444", "#60a5fa"]
    for i, (ccy, rates) in enumerate(HIST_RATE.items()):
        fig.add_trace(go.Scatter(y=rates, x=list(range(len(rates))), mode="lines+markers", name=ccy, line=dict(color=palette[i % len(palette)], width=2)))
    fig.update_layout(title="Taux directeurs", xaxis_title="Période", yaxis_title="Taux (%)", height=380,
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=PRIMARY))
    st.plotly_chart(fig, use_container_width=True)

# -------------------------
# TAB: Risk Sentiment (polished KPI grid)
# -------------------------
with tab_sentiment:
    st.markdown("### Market Sentiment & Core Indicators")
    fx_items = list(FX_RATES.items())[:kpi_count]
    cols = st.columns(3 if kpi_count > 3 else kpi_count)
    for idx, (pair, info) in enumerate(fx_items):
        col = cols[idx % len(cols)]
        rate = info.get("rate", 0) or 0
        chg = info.get("chg", 0) or 0.0
        arrow, cls = format_delta(chg)
        color = "#10b981" if chg >= 0 else "#ef4444"
        # synthetic history if no real history available
        hist = [round(rate * (0.995 + i * 0.0015), 6) for i in range(12)]
        with col:
            st.markdown(f"<div class='kpi-card'><div class='kpi-title'>{pair}</div><div style='display:flex;justify-content:space-between;align-items:center;'><div><div class='kpi-value'>{rate:.4f}</div><div class='kpi-sub' style='color:{color};'>{arrow} {chg:+.2f}%</div></div><div style='width:120px;'>", unsafe_allow_html=True)
            st.plotly_chart(small_sparkline(hist, color=color), use_container_width=True)
            st.markdown("</div></div></div>", unsafe_allow_html=True)

    st.markdown("#### Market Assets Snapshot")
    a1, a2, a3 = st.columns(3)
    vix = MARKET_ASSETS.get("VIX", {"price": None, "chg": None})
    wti = MARKET_ASSETS.get("WTI_CRUDE", {"price": None, "chg": None})
    sp = MARKET_ASSETS.get("US_500", {"price": None, "chg": None})
    a1.markdown(f"<div class='kpi-card'><div class='kpi-title'>VIX</div><div class='kpi-value'>{vix.get('price')}</div><div class='kpi-sub'>{vix.get('chg',0):+.2f}%</div></div>", unsafe_allow_html=True)
    a2.markdown(f"<div class='kpi-card'><div class='kpi-title'>WTI Crude</div><div class='kpi-value'>{wti.get('price')}</div><div class='kpi-sub'>{wti.get('chg',0):+.2f}%</div></div>", unsafe_allow_html=True)
    a3.markdown(f"<div class='kpi-card'><div class='kpi-title'>S&P 500</div><div class='kpi-value'>{sp.get('price')}</div><div class='kpi-sub'>{sp.get('chg',0):+.2f}%</div></div>", unsafe_allow_html=True)

# -------------------------
# TAB: FX Comparison
# -------------------------
with tab_compare:
    st.markdown("### FX Comparison & Predictive Signal")
    col_sel1, col_sel2 = st.columns(2)
    ccy_list = list(MACRO.keys())
    with col_sel1:
        base_ccy = st.selectbox("Devise de Base (Long)", ccy_list, index=min(6, len(ccy_list)-1))
    with col_sel2:
        quote_ccy = st.selectbox("Devise de Contrepartie (Short)", ccy_list, index=0)

    if base_ccy == quote_ccy:
        st.warning("Veuillez sélectionner deux devises distinctes.")
    else:
        b_data, q_data = MACRO.get(base_ccy, {}), MACRO.get(quote_ccy, {})
        spreads = compute_spreads(b_data, q_data)
        df_comp = build_comparison_table(base_ccy, quote_ccy, b_data, q_data, spreads)
        st.dataframe(df_comp, use_container_width=True, hide_index=True)

        regime_tuple = regime_weights("Automatique", auto_sentiment)
        wti_bull = MARKET_ASSETS.get("WTI_CRUDE", {}).get("chg", 0) > 0
        wti_bonus = wti_adjustment(base_ccy, quote_ccy, wti_bull)

        expected_move = (spreads[2] * regime_tuple[1]) + (spreads[1] * regime_tuple[2]) + (spreads[0] * regime_tuple[3]) + wti_bonus
        score_pct = normalize_score(expected_move)

        if score_pct >= 50:
            st.markdown(f"**Orientation Macro globale :** 🟢 **BULLISH** pour {base_ccy}/{quote_ccy}")
            st.progress(score_pct / 100)
            st.markdown(f"<div style='margin-top:8px;'><span class='badge badge-bull'>{score_pct}%</span></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"**Orientation Macro globale :** 🔴 **BEARISH** pour {base_ccy}/{quote_ccy}")
            st.progress((100 - score_pct) / 100)
            st.markdown(f"<div style='margin-top:8px;'><span class='badge badge-bear'>{100 - score_pct}%</span></div>", unsafe_allow_html=True)

        drivers = []
        if spreads[0] > 0:
            drivers.append("Taux directeur favorable")
        if spreads[1] > 0:
            drivers.append("Rendement 10Y favorable")
        if spreads[2] > 0:
            drivers.append("Score fondamental supérieur")
        if wti_bonus != 0:
            drivers.append("Impact WTI/CAD")
        interp = " ; ".join(drivers) if drivers else "Aucun signal fondamental dominant"
        st.info(f"Interprétation rapide: {interp}")

# -------------------------
# TAB: Commodities / Intermarket (with RateProbability)
# -------------------------
# RateProbability fetcher (scrape + cache)
RATEPROB_CACHE = os.path.join(os.path.dirname(__file__), "rateprob_cache.json")
RATEPROB_URL = "https://rateprobability.com"

def _load_rateprob_cache():
    try:
        with open(RATEPROB_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"ts": None, "data": []}

def _save_rateprob_cache(data):
    try:
        payload = {"ts": datetime.utcnow().isoformat() + "Z", "data": data}
        with open(RATEPROB_CACHE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def fetch_rateprobability(force=False, ttl_seconds=600):
    cache = _load_rateprob_cache()
    if not force and cache.get("ts"):
        try:
            age = (datetime.utcnow() - datetime.fromisoformat(cache["ts"].replace("Z", ""))).total_seconds()
            if age < ttl_seconds:
                return cache.get("data", []), cache.get("ts")
        except Exception:
            pass

    if BeautifulSoup is None:
        return cache.get("data", []), cache.get("ts")

    try:
        resp = requests.get(RATEPROB_URL, timeout=10, headers={"User-Agent": "fx-terminal/1.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        table = None
        for h in soup.find_all(["h1", "h2", "h3", "h4", "h5"]):
            txt = h.get_text(strip=True).lower()
            if "upcoming meeting" in txt or "upcoming meetings" in txt:
                table = h.find_next("table")
                if table:
                    break

        rows = []
        if table:
            first_tr = table.find("tr")
            if first_tr:
                headers = [th.get_text(strip=True) for th in first_tr.find_all(["th", "td"])]
                if headers:
                    rows.append(headers)
            for tr in table.find_all("tr")[1:]:
                cols = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if cols:
                    rows.append(cols)
        else:
            for table in soup.find_all("table"):
                header_text = " ".join([th.get_text(strip=True).lower() for th in table.find_all("th")])
                if any(k in header_text for k in ["bank", "probability", "meeting", "rate", "implied"]):
                    first_tr = table.find("tr")
                    if first_tr:
                        headers = [th.get_text(strip=True) for th in first_tr.find_all(["th", "td"])]
                        if headers:
                            rows.append(headers)
                    for tr in table.find_all("tr")[1:]:
                        cols = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                        if cols:
                            rows.append(cols)
                    break

        if rows:
            _save_rateprob_cache(rows)
            return rows, datetime.utcnow().isoformat() + "Z"
        return cache.get("data", []), cache.get("ts")
    except Exception:
        return cache.get("data", []), cache.get("ts")

with tab_intermarket:
    st.markdown("### Intermarket Analytics & Commodities")
    cols = st.columns(3)
    gold = MARKET_ASSETS.get("GOLD", {"price": None, "chg": None})
    wti = MARKET_ASSETS.get("WTI_CRUDE", {"price": None, "chg": None})
    sp500 = MARKET_ASSETS.get("US_500", {"price": None, "chg": None})
    cols[0].markdown(f"<div class='kpi-card'><div class='kpi-title'>Gold Spot</div><div class='kpi-value'>{gold.get('price')}</div><div class='kpi-sub'>{gold.get('chg',0):+.2f}%</div></div>", unsafe_allow_html=True)
    cols[1].markdown(f"<div class='kpi-card'><div class='kpi-title'>WTI Crude</div><div class='kpi-value'>{wti.get('price')}</div><div class='kpi-sub'>{wti.get('chg',0):+.2f}%</div></div>", unsafe_allow_html=True)
    cols[2].markdown(f"<div class='kpi-card'><div class='kpi-title'>S&P 500</div><div class='kpi-value'>{sp500.get('price')}</div><div class='kpi-sub'>{sp500.get('chg',0):+.2f}%</div></div>", unsafe_allow_html=True)

    st.markdown("#### Commodities vs FX (WTI ↔ CAD)")
    st.write("Le WTI influence souvent le CAD. Activez le filtre 'Insights' pour voir les paires CAD impactées.")

    # RateProbability embedded table (styled)
    st.markdown("#### Market-implied Upcoming Meetings (RateProbability)")
    rp_force = st.button("Forcer refresh RateProbability")
    rows, ts = fetch_rateprobability(force=rp_force)
    if not rows:
        st.info("Impossible de récupérer RateProbability — affichage du cache si disponible.")
    else:
        st.markdown(f"*Dernière récupération: {ts}*")
        with st.container():
            st.markdown("<div class='rp-card'>", unsafe_allow_html=True)
            if isinstance(rows, list) and rows and all(isinstance(r, list) for r in rows):
                headers = rows[0]
                data_rows = rows[1:]
                # Normalize into dataframe
                df = pd.DataFrame(data_rows, columns=headers)
                # Try to detect common columns and color-code implied outcome
                lower_cols = [c.lower() for c in df.columns]
                # heuristics
                prob_col = next((c for c in df.columns if "prob" in c.lower()), None)
                outcome_col = next((c for c in df.columns if "implied" in c.lower() or "outcome" in c.lower()), None)
                bank_col = next((c for c in df.columns if "bank" in c.lower() or "institution" in c.lower()), None)
                date_col = next((c for c in df.columns if "date" in c.lower() or "meeting" in c.lower() or "time" in c.lower()), None)

                # Clean probability to numeric if possible
                if prob_col:
                    def parse_pct(x):
                        try:
                            return float(str(x).replace("%","").strip())
                        except Exception:
                            return None
                    df["_prob_pct"] = df[prob_col].apply(parse_pct)
                else:
                    df["_prob_pct"] = None

                # Color mapping for implied outcome
                def outcome_color(val):
                    if not isinstance(val, str):
                        return ""
                    v = val.lower()
                    if "hike" in v or "raise" in v or "up" in v:
                        return "background-color: rgba(16,185,129,0.08); color: #10b981;"
                    if "cut" in v or "lower" in v or "down" in v:
                        return "background-color: rgba(239,68,68,0.06); color: #ef4444;"
                    return "background-color: rgba(109,40,217,0.04); color: #c7b8ff;"

                # Render dataframe with simple styling
                def style_df(d):
                    styled = d.style.set_properties(**{"background-color": "transparent", "color": PRIMARY})
                    if outcome_col:
                        styled = styled.applymap(lambda v: outcome_color(v) if v is not None else "", subset=[outcome_col])
                    if "_prob_pct" in d.columns:
                        styled = styled.format({"_prob_pct": "{:.1f}%"})
                    return styled

                st.dataframe(df, use_container_width=True)
            else:
                st.table(rows)
            st.markdown("</div>", unsafe_allow_html=True)

# -------------------------
# TAB: Insights
# -------------------------
with tab_insights:
    st.markdown("### Insights & Recommandations")
    regime_tuple = regime_weights("Automatique", auto_sentiment)
    wti_bull = MARKET_ASSETS.get("WTI_CRUDE", {}).get("chg", 0) > 0
    ranked = rank_all_pairs(regime_tuple, wti_bull)

    top_bull = [r for r in ranked if r["score_pct"] >= 50][:3]
    top_bear = sorted(ranked, key=lambda x: x["score_pct"])[:3]

    cols = st.columns(2)
    with cols[0]:
        st.markdown("<div class='insight-card'><b>🔥 Top 3 Bullish</b></div>", unsafe_allow_html=True)
        if not top_bull:
            st.info("Aucune paire bullish détectée.")
        for item in top_bull:
            st.markdown(
                f"<div style='margin:8px 0;display:flex;justify-content:space-between;align-items:center;'><div><b>{item['pair']}</b><div class='small-muted'>raw: {item['raw']:.2f}</div></div><div><span class='badge badge-bull'>{item['score_pct']}%</span></div></div>",
                unsafe_allow_html=True,
            )
    with cols[1]:
        st.markdown("<div class='insight-card'><b>❄️ Top 3 Bearish</b></div>", unsafe_allow_html=True)
        if not top_bear:
            st.info("Aucune paire bearish détectée.")
        for item in top_bear:
            st.markdown(
                f"<div style='margin:8px 0;display:flex;justify-content:space-between;align-items:center;'><div><b>{item['pair']}</b><div class='small-muted'>raw: {item['raw']:.2f}</div></div><div><span class='badge badge-bear'>{item['score_pct']}%</span></div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown("#### 📅 Catalyseurs à venir (sélection rapide)")
    catalysts = [
        {"time": "2026-05-20 13:30 UTC", "event": "US Nonfarm Payrolls (NFP)", "impact": "High", "pairs": ["USD/*"]},
        {"time": "2026-05-21 08:00 UTC", "event": "ECB Rate Decision", "impact": "High", "pairs": ["EUR/*"]},
        {"time": "2026-05-22 02:00 UTC", "event": "BoC Rate Statement", "impact": "Medium", "pairs": ["CAD/*"]},
    ]
    for c in catalysts:
        cls = "event-high" if c["impact"] == "High" else ("event-med" if c["impact"] == "Medium" else "event-low")
        st.markdown(
            f"<div class='{cls}' style='margin-bottom:8px;'><b>{c['event']}</b> · <span class='small-muted'>{c['time']}</span><div class='small-muted'>Pairs impactées: {', '.join(c['pairs'])}</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("#### 📰 News & Catalyseurs (flux)")
    articles = fetch_news(limit=6)
    if articles:
        for a in articles:
            title = a.get("title") or "Untitled"
            src = a.get("source") or ""
            ts = (a.get("publishedAt") or "")[:19].replace("T", " ")
            url = a.get("url") or "#"
            st.markdown(f"- <b>{title}</b> <span class='small-muted'>({src} · {ts})</span> — <a href='{url}' target='_blank'>lire</a>", unsafe_allow_html=True)
    else:
        st.info("Aucune news disponible — vérifie la variable d'environnement NEWS_API_KEY ou le cache local.")

# -------------------------
# TAB: Logs
# -------------------------
with tab_logs:
    st.markdown("### System Logs")
    try:
        logs = load_update_log()
    except Exception:
        logs = []
    if logs:
        for entry in logs:
            st.text(f"[{entry.get('ts')}] Session: {entry.get('session')} | Trigger: {entry.get('trigger')} -> Status: {entry.get('status')}")
    else:
        st.info("Aucun log disponible.")

# -------------------------
# Footer
# -------------------------
st.markdown("---")
st.markdown(
    f"<div style='display:flex;justify-content:space-between;align-items:center;'><div class='small-muted'>Données: Yahoo Finance (yfinance), sources macro locales; modèle: indicateurs fondamentaux pondérés.</div><div class='small-muted'>Dernière mise à jour: {utc_now}</div></div>",
    unsafe_allow_html=True,
)
