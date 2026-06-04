import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# L'import global du scraper est proscrit pour la stabilité du déploiement
from data import FX_RATES

st.set_page_config(page_title="LNE - WATCH TOWER", page_icon="🔭", layout="wide")

# --- INJECTION CSS TERMINAL INSTITUTIONNEL ---
st.markdown("""
<style>
    .stApp { background-color: #050505 !important; color: #e2e8f0 !important; }
    #MainMenu, header, footer { visibility: hidden !important; height: 0 !important; }
    div.block-container { padding: 1rem 2rem !important; max-width: 100% !important; }
    
    .ticker-container {
        display: flex; gap: 25px; background-color: #0a0a0c; border-bottom: 1px solid #1e1e24;
        padding: 12px 20px; font-family: 'Courier New', monospace; font-size: 12px; margin-bottom: 20px; overflow-x: auto;
    }
    .metric-card {
        background-color: #0f0f13; border: 1px solid #1c1c21; border-left: 3px solid #3b82f6;
        border-radius: 4px; padding: 15px; margin-bottom: 15px;
    }
    .metric-title { color: #8b8d98; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { font-size: 20px; font-weight: bold; margin-top: 5px; }
    
    .bias-hawkish { color: #f97316 !important; font-weight: bold; }
    .bias-dovish { color: #3b82f6 !important; font-weight: bold; }
    
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #0f0f13; border-radius: 4px 4px 0 0; 
        padding: 10px 20px; color: #8b8d98; border: 1px solid #1c1c21; border-bottom: none;
    }
    .stTabs [aria-selected="true"] { background-color: #1c1c21; color: #fff; border-top: 2px solid #3b82f6; }
</style>
""", unsafe_allow_html=True)

# ─── MOTEUR DE CACHE SÉCURISÉ ───
cache = {} 
try:
    with open("news_cache.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, dict):
            cache = data
except Exception:
    cache = {"metadata": {}, "macro_data": {}, "scores": {}, "news_feed": []}

if not cache.get("macro_data"):
    try:
        from scraper import run_global_scraper
        run_global_scraper()
        with open("news_cache.json", "r", encoding="utf-8") as f:
            cache = json.load(f)
    except Exception as e:
        st.error(f"Erreur d'initialisation : {e}")

meta, macro_data, scores, news_feed = cache.get("metadata", {}), cache.get("macro_data", {}), cache.get("scores", {}), cache.get("news_feed", [])

# --- HEADER & RAFRAÎCHISSEMENT ---
col_logo, col_btn = st.columns([5, 1])
with col_logo:
    st.markdown("<h1 style='margin:0; font-size: 28px; letter-spacing: 2px;'>🔭 LNE WATCH TOWER | <span style='color:#3b82f6; font-size: 18px;'>G10 MACRO TERMINAL</span></h1>", unsafe_allow_html=True)
with col_btn:
    if st.button("⚡ FORCE SYNC", use_container_width=True):
        with st.spinner("Extraction..."):
            from scraper import run_global_scraper
            run_global_scraper()
        st.rerun()

# ─── BARRE DE DOCK SUPÉRIEUR (TICKER) ───
ticker_html = '<div class="ticker-container">'
for ccy, info in macro_data.items():
    bias = info.get("bias", "Neutral")
    bias_style = "bias-hawkish" if bias in ["Hawkish", "Tightening", "Holding Restrictive"] else "bias-dovish"
    ticker_html += f"<div><b>{ccy}</b> ({info.get('cb', '')}): {info.get('rate', 0):.2f}% | 10Y: {info.get('yield_10y', 0.0):.2f}% <span class='{bias_style}'>[{bias.upper()}]</span></div> • "
ticker_html += f"<div style='margin-left: auto; color:#71717a;'>STATUS: LIVE | SYNC: {meta.get('updated_at', 'N/A')}</div></div>"
st.markdown(ticker_html, unsafe_allow_html=True)

# ─── ONGLETS ───
tab_macro, tab_cb, tab_flows, tab_sentiment, tab_tech = st.tabs(["📊 MACRO CONVERGENCE", "🏛️ CENTRAL BANKS", "🐋 INSTITUTIONAL FLOWS", "📰 SENTIMENT", "📈 HEATMAP"])

with tab_macro:
    st.markdown("### Modèle Quantitatif G10")
    sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='metric-card'><div class='metric-title'>Risque Géo</div><div class='metric-value' style='color:#ef4444;'>{meta.get('geo_risk_level', 'MODÉRÉ')}</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'><div class='metric-title'>Tonalité BC</div><div class='metric-value' style='color:#3b82f6;'>{meta.get('speech_tone', 'MIXED')}</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card'><div class='metric-title'>Devise Forte</div><div class='metric-value' style='color:#10b981;'>{sorted_scores[0][0] if sorted_scores else 'N/A'}</div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='metric-card'><div class='metric-title'>Devise Faible</div><div class='metric-value' style='color:#ef4444;'>{sorted_scores[-1][0] if sorted_scores else 'N/A'}</div></div>", unsafe_allow_html=True)

    rows = [{"Asset": ccy, "Target Rate": f"{info.get('rate', 0):.2f}%", "10Y Yield": f"{info.get('yield_10y', 0):.2f}%", "ALGO SCORE": scores.get(ccy, 0)} for ccy, info in macro_data.items()]
    st.dataframe(pd.DataFrame(rows).sort_values(by="ALGO SCORE", ascending=False), use_container_width=True, hide_index=True)

with tab_tech:
    st.markdown("### G10 Relative Strength Heatmap")
    df_fx = pd.DataFrame([{"Pair": k, "Change": v["chg"]} for k, v in FX_RATES.items()])
    if not df_fx.empty:
        fig = px.treemap(df_fx, path=['Pair'], values=df_fx["Change"].abs(), color='Change', color_continuous_scale=["#ef4444", "#1e1e24", "#10b981"])
        st.plotly_chart(fig, use_container_width=True)
