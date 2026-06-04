import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from data import FX_RATES

st.set_page_config(page_title="LNE - WATCH TOWER", page_icon="🔭", layout="wide")

# --- CSS TERMINAL ---
st.markdown("""
<style>
    .stApp { background-color: #050505 !important; color: #e2e8f0 !important; }
    .ticker-container { display: flex; gap: 20px; background-color: #0a0a0c; border-bottom: 1px solid #1e1e24; padding: 10px 20px; font-family: 'Courier New', monospace; font-size: 11px; margin-bottom: 20px; }
    .metric-card { background-color: #0f0f13; border: 1px solid #1c1c21; border-left: 3px solid #3b82f6; padding: 15px; border-radius: 4px; }
    .bias-hawkish { color: #f97316 !important; font-weight: bold; }
    .bias-dovish { color: #3b82f6 !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ─── MOTEUR DE CHARGEMENT ROBUSTE ───
try:
    with open("news_cache.json", "r", encoding="utf-8") as f:
        cache = json.load(f)
except:
    cache = {}

# Extraction avec clés synchronisées avec le scraper
meta = cache.get("metadata", {})
macro_data = cache.get("macro_data", {})
scores = cache.get("scores", {})
probs = cache.get("wirp_data", {})   # Corrigé : pointe vers wirp_data
cot_data = cache.get("cot_data", {}) # Données de flux
news_feed = cache.get("news_feed", [])

# --- HEADER & SYNC ---
col_logo, col_btn = st.columns([5, 1])
with col_logo: st.markdown("# 🔭 LNE WATCH TOWER | <span style='color:#3b82f6; font-size: 18px;'>G10 MACRO TERMINAL</span>", unsafe_allow_html=True)
with col_btn:
    if st.button("⚡ FORCE SYNC"):
        from scraper import run_global_scraper
        run_global_scraper()
        st.rerun()

# --- TICKER ---
ticker_html = '<div class="ticker-container">'
for ccy, info in macro_data.items():
    bias = info.get("bias", "Neutral")
    style = "bias-hawkish" if bias in ["Hawkish", "Tightening"] else "bias-dovish"
    ticker_html += f"<div><b>{ccy}</b>: {info.get('rate', 0):.2f}% | 10Y: {info.get('yield_10y', 0):.2f}% <span class='{style}'>[{bias.upper()}]</span></div> • "
ticker_html += f"</div>"
st.markdown(ticker_html, unsafe_allow_html=True)

# --- ONGLETS ---
tab_macro, tab_cb, tab_flows, tab_sentiment, tab_tech = st.tabs(["📊 MACRO", "🏛️ WIRP", "🐋 FLOWS", "📰 SENTIMENT", "📈 HEATMAP"])

with tab_macro:
    st.markdown("### Modèle Quantitatif")
    rows = [{"Asset": c, **v, "Score": scores.get(c, 0)} for c, v in macro_data.items()]
    st.dataframe(pd.DataFrame(rows).sort_values("Score", ascending=False), use_container_width=True)

with tab_cb:
    if not probs:
        st.warning("Données WIRP en attente de synchronisation.")
    else:
        selected = st.selectbox("Sélectionner Node :", list(probs.keys()))
        data = probs.get(selected, {})
        st.metric("Taux Actuel", f"{data.get('current_rate')}%")
        st.write(pd.DataFrame(data.get("table_data", [])))

with tab_flows:
    st.markdown("### 🐋 Positionnement Institutionnel")
    if not cot_data:
        st.info("Données de flux non disponibles.")
    else:
        st.json(cot_data)

with tab_sentiment:
    st.markdown("### 📰 FinancialJuice")
    for news in news_feed[:5]:
        st.markdown(f"**{news.get('title')}**")

with tab_tech:
    st.markdown("### G10 Heatmap")
    df = pd.DataFrame([{"Pair": k, "Change": v["chg"]} for k, v in FX_RATES.items()])
    if not df.empty:
        fig = px.treemap(df, path=['Pair'], values=df["Change"].abs(), color='Change', color_continuous_scale=["red", "black", "green"])
        st.plotly_chart(fig, use_container_width=True)
