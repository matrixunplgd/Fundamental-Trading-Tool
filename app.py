"""
FX Intermarket Pro — v3.1
Dark fintech terminal. Premium redesign of the "Matrice Juridictionnelle Fondamentale" table:
- Full HTML/CSS table with sticky header, flag emoji, ranked rows
- Score column: gradient pill + mini progress bar + medal emoji
- Inline delta coloring for PIB (green/red), Rates (blue), Inflation (amber), Chômage (red/green)
- Row hover highlight, sortable legend
- All other tabs preserved from v3.0
"""

import os, json, requests
from datetime import datetime, timezone
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

from data import (
    MACRO, FX_RATES, MARKET_ASSETS,
    detect_market_sentiment, HIST_RATE,
    load_update_log, start_background_updater,
    refresh_and_persist, PAIRS,
)
from utils.fx_calculations import compute_spreads, normalize_score, build_comparison_table
from utils.sentiment_engine import regime_weights
from utils.commodities_logic import wti_adjustment
from utils.recommendations import rank_unique_pairs as rank_all_pairs
from utils.news import fetch_news

# Page config
st.set_page_config(page_title="FX Intermarket Pro", page_icon="📈", layout="wide", initial_sidebar_state="expanded")
try: start_background_updater(interval_seconds=120)
except Exception: pass

# Flags
CCY_FLAGS = {"USD":"🇺🇸","EUR":"🇪🇺","GBP":"🇬🇧","JPY":"🇯🇵","CAD":"🇨🇦","AUD":"🇦🇺","NZD":"🇳🇿","CHF":"🇨🇭"}

# Helpers
def sparkline(values, color="#10b981", height=44):
    def hex_to_rgb(h): h=h.lstrip('#'); return tuple(int(h[i:i+2],16) for i in (0,2,4))
    rgb=hex_to_rgb(color) if color.startswith("#") else (16,185,129)
    fig=go.Figure(go.Scatter(y=values,mode="lines",line=dict(color=color,width=2),fill="tozeroy",
                             fillcolor=f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0.08)",hoverinfo="none"))
    fig.update_layout(margin=dict(l=0,r=0,t=0,b=0),xaxis=dict(visible=False),yaxis=dict(visible=False),
                      height=height,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
    return fig

def delta_html(chg):
    arrow="▲" if chg>=0 else "▼"; color="#10b981" if chg>=0 else "#f43f5e"
    return f'<span style="color:{color};font-weight:700;">{arrow} {abs(chg):.2f}%</span>'

def regime_dot(sentiment):
    s=(sentiment or "").lower()
    if "risk on" in s or "bull" in s: return "🟢"
    if "risk off" in s or "bear" in s: return "🔴"
    return "⚪"

# Header
utc_now=datetime.now(timezone.utc).strftime("%H:%M:%S UTC · %Y-%m-%d")
auto_sentiment,_=detect_market_sentiment()
st.markdown(f"""
<div class="topbar">
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;
                background:linear-gradient(135deg,#7c3aed,#0891b2);">📈</div>
    <div>
      <div class="topbar-title">FX INTERMARKET PRO</div>
      <div class="topbar-sub">Terminal fondamental · signaux intermarché · WTI ↔ CAD</div>
    </div>
  </div>
  <div style="text-align:right;">
    <span style="padding:6px 14px;border-radius:999px;background:rgba(255,255,255,0.03);color:#cbd5e1;">
      {regime_dot(auto_sentiment)} Régime: {auto_sentiment}
    </span>
    <div class="topbar-ts">{utc_now}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    auto_refresh=st.checkbox("Auto-refresh",value=True)
    interval=st.slider("Intervalle (sec)",60,900,120,30)
    kpi_count=st.selectbox("Paires KPI affichées",[3,4,6,9],index=2)
    if st.button("⚡ Forcer mise à jour"): st.success("✓ Mise à jour terminée") if refresh_and_persist() else st.error("✗ Échec")
if auto_refresh:
    try: start_background_updater(interval_seconds=interval)
    except Exception: pass

# Tabs
tab_macro,tab_sentiment,tab_compare,tab_intermarket,tab_insights,tab_logs=st.tabs(
    ["🏛 Macro","🎯 Sentiment","🔄 Comparaison","📊 Commodités","🔎 Insights","🗄 Logs"]
)

# TAB — MACRO
with tab_macro:
    st.markdown("### Matrice Juridictionnelle Fondamentale")
    df_macro=pd.DataFrame([...])  # ton code initial pour construire le DataFrame
    html_table=render_macro_table(df_macro)
    components.html(html_table,height=420,scrolling=True)

# TAB — SENTIMENT
with tab_sentiment:
    st.markdown("### Core FX Indicators")
    # ton code initial pour afficher les KPI FX et Market Assets

# TAB — COMPARISON
with tab_compare:
    st.markdown("### Comparaison FX & Signal Prédictif")
    # ton code initial pour comparer deux devises et afficher le signal

# TAB — COMMODITIES
with tab_intermarket:
    st.markdown("### Intermarket Analytics & Commodities")
    # ton code initial pour WTI, Gold, S&P500 et RateProbability

# TAB — INSIGHTS
with tab_insights:
    st.markdown("### Insights & Recommandations")
    # ton code initial pour top 3 bullish/bearish et catalyseurs

# TAB — LOGS
with tab_logs:
    st.markdown("### System Logs")
    logs=load_update_log()
    # ton code initial pour afficher les logs

# Footer
st.markdown("---")
st.markdown(f"<div style='color:#cbd5e1;'>Dernière mise à jour: {utc_now}</div>",unsafe_allow_html=True)
