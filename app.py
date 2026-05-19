# app.py
"""
FX Intermarket Pro — v3.1
Dark fintech terminal. Premium redesign + sentiment-aware comparison.
- Macro table premium HTML
- Comparaison: mouvement pondéré selon Risk-On / Risk-Off
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

# TAB — COMPARISON
with tab_compare:
    st.markdown('<div style="font-weight:700;color:#cbd5e1;margin-bottom:8px;">Comparaison FX & Signal Prédictif</div>',unsafe_allow_html=True)
    ccy_list=list(MACRO.keys())
    c1,c2=st.columns(2)
    with c1: base_ccy=st.selectbox("Devise Long (Base)",ccy_list,index=min(6,len(ccy_list)-1))
    with c2: quote_ccy=st.selectbox("Devise Short (Contrepartie)",ccy_list,index=0)

    if base_ccy==quote_ccy:
        st.markdown('<div style="background:#2b2f36;padding:10px;border-radius:8px;color:#f59e0b;">⚠ Sélectionnez deux devises distinctes.</div>',unsafe_allow_html=True)
    else:
        b_data,q_data=MACRO.get(base_ccy,{}),MACRO.get(quote_ccy,{})
        spreads=compute_spreads(b_data,q_data)
        df_comp=build_comparison_table(base_ccy,quote_ccy,b_data,q_data,spreads)
        st.dataframe(df_comp,use_container_width=True)

        # 🔄 Mise à jour du sentiment en direct
        auto_sentiment,_=detect_market_sentiment()
        regime_tuple=regime_weights("Automatique",auto_sentiment)
        wti_bull=MARKET_ASSETS.get("WTI_CRUDE",{}).get("chg",0)>0
        wti_bonus=wti_adjustment(base_ccy,quote_ccy,wti_bull)

        # Pondération selon sentiment global
        sentiment=auto_sentiment.lower()
        if "risk on" in sentiment or "bull" in sentiment: sentiment_factor=1.2
        elif "risk off" in sentiment or "bear" in sentiment: sentiment_factor=0.8
        else: sentiment_factor=1.0

        expected_move=((spreads[2]*regime_tuple[1])+(spreads[1]*regime_tuple[2])+(spreads[0]*regime_tuple[3])+wti_bonus)*sentiment_factor
        score_pct=normalize_score(expected_move)

        # Signal box
        st.markdown('<div style="background:var(--panel);padding:16px;border-radius:12px;border:1px solid var(--border);">',unsafe_allow_html=True)
        if score_pct>=50:
            st.markdown(f'<div style="font-size:20px;font-weight:800;color:#10b981;">BULLISH — {score_pct}%</div>',unsafe_allow_html=True)
            st.markdown(f'<div style="height:10px;background:rgba(255,255,255,0.03);border-radius:999px;margin-top:8px;"><div style="width:{score_pct}%;height:100%;background:linear-gradient(90deg,#10b981,#34d399);border-radius:999px;"></div></div>',unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="font-size:20px;font-weight:800;color:#f43f5e;">BEARISH — {100-score_pct}%</div>',unsafe_allow_html=True)
            st.markdown(f'<div style="height:10px;background:rgba(255,255,255,0.03);border-radius:999px;margin-top:8px;"><div style="width:{100-score_pct}%;height:100%;background:linear-gradient(90deg,#f43f5e,#fb7185);border-radius:999px;"></div></div>',unsafe_allow_html=True)

        # ➕ Mention explicite du sentiment
        st.markdown(f"<div style='color:#cbd5e1;font-size:12px;margin-top:6px;'>Mouvement pondéré selon le sentiment actuel du marché : {auto_sentiment}</div>",
