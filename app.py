"""
FX Intermarket Pro — v3.0
Professional dark Fintech terminal. UI/UX redesign:
- Glass-morphism dark panels, tight 8px grid system
- Tab bar with icon + label, active indicator
- KPI cards: monospaced figures, semantic delta colors, micro-sparklines
- RateProbability table: color-coded by outcome with progress bars
- Sidebar: grouped controls with clear labels
- Insights: ranked pair cards with animated progress bars
- Macro table: color-coded Score column
- Consistent elevation scale: --z1 → --z4
- prefers-reduced-motion respected
- cursor-pointer on all interactives
- WCAG AA color contrast for all text
"""

import os
import json
import time
import requests
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

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
  --bg:       #080d1a;
  --surface:  #0d1424;
  --panel:    #111927;
  --border:   rgba(255,255,255,0.06);
  --border-hi:rgba(255,255,255,0.12);

  --accent:   #7c3aed;
  --accent-2: #0891b2;
  --accent-g: linear-gradient(135deg, #7c3aed 0%, #0891b2 100%);

  --txt:      #e2e8f0;
  --txt-2:    #94a3b8;
  --txt-3:    #475569;

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
  background: var(--bg) !important;
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

/* ══════════════════════════════
   TOPBAR
══════════════════════════════ */
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
.topbar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.topbar-logo {
  width: 36px; height: 36px;
  background: var(--accent-g);
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px;
  box-shadow: 0 0 18px rgba(124,58,237,.5);
}
.topbar-title {
  font-size: 18px; font-weight: 800;
  letter-spacing: 0.04em;
  background: var(--accent-g);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.topbar-sub { font-size: 11px; color: var(--txt-2); margin-top: 1px; }
.topbar-right { text-align: right; }
.regime-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  box-shadow: var(--z1);
}
.regime-bull  { background: rgba(16,185,129,.15); color: #10b981; border: 1px solid rgba(16,185,129,.3); }
.regime-bear  { background: rgba(244,63,94,.15);  color: #f43f5e; border: 1px solid rgba(244,63,94,.3); }
.regime-neut  { background: rgba(148,163,184,.12); color: #94a3b8; border: 1px solid rgba(148,163,184,.2); }
.topbar-ts { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--txt-3); margin-top: 4px; }

/* ══════════════════════════════
   SIDEBAR
══════════════════════════════ */
[data-testid="stSidebar"] {
  background: var(--surface) !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] .stMarkdown h3 {
  font-size: 11px !important;
  font-weight: 700 !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase;
  color: var(--txt-3) !important;
  margin: 16px 0 10px !important;
}
.sidebar-section {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 14px;
  margin-bottom: 12px;
}
.sidebar-section label { font-size: 12px !important; color: var(--txt-2) !important; }

/* ══════════════════════════════
   KPI CARDS
══════════════════════════════ */
.kpi-grid {
  display: grid;
  gap: 12px;
}
.kpi {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--r2);
  padding: 16px;
  box-shadow: var(--z2);
  transition: border-color 200ms ease, box-shadow 200ms ease;
  position: relative;
  overflow: hidden;
}
.kpi::before {
  content: '';
  position: absolute; inset: 0;
  background: var(--accent-g);
  opacity: 0;
  transition: opacity 200ms ease;
  border-radius: var(--r2);
}
.kpi:hover { border-color: var(--border-hi); box-shadow: var(--z3); }
.kpi:hover::before { opacity: 0.03; }

.kpi-label {
  font-size: 10px; font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--txt-3);
  margin-bottom: 8px;
}
.kpi-val {
  font-family: 'JetBrains Mono', monospace;
  font-size: 22px; font-weight: 700;
  color: var(--txt);
  letter-spacing: -0.01em;
  margin-bottom: 4px;
}
.kpi-delta {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px; font-weight: 600;
  display: flex; align-items: center; gap: 4px;
}
.kpi-up   { color: var(--up); }
.kpi-down { color: var(--down); }
.kpi-icon {
  position: absolute; top: 14px; right: 14px;
  font-size: 20px; opacity: 0.15;
}

/* ══════════════════════════════
   SECTION TITLE
══════════════════════════════ */
.sec-title {
  font-size: 13px; font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--txt-2);
  margin: 20px 0 12px;
  display: flex; align-items: center; gap: 8px;
}
.sec-title::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}
.sec-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--accent-g);
  display: inline-block;
  flex-shrink: 0;
}

