# app.py
"""
FX Intermarket Pro — v3.0
Professional dark Fintech terminal. UI/UX redesign (complete, corrected).
Table text colors adjusted for high contrast on dark blue background.
"""

import os
import json
import time
import requests
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go

# Optional: BeautifulSoup for scraping RateProbability
try:
    from bs4 import BeautifulSoup
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

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="FX Intermarket Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Start background updater (idempotent)
try:
    start_background_updater(interval_seconds=120)
except Exception:
    pass

# ─────────────────────────────────────────────
# Design tokens & global CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
/* ── Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ── Tokens ── */
:root {
  --bg:       #071028;
  --surface:  #0d1424;
  --panel:    #0f1726;
  --border:   rgba(255,255,255,0.06);
  --border-hi:rgba(255,255,255,0.12);

  --accent:   #7c3aed;
  --accent-2: #0891b2;
  --accent-g: linear-gradient(135deg, #7c3aed 0%, #0891b2 100%);

  --txt:      #ffffff;
  --txt-2:    #cbd5e1;
  --txt-3:    #94a3b8;

  --up:    #10b981;
  --down:  #f43f5e;
  --warn:  #f59e0b;
  --info:  #38bdf8;

  --z1: 0 1px 4px rgba(0,0,0,.4);
  --z2: 0 4px 16px rgba(0,0,0,.55);
  --z3: 0 8px 32px rgba(0,0,0,.65);
  --z4: 0 20px 60px rgba(0,0,0,.8);

  --r:  10px;
  --r2: 14px;
  --r3: 18px;
}

/* ── Reset body ── */
html, body, .stApp, .main, [data-testid="stAppViewContainer"] {
  background: linear-gradient(180deg, #071028 0%, #041022 100%) !important;
  color: var(--txt);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 14px;
  line-height: 1.55;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden !important; }
[data-testid="stDecoration"] { display: none !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(124,58,237,.4); border-radius: 6px; }
::-webkit-scrollbar-thumb:hover { background: rgba(124,58,237,.7); }

/* TOPBAR */
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(100deg, rgba(124,58,237,0.18) 0%, rgba(8,145,178,0.12) 100%);
  border: 1px solid var(--border-hi);
  border-radius: var(--r3);
  padding: 14px 22px;
  margin-bottom: 20px;
  box-shadow: var(--z3);
  backdrop-filter: blur(12px);
}
.topbar-brand { display:flex; align-items:center; gap:12px; }
.topbar-logo { width:36px; height:36px; background:var(--accent-g); border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:18px; box-shadow:0 0 18px rgba(124,58,237,.5); }
.topbar-title { font-size:18px; font-weight:800; background:var(--accent-g); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.topbar-sub { font-size:11px; color:var(--txt-2); margin-top:1px; }
.topbar-right { text-align:right; }
.regime-pill { display:inline-flex; align-items:center; gap:6px; padding:4px 12px; border-radius:999px; font-size:12px; font-weight:700; box-shadow:var(--z1); }
.regime-bull { background: rgba(16,185,129,.12); color: #10b981; border:1px solid rgba(16,185,129,.2); }
.regime-bear { background: rgba(244,63,94,.12); color: #f43f5e; border:1px solid rgba(244,63,94,.2); }
.regime-neut { background: rgba(148,163,184,.08); color: #94a3b8; border:1px solid rgba(148,163,184,.12); }
.topbar-ts { font-family:'JetBrains Mono', monospace; font-size:11px; color:var(--txt-3); margin-top:4px; }

/* SIDEBAR */
[data-testid="stSidebar"] { background: var(--surface) !important; border-right:1px solid var(--border) !important; }
.sidebar-section { background: var(--panel); border:1px solid var(--border); border-radius:var(--r); padding:14px; margin-bottom:12px; }
.sidebar-section label { font-size:12px !important; color:var(--txt-2) !important; }

/* KPI */
.kpi { background: var(--panel); border:1px solid var(--border); border-radius:var(--r2); padding:16px; box-shadow:var(--z2); position:relative; overflow:hidden; }
.kpi-label { font-size:10px; font-weight:700; color:var(--txt-2); margin-bottom:8px; }
.kpi-val { font-family:'JetBrains Mono', monospace; font-size:22px; font-weight:700; color:var(--txt); margin-bottom:4px; }
.kpi-delta { font-family:'JetBrains Mono', monospace; font-size:12px; font-weight:600; }

/* Section title */
.sec-title { font-size:13px; font-weight:700; color:var(--txt-2); margin:20px 0 12px; display:flex; align-items:center; gap:8px; }
.sec-dot { width:6px; height:6px; border-radius:50%; background:var(--accent-g); }

/* Data table overrides for Streamlit default tables */
.stDataFrame { border-radius:var(--r2) !important; overflow:hidden !important; border:1px solid var(--border) !important; box-shadow:var(--z2) !important; }
.stDataFrame [data-testid="stDataFrameResizable"] { background: var(--panel) !important; }
.stDataFrame th { background: rgba(124,58,237,.08) !important; color: var(--txt) !important; font-size:11px !important; font-weight:700 !important; text-transform:uppercase !important; }
.stDataFrame td { color: var(--txt) !important; font-family:'JetBrains Mono', monospace !important; font-size:12px !important; }

/* RP wrap */
.rp-wrap { background: var(--panel); border:1px solid var(--border); border-radius:var(--r2); overflow:hidden; box-shadow:var(--z2); padding:8px; }

/* Misc */
.info-box { background: rgba(56,189,248,.07); border:1px solid rgba(56,189,248,.2); border-radius:var(--r); padding:12px 16px; color:#7dd3fc; margin:8px 0; }
.warn-box { background: rgba(245,158,11,.07); border:1px solid rgba(245,158,11,.2); border-radius:var(--r); padding:12px 16px; color:#fcd34d; margin:8px 0; }

/* Streamlit tabs */
.stTabs [data-baseweb="tab-list"] { gap:4px !important; background:var(--surface) !important; padding:4px !important; border-radius:var(--r) !important; border:1px solid var(--border) !important; }
.stTabs [data-baseweb="tab"] { border-radius:8px !important; padding:8px 16px !important; font-size:13px !important; font-weight:600 !important; color:var(--txt-2) !important; background:transparent !important; }
.stTabs [aria-selected="true"] { background:var(--panel) !important; color:var(--txt) !important; box-shadow:var(--z1) !important; }

/* Reduce-motion */
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { transition-duration:0.01ms !important; animation-duration:0.01ms !important; } }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def sparkline(values, color="#10b981", height=44):
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    rgb = hex_to_rgb(color) if isinstance(color, str) and color.startswith("#") else (16,185,129)
    fill = f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0.08)"
    fig = go.Figure(go.Scatter(
        y=values, mode="lines",
        line=dict(color=color, width=2),
        fill="tozeroy",
        fillcolor=fill,
        hoverinfo="none",
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False, fixedrange=True),
        yaxis=dict(visible=False, fixedrange=True),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig

def delta_html(chg):
    arrow = "▲" if chg >= 0 else "▼"
    cls = "kpi-up" if chg >= 0 else "kpi-down"
    color = "#10b981" if chg >= 0 else "#f43f5e"
    return f'<span style="color:{color}; font-weight:700;">{arrow} {abs(chg):.2f}%</span>'

def regime_class(sentiment):
    s = (sentiment or "").lower()
    if "bull" in s or "risk on" in s: return "regime-bull", "🟢"
    if "bear" in s or "risk off" in s: return "regime-bear", "🔴"
    return "regime-neut", "⚪"

# HTML table renderer for Macro (robust alternative to pandas Styler)
def score_style_html(val):
    try:
        v = float(val)
    except Exception:
        return f'<span style="color:var(--txt);">{val}</span>'
    if v >= 70:
        color = "#10b981"
    elif v >= 40:
        color = "#f59e0b"
    else:
        color = "#f43f5e"
    pct = max(0, min(100, int(v)))
    bar = (
        f'<div style="width:100%; background:rgba(255,255,255,0.03); height:8px; border-radius:999px; overflow:hidden;">'
        f'<div style="width:{pct}%; height:100%; background:linear-gradient(90deg,{color}, rgba(255,255,255,0.06));"></div></div>'
    )
    return f'<div style="display:flex;flex-direction:column;gap:6px;align-items:center;"><div style="font-weight:700;color:{color};">{v:.0f}</div>{bar}</div>'

def df_to_html_table(df, height=320):
    # Build header
    cols = list(df.columns)
    thead = "<tr>" + "".join([
        f'<th style="padding:10px;text-align:center;font-weight:700;color:var(--txt);font-size:12px;border-bottom:1px solid rgba(255,255,255,0.04);">{c}</th>'
        for c in cols
    ]) + "</tr>"

    # Build rows
    tbody_rows = []
    for _, row in df.iterrows():
        cells = []
        for c in cols:
            val = row[c]
            if c == "Score":
                cell_html = score_style_html(val)
                cells.append(f'<td style="padding:12px;text-align:center;vertical-align:middle;background:transparent;color:var(--txt);">{cell_html}</td>')
            else:
                # ensure readable white text for all cells
                cells.append(f'<td style="padding:12px;text-align:center;font-family:JetBrains Mono;color:var(--txt);">{val}</td>')
        tbody_rows.append("<tr>" + "".join(cells) + "</tr>")
    tbody = "\n".join(tbody_rows)

    table_html = f"""
    <div style="border-radius:12px; overflow:hidden; border:1px solid rgba(255,255,255,0.06); box-shadow: 0 6px 18px rgba(2,6,23,0.55); background:transparent;">
      <table style="width:100%; border-collapse:collapse; background:transparent;">
        <thead style="background:rgba(124,58,237,0.06);">{thead}</thead>
        <tbody>{tbody}</tbody>
      </table>
    </div>
    """
    wrapper = f'<div style="padding:8px; height:{height}px; overflow:auto;">{table_html}</div>'
    return wrapper

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
utc_now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC · %Y-%m-%d")
auto_sentiment, sentiment_color = detect_market_sentiment()
r_cls, r_dot = regime_class(auto_sentiment)

st.markdown(f"""
<div class="topbar">
  <div class="topbar-brand">
    <div class="topbar-logo">📈</div>
    <div>
      <div class="topbar-title">FX INTERMARKET PRO</div>
      <div class="topbar-sub">Terminal fondamental · signaux intermarché · corrélation WTI ↔ CAD</div>
    </div>
  </div>
  <div class="topbar-right">
    <div>
      <span class="regime-pill {r_cls}">{r_dot} Régime: {auto_sentiment}</span>
    </div>
    <div class="topbar-ts">{utc_now}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Paramètres")
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    auto_refresh = st.checkbox("Auto-refresh", value=True, help="Mise à jour en arrière-plan")
    interval = st.slider("Intervalle (sec)", min_value=60, max_value=900, value=120, step=30)
    kpi_count = st.selectbox("Paires KPI affichées", options=[3, 4, 6, 9], index=2)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Actions")
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    if st.button("⚡ Forcer mise à jour"):
        ok = refresh_and_persist()
        if ok:
            st.success("✓ Mise à jour terminée")
        else:
            st.error("✗ Échec — consulter les logs")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Export")
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Configurez votre clé API pour publier vers des services externes.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

if auto_refresh:
    try:
        start_background_updater(interval_seconds=interval)
    except Exception:
        pass

# ─────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────
tab_macro, tab_sentiment, tab_compare, tab_intermarket, tab_insights, tab_logs = st.tabs([
    "🏛  Macro", "🎯  Sentiment", "🔄  Comparaison", "📊  Commodités", "🔎  Insights", "🗄  Logs"
])

# ═══════════════════════════════════════════
# TAB — MACRO
# ═══════════════════════════════════════════
with tab_macro:
    st.markdown('<div class="sec-title"><span class="sec-dot"></span> Matrice Juridictionnelle Fondamentale</div>', unsafe_allow_html=True)

    df_macro = pd.DataFrame([
        {
            "Devise":          ccy,
            "Banque Centrale": info.get("cb", "N/A"),
            "Taux (%)":        round(info.get("rate", 0.0), 2),
            "10Y Yield (%)":   round(info.get("yield_10y", 0.0), 2),
            "PIB (%)":         round(info.get("gdp", 0.0), 2),
            "Inflation (%)":   round(info.get("cpi_prev", 0.0), 1),
            "Chômage (%)":     round(info.get("unem", 0.0), 1),
            "Score":           info.get("score", 0),
        }
        for ccy, info in MACRO.items()
    ])

    # --- Robust Macro table rendering: try HTML card, fallback to st.dataframe ---
    try:
        html_table = df_to_html_table(df_macro, height=360)
        components.html(html_table, height=420, scrolling=True)
        st.markdown("<div style='margin-top:8px;color:#cbd5e1;font-size:12px;'>Si le tableau stylé n'apparaît pas, voici une version alternative :</div>", unsafe_allow_html=True)
        st.dataframe(df_macro, use_container_width=True, height=220)
    except Exception:
        st.warning("Rendu HTML du tableau indisponible — affichage de secours.")
        st.dataframe(df_macro, use_container_width=True, height=360)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-title"><span class="sec-dot"></span> Évolution des Taux Directeurs</div>', unsafe_allow_html=True)

    palette = ["#7c3aed", "#0891b2", "#10b981", "#f59e0b", "#f43f5e", "#60a5fa"]
    fig = go.Figure()
    for i, (ccy, rates) in enumerate(HIST_RATE.items()):
        fig.add_trace(go.Scatter(
            y=rates, x=list(range(len(rates))),
            mode="lines+markers",
            name=ccy,
            line=dict(color=palette[i % len(palette)], width=2.5),
            marker=dict(size=5),
        ))
    fig.update_layout(
        height=360,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", family="Inter"),
        xaxis=dict(
            title="Période",
            gridcolor="rgba(255,255,255,.04)",
            linecolor="rgba(255,255,255,.06)",
            tickfont=dict(size=11),
        ),
        yaxis=dict(
            title="Taux (%)",
            gridcolor="rgba(255,255,255,.04)",
            linecolor="rgba(255,255,255,.06)",
            tickfont=dict(size=11),
        ),
        legend=dict(
            bgcolor="rgba(13,20,36,.9)",
            bordercolor="rgba(255,255,255,.06)",
            borderwidth=1,
            font=dict(size=12),
        ),
        hovermode="x unified",
        margin=dict(l=8, r=8, t=8, b=8),
    )
    st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════
# TAB — SENTIMENT / KPI
# ═══════════════════════════════════════════
with tab_sentiment:
    st.markdown('<div class="sec-title"><span class="sec-dot"></span> Core FX Indicators</div>', unsafe_allow_html=True)

    fx_items = list(FX_RATES.items())[:kpi_count]
    cols_per_row = 3
    rows_fx = [fx_items[i:i+cols_per_row] for i in range(0, len(fx_items), cols_per_row)]

    for row in rows_fx:
        cols = st.columns(len(row))
        for col, (pair, info) in zip(cols, row):
            rate = info.get("rate", 0) or 0
            chg  = info.get("chg",  0) or 0.0
            color = "#10b981" if chg >= 0 else "#f43f5e"
            hist = [round(rate * (0.994 + i * 0.0015 + (0.001 if i % 3 == 0 else 0)), 6) for i in range(16)]
            with col:
                st.markdown(f"""
                <div class="kpi">
                  <div class="kpi-label">{pair}</div>
                  <div class="kpi-val">{rate:.4f}</div>
                  <div class="kpi-delta">{delta_html(chg)}</div>
                </div>
                """, unsafe_allow_html=True)
                st.plotly_chart(sparkline(hist, color=color), use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-title"><span class="sec-dot"></span> Market Assets Snapshot</div>', unsafe_allow_html=True)

    asset_defs = [
        ("VIX",       "🌊", "VIX"),
        ("WTI_CRUDE", "🛢", "WTI Crude"),
        ("US_500",    "📈", "S&P 500"),
        ("GOLD",      "✦",  "Gold Spot"),
    ]
    acols = st.columns(4)
    for col, (key, icon, label) in zip(acols, asset_defs):
        a = MARKET_ASSETS.get(key, {"price": "—", "chg": 0})
        price = a.get("price") or "—"
        chg   = a.get("chg", 0) or 0
        with col:
            st.markdown(f"""
            <div class="kpi">
              <div class="kpi-icon">{icon}</div>
              <div class="kpi-label">{label}</div>
              <div class="kpi-val">{price}</div>
              <div class="kpi-delta">{delta_html(chg)}</div>
            </div>
            """, unsafe_allow_html=True)

# ═══════════════════════════════════════════
# TAB — COMPARISON
# ═══════════════════════════════════════════
with tab_compare:
    st.markdown('<div class="sec-title"><span class="sec-dot"></span> Comparaison FX & Signal Prédictif</div>', unsafe_allow_html=True)

    ccy_list = list(MACRO.keys())
    c1, c2 = st.columns(2)
    with c1:
        base_ccy  = st.selectbox("Devise Long (Base)", ccy_list, index=min(6, len(ccy_list)-1))
    with c2:
        quote_ccy = st.selectbox("Devise Short (Contrepartie)", ccy_list, index=0)

    if base_ccy == quote_ccy:
        st.markdown('<div class="warn-box">⚠ Sélectionnez deux devises distinctes.</div>', unsafe_allow_html=True)
    else:
        b_data, q_data = MACRO.get(base_ccy, {}), MACRO.get(quote_ccy, {})
        spreads = compute_spreads(b_data, q_data)
        df_comp = build_comparison_table(base_ccy, quote_ccy, b_data, q_data, spreads)

        st.dataframe(df_comp, use_container_width=True)

        regime_tuple = regime_weights("Automatique", auto_sentiment)
        wti_bull = MARKET_ASSETS.get("WTI_CRUDE", {}).get("chg", 0) > 0
        wti_bonus = wti_adjustment(base_ccy, quote_ccy, wti_bull)

        expected_move = (spreads[2] * regime_tuple[1]) + (spreads[1] * regime_tuple[2]) + (spreads[0] * regime_tuple[3]) + wti_bonus
        score_pct = normalize_score(expected_move)

        # Signal box
        st.markdown('<div class="signal-box">', unsafe_allow_html=True)
        if score_pct >= 50:
            st.markdown(f'<div class="signal-main sig-bull">BULLISH — {score_pct}%</div>', unsafe_allow_html=True)
            bar_html = f'<div class="signal-bar-wrap"><div class="signal-bar bar-up" style="width:{score_pct}%;"></div></div>'
        else:
            st.markdown(f'<div class="signal-main sig-bear">BEARISH — {100-score_pct}%</div>', unsafe_allow_html=True)
            bar_html = f'<div class="signal-bar-wrap"><div class="signal-bar bar-down" style="width:{100-score_pct}%;"></div></div>'
        st.markdown(bar_html, unsafe_allow_html=True)
        drivers = []
        if spreads[0] > 0:
            drivers.append("Taux directeur favorable")
        if spreads[1] > 0:
            drivers.append("Rendement 10Y favorable")
        if spreads[2] > 0:
            drivers.append("Score fondamental supérieur")
        if wti_bonus != 0:
            drivers.append("Impact WTI/CAD")
        if drivers:
            chips = " ".join([f'<span class="driver-chip">{d}</span>' for d in drivers])
            st.markdown(f'<div class="signal-drivers">{chips}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════
# TAB — COMMODITIES / INTERMARKET (with RateProbability)
# ═══════════════════════════════════════════
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
    st.markdown('<div class="sec-title"><span class="sec-dot"></span> Intermarket Analytics & Commodities</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    gold = MARKET_ASSETS.get("GOLD", {"price": None, "chg": None})
    wti = MARKET_ASSETS.get("WTI_CRUDE", {"price": None, "chg": None})
    sp500 = MARKET_ASSETS.get("US_500", {"price": None, "chg": None})
    cols[0].markdown(f"<div class='kpi'><div class='kpi-icon'>✦</div><div class='kpi-label'>Gold Spot</div><div class='kpi-val'>{gold.get('price')}</div><div class='kpi-delta'>{delta_html(gold.get('chg',0))}</div></div>", unsafe_allow_html=True)
    cols[1].markdown(f"<div class='kpi'><div class='kpi-icon'>🛢</div><div class='kpi-label'>WTI Crude</div><div class='kpi-val'>{wti.get('price')}</div><div class='kpi-delta'>{delta_html(wti.get('chg',0))}</div></div>", unsafe_allow_html=True)
    cols[2].markdown(f"<div class='kpi'><div class='kpi-icon'>📈</div><div class='kpi-label'>S&P 500</div><div class='kpi-val'>{sp500.get('price')}</div><div class='kpi-delta'>{delta_html(sp500.get('chg',0))}</div></div>", unsafe_allow_html=True)

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
            st.markdown("<div class='rp-wrap'>", unsafe_allow_html=True)
            if isinstance(rows, list) and rows and all(isinstance(r, list) for r in rows):
                headers = rows[0]
                data_rows = rows[1:]
                try:
                    df = pd.DataFrame(data_rows, columns=headers)
                except Exception:
                    df = pd.DataFrame(data_rows)
                prob_col = next((c for c in df.columns if "prob" in c.lower()), None)
                if prob_col:
                    def parse_pct(x):
                        try:
                            return float(str(x).replace("%","").strip())
                        except Exception:
                            return None
                    df["_prob_pct"] = df[prob_col].apply(parse_pct)
                else:
                    df["_prob_pct"] = None
                st.dataframe(df, use_container_width=True)
            else:
                st.table(rows)
            st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════
# TAB — INSIGHTS
# ═══════════════════════════════════════════
with tab_insights:
    st.markdown('<div class="sec-title"><span class="sec-dot"></span> Insights & Recommandations</div>', unsafe_allow_html=True)
    regime_tuple = regime_weights("Automatique", auto_sentiment)
    wti_bull = MARKET_ASSETS.get("WTI_CRUDE", {}).get("chg", 0) > 0
    ranked = rank_all_pairs(regime_tuple, wti_bull)

    top_bull = [r for r in ranked if r["score_pct"] >= 50][:3]
    top_bear = sorted(ranked, key=lambda x: x["score_pct"])[:3]

    cols = st.columns(2)
    with cols[0]:
        st.markdown("<div class='insight-pair'><div><div class='pair-name'>Top 3 Bullish</div></div></div>", unsafe_allow_html=True)
        if not top_bull:
            st.info("Aucune paire bullish détectée.")
        for item in top_bull:
            pct = item.get("score_pct", 0)
            raw = item.get("raw", 0)
            st.markdown(
                f"<div class='insight-pair'><div><div class='pair-name'>{item['pair']}</div><div class='pair-raw'>raw: {raw:.2f}</div></div><div><span class='badge badge-up'>{pct}%</span></div></div>",
                unsafe_allow_html=True,
            )
    with cols[1]:
        st.markdown("<div class='insight-pair'><div><div class='pair-name'>Top 3 Bearish</div></div></div>", unsafe_allow_html=True)
        if not top_bear:
            st.info("Aucune paire bearish détectée.")
        for item in top_bear:
            pct = item.get("score_pct", 0)
            raw = item.get("raw", 0)
            st.markdown(
                f"<div class='insight-pair'><div><div class='pair-name'>{item['pair']}</div><div class='pair-raw'>raw: {raw:.2f}</div></div><div><span class='badge badge-down'>{pct}%</span></div></div>",
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
        st.markdown(
            f"<div class='event-card'><div class='event-pip event-high-pip'></div><div><div class='event-name'>{c['event']}</div><div class='event-meta'>{c['time']}</div><div class='event-pairs'>Pairs impactées: {', '.join(c['pairs'])}</div></div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("#### 📰 News & Catalyseurs (flux)")
    articles = fetch_news(limit=6)
    if articles:
        for i, a in enumerate(articles, 1):
            title = a.get("title") or "Untitled"
            src = a.get("source") or ""
            ts = (a.get("publishedAt") or "")[:19].replace("T", " ")
            url = a.get("url") or "#"
            st.markdown(f"<div class='news-item'><div class='news-num'>{i}</div><div><div class='news-title'><a href='{url}' target='_blank'>{title}</a></div><div class='news-meta'>{src} · {ts}</div></div></div>", unsafe_allow_html=True)
    else:
        st.info("Aucune news disponible — vérifie la variable d'environnement NEWS_API_KEY ou le cache local.")

# ═══════════════════════════════════════════
# TAB — LOGS
# ═══════════════════════════════════════════
with tab_logs:
    st.markdown('<div class="sec-title"><span class="sec-dot"></span> System Logs</div>', unsafe_allow_html=True)
    try:
        logs = load_update_log()
    except Exception:
        logs = []
    if logs:
        for entry in logs:
            status_cls = "log-ok" if entry.get("status") == "success" else "log-fail"
            st.markdown(f"<div class='log-entry'><div class='log-ts'>{entry.get('ts')}</div><div style='flex:1'>{entry.get('session')} · {entry.get('trigger')}</div><div class='{status_cls}'>{entry.get('status')}</div></div>", unsafe_allow_html=True)
    else:
        st.info("Aucun log disponible.")

# ─────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"<div style='display:flex;justify-content:space-between;align-items:center;'><div style='color:#cbd5e1;'>Données: Yahoo Finance (yfinance), sources macro locales; modèle: indicateurs fondamentaux pondérés.</div><div style='color:#cbd5e1;'>Dernière mise à jour: {utc_now}</div></div>",
    unsafe_allow_html=True,
)
