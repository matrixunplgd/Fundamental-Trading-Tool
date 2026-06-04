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
cache = {}
try:
    with open("news_cache.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, dict):
            cache = data
except Exception as e:
    st.sidebar.error("Cache indisponible ou corrompu.")

# Extraction sécurisée
meta = cache.get("metadata", {})
macro_data = cache.get("macro_data", {})
scores = cache.get("scores", {})
probs = cache.get("wirp_data", {})
cot_data = cache.get("cot_data", {})
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
if macro_data:
    ticker_html = '<div class="ticker-container">'
    for ccy, info in macro_data.items():
        bias = info.get("bias", "Neutral")
        style = "bias-hawkish" if bias in ["Hawkish", "Tightening"] else "bias-dovish"
        ticker_html += f"<div><b>{ccy}</b>: {info.get('rate', 0):.2f}% | 10Y: {info.get('yield_10y', 0):.2f}% <span class='{style}'>[{bias.upper()}]</span></div> • "
    ticker_html += "</div>"
    st.markdown(ticker_html, unsafe_allow_html=True)

# --- ONGLETS ---
tab_macro, tab_cb, tab_flows, tab_sentiment, tab_tech = st.tabs(["📊 MACRO", "🏛️ WIRP", "🐋 FLOWS", "📰 SENTIMENT", "📈 HEATMAP"])

with tab_macro:
    st.markdown("### Modèle Quantitatif G10")
    if macro_data:
        rows = []
        for ccy, info in macro_data.items():
            rows.append({
                "Asset": ccy,
                "Target Rate": f"{info.get('rate', 0.0):.2f}%",
                "10Y Yield": f"{info.get('yield_10y', 0.0):.2f}%",
                "Core CPI": f"{info.get('cpi', 0.0):.1f}%",
                "PMI": f"{info.get('pmi', 50.0):.1f}",
                "Unemployment": f"{info.get('unem', 0.0):.1f}%",
                "ALGO SCORE": float(scores.get(ccy, 0.0))
            })
        df_macro = pd.DataFrame(rows)
        # Tri sécurisé
        df_macro = df_macro.sort_values(by="ALGO SCORE", ascending=False)
        st.dataframe(df_macro, use_container_width=True, hide_index=True)
    else:
        st.write("Données macro non disponibles.")

with tab_cb:
    if not isinstance(probs, dict) or not probs:
        st.warning("Données WIRP non disponibles.")
    else:
        selected = st.selectbox("Sélectionner Node :", list(probs.keys()))
        data = probs.get(selected, {})
        st.metric("Taux Actuel", f"{data.get('current_rate', 0)}%")
        if data.get("table_data"):
            st.write(pd.DataFrame(data["table_data"]))

with tab_flows:
    st.markdown("### 🐋 Positionnement Institutionnel")
    st.write(cot_data if cot_data else "Données de flux non disponibles.")

with tab_sentiment:
    st.markdown("### 📰 FinancialJuice")
    if news_feed:
        for news in news_feed[:5]:
            st.markdown(f"**{news.get('title', 'Sans titre')}**")
    else:
        st.write("Aucune actualité disponible.")

with tab_tech:
    st.markdown("### G10 Heatmap")
    df = pd.DataFrame([{"Pair": k, "Change": v.get("chg", 0)} for k, v in FX_RATES.items()])
    if not df.empty:
        fig = px.treemap(df, path=['Pair'], values=df["Change"].abs(), color='Change', color_continuous_scale=["red", "black", "green"])
        st.plotly_chart(fig, use_container_width=True)