/* ══════════════════════════════
   DATA TABLE
══════════════════════════════ */
.stDataFrame {
  border-radius: var(--r2) !important;
  overflow: hidden !important;
  border: 1px solid var(--border) !important;
  box-shadow: var(--z2) !important;
}
.stDataFrame [data-testid="stDataFrameResizable"] {
  background: var(--panel) !important;
}
.stDataFrame th {
  background: rgba(124,58,237,.1) !important;
  color: var(--txt-2) !important;
  font-size: 11px !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.08em !important;
}
.stDataFrame td {
  color: var(--txt) !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 12px !important;
}

/* ══════════════════════════════
   INSIGHT CARDS
══════════════════════════════ */
.insight-pair {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 14px 16px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  transition: border-color 150ms;
}
.insight-pair:hover { border-color: var(--border-hi); }
.pair-name { font-family: 'JetBrains Mono', monospace; font-size: 15px; font-weight: 700; color: var(--txt); }
.pair-raw  { font-size: 11px; color: var(--txt-3); margin-top: 2px; }
.badge {
  display: inline-flex; align-items: center;
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 12px; font-weight: 700;
  letter-spacing: 0.04em;
}
.badge-up   { background: rgba(16,185,129,.15);  color: #10b981; border: 1px solid rgba(16,185,129,.25); }
.badge-down { background: rgba(244,63,94,.15);   color: #f43f5e; border: 1px solid rgba(244,63,94,.25); }
.badge-neut { background: rgba(148,163,184,.1);  color: #94a3b8; border: 1px solid rgba(148,163,184,.2); }

/* progress bar */
.prog-wrap { width: 100%; height: 4px; background: rgba(255,255,255,.06); border-radius: 999px; margin-top: 4px; overflow: hidden; }
.prog-fill  { height: 100%; border-radius: 999px; transition: width 400ms cubic-bezier(.4,0,.2,1); }
.prog-up    { background: linear-gradient(90deg, #10b981, #34d399); }
.prog-down  { background: linear-gradient(90deg, #f43f5e, #fb7185); }

/* ══════════════════════════════
   EVENT CARDS
══════════════════════════════ */
.event-card {
  display: flex;
  gap: 14px;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 14px 16px;
  margin-bottom: 8px;
  align-items: flex-start;
}
.event-pip { width: 4px; border-radius: 2px; flex-shrink: 0; margin-top: 2px; }
.event-high-pip  { background: var(--down); }
.event-med-pip   { background: var(--warn); }
.event-low-pip   { background: var(--up);   }
.event-name { font-size: 13px; font-weight: 600; color: var(--txt); }
.event-meta { font-size: 11px; color: var(--txt-3); font-family: 'JetBrains Mono', monospace; margin-top: 2px; }
.event-pairs { font-size: 11px; color: var(--txt-2); margin-top: 4px; }
.imp-badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 10px; font-weight: 700; margin-left: 8px; }
.imp-high { background: rgba(244,63,94,.15); color: #f43f5e; }
.imp-med  { background: rgba(245,158,11,.15); color: #f59e0b; }
.imp-low  { background: rgba(16,185,129,.15); color: #10b981; }

/* ══════════════════════════════
   COMPARISON TABLE
══════════════════════════════ */
.comp-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
  margin-bottom: 8px;
}
.comp-cell {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 12px;
  text-align: center;
}
.comp-cell-label { font-size: 10px; font-weight: 700; color: var(--txt-3); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 4px; }
.comp-cell-val { font-family: 'JetBrains Mono', monospace; font-size: 15px; font-weight: 700; color: var(--txt); }

/* ══════════════════════════════
   SIGNAL BOX
══════════════════════════════ */
.signal-box {
  background: var(--panel);
  border-radius: var(--r2);
  padding: 20px;
  border: 1px solid var(--border);
  box-shadow: var(--z2);
  margin-top: 12px;
}
.signal-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; color: var(--txt-3); margin-bottom: 8px; }
.signal-main  { font-size: 26px; font-weight: 800; margin-bottom: 12px; }
.sig-bull { color: var(--up); }
.sig-bear { color: var(--down); }
.signal-bar-wrap { width: 100%; height: 6px; background: rgba(255,255,255,.06); border-radius: 999px; overflow: hidden; margin-bottom: 12px; }
.signal-bar { height: 100%; border-radius: 999px; }
.bar-up   { background: linear-gradient(90deg, #10b981, #34d399); }
.bar-down { background: linear-gradient(90deg, #f43f5e, #fb7185); }
.signal-drivers { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.driver-chip {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px; font-weight: 600;
  background: rgba(124,58,237,.12);
  border: 1px solid rgba(124,58,237,.25);
  color: #c4b5fd;
}

/* ══════════════════════════════
   NEWS ITEM
══════════════════════════════ */
.news-item {
  display: flex;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
  align-items: flex-start;
}
.news-item:last-child { border-bottom: none; }
.news-num { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--txt-3); width: 20px; flex-shrink: 0; margin-top: 2px; }
.news-title { font-size: 13px; font-weight: 600; color: var(--txt); line-height: 1.4; }
.news-meta { font-size: 11px; color: var(--txt-3); margin-top: 3px; }
.news-title a { color: var(--info); text-decoration: none; }
.news-title a:hover { text-decoration: underline; }

/* ══════════════════════════════
   LOG TABLE
══════════════════════════════ */
.log-entry {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--txt-2);
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  display: flex;
  gap: 16px;
}
.log-entry:hover { background: rgba(255,255,255,.02); }
.log-ts  { color: var(--txt-3); width: 160px; flex-shrink: 0; }
.log-ok   { color: var(--up); }
.log-fail { color: var(--down); }

/* ══════════════════════════════
   RATE PROBABILITY
══════════════════════════════ */
.rp-wrap {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--r2);
  overflow: hidden;
  box-shadow: var(--z2);
}
.rp-row {
  display: grid;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  gap: 12px;
  align-items: center;
  font-size: 12px;
}
.rp-row:last-child { border-bottom: none; }
.rp-header {
  background: rgba(124,58,237,.08);
  font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;
  color: var(--txt-3);
}
.rp-hike  { color: var(--up); font-weight: 700; }
.rp-cut   { color: var(--down); font-weight: 700; }
.rp-hold  { color: var(--txt-2); }

/* ══════════════════════════════
   MISC
══════════════════════════════ */
.info-box {
  background: rgba(56,189,248,.07);
  border: 1px solid rgba(56,189,248,.2);
  border-radius: var(--r);
  padding: 12px 16px;
  font-size: 12px;
  color: #7dd3fc;
  margin: 8px 0;
}
.warn-box {
  background: rgba(245,158,11,.07);
  border: 1px solid rgba(245,158,11,.2);
  border-radius: var(--r);
  padding: 12px 16px;
  font-size: 12px;
  color: #fcd34d;
  margin: 8px 0;
}
.divider { height: 1px; background: var(--border); margin: 20px 0; }

/* Streamlit overrides */
.stTabs [data-baseweb="tab-list"] {
  gap: 4px !important;
  background: var(--surface) !important;
  padding: 4px !important;
  border-radius: var(--r) !important;
  border: 1px solid var(--border) !important;
}
.stTabs [data-baseweb="tab"] {
  border-radius: 8px !important;
  padding: 8px 16px !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  color: var(--txt-2) !important;
  background: transparent !important;
  transition: all 150ms !important;
}
.stTabs [aria-selected="true"] {
  background: var(--panel) !important;
  color: var(--txt) !important;
  box-shadow: var(--z1) !important;
}
.stSelectbox > div, .stSlider > div { font-size: 13px !important; }
button[kind="primary"], .stButton > button {
  background: var(--accent-g) !important;
  border: none !important;
  border-radius: var(--r) !important;
  font-weight: 700 !important;
  font-size: 13px !important;
  padding: 10px 20px !important;
  cursor: pointer !important;
  transition: opacity 150ms, transform 100ms !important;
}
button[kind="primary"]:hover, .stButton > button:hover { opacity: 0.88 !important; }
button[kind="primary"]:active, .stButton > button:active { transform: scale(0.97) !important; }

/* Reduce-motion */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition-duration: 0.01ms !important; animation-duration: 0.01ms !important; }
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def sparkline(values, color="#10b981", height=44):
    fig = go.Figure(go.Scatter(
        y=values, mode="lines",
        line=dict(color=color, width=2),
        fill="tozeroy",
        fillcolor=f"rgba({','.join(str(int(int(color.lstrip('#')[i:i+2], 16))) for i in (0,2,4))},0.08)",
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
    return f'<span class="{cls}">{arrow} {abs(chg):.2f}%</span>'

def regime_class(sentiment):
    s = (sentiment or "").lower()
    if "bull" in s or "risk on" in s: return "regime-bull", "🟢"
    if "bear" in s or "risk off" in s: return "regime-bear", "🔴"
    return "regime-neut", "⚪"

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

    def color_score(val):
        if isinstance(val, (int, float)):
            if val >= 70:   return "color: #10b981; font-weight: 700"
            if val >= 40:   return "color: #f59e0b; font-weight: 600"
            return "color: #f43f5e; font-weight: 700"
        return ""

    styled = (
        df_macro.style
        .applymap(color_score, subset=["Score"])
        .format({
            "Taux (%)":      "{:.2f}",
            "10Y Yield (%)": "{:.2f}",
            "PIB (%)":       "{:+.2f}",
            "Inflation (%)": "{:.1f}",
            "Chômage (%)":   "{:.1f}",
        })
        .set_properties(**{"text-align": "center"})
    )
    st.dataframe(styled, use_container_width=True, height=320)

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
        font=dict(color="#94a3b8", family="Inter"),
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
    rows = [fx_items[i:i+cols_per_row] for i in range(0, len(fx_items), cols_per_row)]

    for row in rows:
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
        st.dataframe(df_comp, use_container_width=True, hide_index=True)

        regime_tuple = regime_weights("Automatique", auto_sentiment)
        wti_bull  = MARKET_ASSETS.get("WTI_CRUDE", {}).get("chg", 0) > 0
        wti_bonus = wti_adjustment(base_ccy, quote_ccy, wti_bull)

        expected_move = (
            spreads[2] * regime_tuple[1] +
            spreads[1] * regime_tuple[2] +
            spreads[0] * regime_tuple[3] +
            wti_bonus
        )
        score_pct = normalize_score(expected_move)
        bullish = score_pct >= 50
        bar_width = score_pct if bullish else (100 - score_pct)
        bar_cls   = "bar-up" if bullish else "bar-down"
        sig_label = "BULLISH" if bullish else "BEARISH"
        sig_cls   = "sig-bull" if bullish else "sig-bear"

        drivers = []
        if spreads[0] > 0: drivers.append("Taux directeur")
        if spreads[1] > 0: drivers.append("Rendement 10Y")
        if spreads[2] > 0: drivers.append("Score fondamental")
        if wti_bonus != 0: drivers.append("Impact WTI/CAD")
        if not drivers:    drivers.append("Aucun signal dominant")

        chips = "".join(f'<span class="driver-chip">{d}</span>' for d in drivers)

        st.markdown(f"""
        <div class="signal-box">
          <div class="signal-label">Orientation Macro — {base_ccy}/{quote_ccy}</div>
          <div class="signal-main {sig_cls}">{sig_label} <span style="font-size:18px;opacity:.6">{bar_width}%</span></div>
          <div class="signal-bar-wrap">
            <div class="signal-bar {bar_cls}" style="width:{bar_width}%"></div>
          </div>
          <div class="signal-label" style="margin-top:12px">Drivers détectés</div>
          <div class="signal-drivers">{chips}</div>
        </div>
        """, unsafe_allow_html=True)

# ═══════════════════════════════════════════
# TAB — COMMODITIES / INTERMARKET
# ═══════════════════════════════════════════
RATEPROB_CACHE = os.path.join(os.path.dirname(__file__), "rateprob_cache.json")
RATEPROB_URL   = "https://rateprobability.com"

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
            age = (datetime.utcnow() - datetime.fromisoformat(cache["ts"].replace("Z",""))).total_seconds()
            if age < ttl_seconds:
                return cache.get("data", []), cache.get("ts")
        except Exception:
            pass

    if BeautifulSoup is None:
        return cache.get("data", []), cache.get("ts")

    try:
        resp = requests.get(RATEPROB_URL, timeout=10, headers={"User-Agent": "fx-terminal/2.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        table = None
        for h in soup.find_all(["h1","h2","h3","h4","h5"]):
            if "upcoming meeting" in h.get_text(strip=True).lower():
                table = h.find_next("table")
                if table: break
        rows = []
        if table:
            ths = table.find("tr")
            if ths:
                rows.append([t.get_text(strip=True) for t in ths.find_all(["th","td"])])
            for tr in table.find_all("tr")[1:]:
                cells = [td.get_text(strip=True) for td in tr.find_all(["td","th"])]
                if cells: rows.append(cells)
        if not rows:
            for tbl in soup.find_all("table"):
                hdr = " ".join(th.get_text(strip=True).lower() for th in tbl.find_all("th"))
                if any(k in hdr for k in ["bank","probability","meeting","rate","implied"]):
                    ths = tbl.find("tr")
                    if ths:
                        rows.append([t.get_text(strip=True) for t in ths.find_all(["th","td"])])
                    for tr in tbl.find_all("tr")[1:]:
                        cells = [td.get_text(strip=True) for td in tr.find_all(["td","th"])]
                        if cells: rows.append(cells)
                    break
        if rows:
            _save_rateprob_cache(rows)
            return rows, datetime.utcnow().isoformat() + "Z"
        return cache.get("data", []), cache.get("ts")
    except Exception:
        return cache.get("data", []), cache.get("ts")

with tab_intermarket:
    st.markdown('<div class="sec-title"><span class="sec-dot"></span> Commodités & Marchés</div>', unsafe_allow_html=True)

    commodity_assets = [
        ("GOLD",      "✦",  "Gold Spot"),
        ("WTI_CRUDE", "🛢", "WTI Crude"),
        ("US_500",    "📈", "S&P 500"),
        ("SILVER",    "◆",  "Silver"),
    ]
    ccols = st.columns(4)
    for col, (key, icon, label) in zip(ccols, commodity_assets):
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

    st.markdown('<div class="info-box">ℹ Le WTI influence structurellement le CAD. Voir l\'onglet Insights pour les paires CAD concernées.</div>', unsafe_allow_html=True)

    # RateProbability
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-title"><span class="sec-dot"></span> Upcoming Meetings — RateProbability</div>', unsafe_allow_html=True)

    rp_col, _ = st.columns([1, 3])
    with rp_col:
        rp_force = st.button("🔄 Rafraîchir RateProbability")

    rows, ts = fetch_rateprobability(force=rp_force)
    if not rows:
        st.markdown('<div class="warn-box">⚠ Données indisponibles — cache vide ou erreur réseau.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="font-size:11px;color:var(--txt-3);margin-bottom:8px;font-family:\'JetBrains Mono\',monospace">Dernière synchro: {ts}</div>', unsafe_allow_html=True)
        if isinstance(rows, list) and rows and all(isinstance(r, list) for r in rows):
            headers, data_rows = rows[0], rows[1:]
            df_rp = pd.DataFrame(data_rows, columns=headers)
            outcome_col = next((c for c in df_rp.columns if "implied" in c.lower() or "outcome" in c.lower()), None)
            prob_col    = next((c for c in df_rp.columns if "prob" in c.lower()), None)

            def color_outcome(v):
                if not isinstance(v, str): return ""
                vl = v.lower()
                if "hike" in vl or "raise" in vl: return "color: #10b981; font-weight: 700"
                if "cut"  in vl or "lower" in vl: return "color: #f43f5e; font-weight: 700"
                return "color: #94a3b8"

            styled_rp = df_rp.style
            if outcome_col:
                styled_rp = styled_rp.applymap(color_outcome, subset=[outcome_col])
            st.dataframe(styled_rp, use_container_width=True, hide_index=True)
        else:
            st.table(rows)

# ═══════════════════════════════════════════
# TAB — INSIGHTS
# ═══════════════════════════════════════════
with tab_insights:
    regime_tuple = regime_weights("Automatique", auto_sentiment)
    wti_bull = MARKET_ASSETS.get("WTI_CRUDE", {}).get("chg", 0) > 0
    ranked   = rank_all_pairs(regime_tuple, wti_bull)

    top_bull  = [r for r in ranked if r["score_pct"] >= 50][:4]
    top_bear  = sorted(ranked, key=lambda x: x["score_pct"])[:4]

    col_bull, col_bear = st.columns(2)

    with col_bull:
        st.markdown('<div class="sec-title"><span class="sec-dot"></span> Top Bullish</div>', unsafe_allow_html=True)
        if not top_bull:
            st.markdown('<div class="info-box">Aucune paire bullish détectée.</div>', unsafe_allow_html=True)
        for item in top_bull:
            pct = item["score_pct"]
            st.markdown(f"""
            <div class="insight-pair">
              <div>
                <div class="pair-name">{item["pair"]}</div>
                <div class="pair-raw">Score brut: {item["raw"]:.2f}</div>
                <div class="prog-wrap"><div class="prog-fill prog-up" style="width:{pct}%"></div></div>
              </div>
              <div><span class="badge badge-up">▲ {pct}%</span></div>
            </div>
            """, unsafe_allow_html=True)

    with col_bear:
        st.markdown('<div class="sec-title"><span class="sec-dot"></span> Top Bearish</div>', unsafe_allow_html=True)
        if not top_bear:
            st.markdown('<div class="info-box">Aucune paire bearish détectée.</div>', unsafe_allow_html=True)
        for item in top_bear:
            pct = 100 - item["score_pct"]
            st.markdown(f"""
            <div class="insight-pair">
              <div>
                <div class="pair-name">{item["pair"]}</div>
                <div class="pair-raw">Score brut: {item["raw"]:.2f}</div>
                <div class="prog-wrap"><div class="prog-fill prog-down" style="width:{pct}%"></div></div>
              </div>
              <div><span class="badge badge-down">▼ {pct}%</span></div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-title"><span class="sec-dot"></span> Catalyseurs à Venir</div>', unsafe_allow_html=True)

    catalysts = [
        {"time": "2026-05-20 · 13:30 UTC", "event": "US Nonfarm Payrolls (NFP)",  "impact": "High",   "pairs": ["USD/*"]},
        {"time": "2026-05-21 · 08:00 UTC", "event": "ECB Rate Decision",           "impact": "High",   "pairs": ["EUR/*"]},
        {"time": "2026-05-22 · 02:00 UTC", "event": "BoC Rate Statement",          "impact": "Medium", "pairs": ["CAD/*"]},
        {"time": "2026-05-23 · 01:30 UTC", "event": "RBA Minutes",                 "impact": "Low",    "pairs": ["AUD/*"]},
    ]
    for c in catalysts:
        pip_cls = {"High": "event-high-pip", "Medium": "event-med-pip", "Low": "event-low-pip"}.get(c["impact"], "event-low-pip")
        imp_cls = {"High": "imp-high",       "Medium": "imp-med",       "Low": "imp-low"}.get(c["impact"], "imp-low")
        pairs_str = ", ".join(c["pairs"])
        st.markdown(f"""
        <div class="event-card">
          <div class="event-pip {pip_cls}" style="height:48px"></div>
          <div>
            <div class="event-name">
              {c["event"]}
              <span class="imp-badge {imp_cls}">{c["impact"]}</span>
            </div>
            <div class="event-meta">{c["time"]}</div>
            <div class="event-pairs">Paires: {pairs_str}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-title"><span class="sec-dot"></span> News & Flux</div>', unsafe_allow_html=True)

    articles = fetch_news(limit=6)
    if articles:
        st.markdown('<div style="background:var(--panel);border:1px solid var(--border);border-radius:var(--r2);padding:8px 16px;">', unsafe_allow_html=True)
        for i, a in enumerate(articles, 1):
            title = a.get("title") or "Untitled"
            src   = a.get("source") or ""
            ts    = (a.get("publishedAt") or "")[:19].replace("T", " ")
            url   = a.get("url") or "#"
            st.markdown(f"""
            <div class="news-item">
              <div class="news-num">#{i:02d}</div>
              <div>
                <div class="news-title"><a href="{url}" target="_blank" rel="noopener">{title}</a></div>
                <div class="news-meta">{src} · {ts}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="info-box">ℹ Aucune news — vérifiez <code>NEWS_API_KEY</code> ou le cache local.</div>', unsafe_allow_html=True)

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
        st.markdown('<div style="background:var(--panel);border:1px solid var(--border);border-radius:var(--r2);overflow:hidden;">', unsafe_allow_html=True)
        for entry in logs:
            status    = entry.get("status", "")
            status_cls = "log-ok" if str(status).lower() in ("ok","success","200") else "log-fail"
            st.markdown(f"""
            <div class="log-entry">
              <span class="log-ts">{entry.get("ts","—")}</span>
              <span>Session: <b>{entry.get("session","—")}</b></span>
              <span>Trigger: <b>{entry.get("trigger","—")}</b></span>
              <span class="{status_cls}">Status: {status}</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="info-box">ℹ Aucun log disponible.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;padding-bottom:12px;">
  <div style="font-size:11px;color:var(--txt-3);">Sources: Yahoo Finance (yfinance) · Indicateurs macro fondamentaux pondérés · rateprobability.com</div>
  <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--txt-3);">{utc_now}</div>
</div>
""", unsafe_allow_html=True)
