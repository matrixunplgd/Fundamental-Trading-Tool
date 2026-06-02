# app.py
import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go

# Import de ton moteur de scraping pour l'option de rafraîchissement manuel
from scraper import run_global_scraper
from data import FX_RATES

st.set_page_config(page_title="LNE - WATCH TOWER", layout="wide")

# --- INJECTION CSS DARK THEME HIGH-TECH ---
st.markdown("""
<style>
    .stApp { background-color: #09090b !important; color: #f4f4f5 !important; }
    #MainMenu, header, footer { visibility: hidden !important; height: 0 !important; }
    div.block-container { padding: 0rem 2rem !important; max-width: 100% !important; }
    
    .ticker-container {
        display: flex; gap: 20px; background-color: #0c0c0e; border-bottom: 1px solid #1e1e24;
        padding: 12px 20px; font-family: monospace; font-size: 11px; margin-bottom: 25px; overflow-x: auto;
    }
    .terminal-card {
        background-color: #121214 !important; border: 1px solid #1c1c1f !important;
        border-radius: 4px; padding: 24px; margin-bottom: 20px;
    }
    .bias-hawkish { color: #f97316 !important; font-weight: bold; }
    .bias-dovish { color: #3b82f6 !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- BOUTON DE RAFRAÎCHISSEMENT INTERACTIF (EN 1 CLIC) ---
col_title, col_btn = st.columns([4, 1])
with col_title:
    st.markdown("<h2 style='margin-top:10px;'>🔭 LNE WATCH TOWER CENTRAL</h2>", unsafe_allow_html=True)
with col_btn:
    st.markdown("<div style='padding-top:15px;'></div>", unsafe_allow_html=True)
    if st.button("🔄 Force Market Refresh", use_container_width=True):
        with st.spinner("Scraping global en cours..."):
            run_global_scraper()
        st.success("Données actualisées !")
        st.rerun()

# Chargement du cache local
try:
    with open("news_cache.json", "r") as f:
        cache = json.load(f)
except Exception:
    run_global_scraper()
    with open("news_cache.json", "r") as f:
        cache = json.load(f)

meta = cache["metadata"]
macro_data = cache["macro_data"]

# ─── 1. BARRE DE DOCK SUPÉRIEUR (MONITORING EXHAUSTIF DU G10) ───
ticker_html = '<div class="ticker-container">'
for ccy, info in macro_data.items():
    bias_style = "bias-hawkish" if info["bias"] in ["Hawkish", "Tightening", "Holding Restrictive"] else "bias-dovish"
    ticker_html += f"<div>{ccy} ({info['cb']}): <b>{info['rate']:.2f}%</b> <span class='{bias_style}'>{info['bias'].upper()}</span></div> • "
ticker_html += f"<div style='margin-left: auto; color:#71717a;'>SYNC: {meta['updated_at']}</div></div>"
st.markdown(ticker_html, unsafe_allow_html=True)

# ─── 2. SIDEBAR AVEC TOUTES LES PAIRES MAJEURES SANS EXCEPTION ───
with st.sidebar:
    st.markdown("<h4 style='color:#71717a; font-size:11px;'>MONITORED CURRENCIES</h4>", unsafe_allow_html=True)
    for pair, data in FX_RATES.items():
        color = "#10b981" if data["chg"] >= 0 else "#ef4444"
        st.markdown(f"**{pair}** : `{data['rate']:.4f}` <span style='color:{color}; font-size:11px;'>({data['chg']:+.2f}%)</span>", unsafe_allow_html=True)

# ─── 3. PANNEAU DE CONFLUENCES & MATRICE DE POLITIQUES MONÉTAIRES ───
tab_matrix, tab_ois = st.tabs(["📊 SCORING MATRIX", "🔮 OIS RATE PROBABILITIES"])

with tab_matrix:
    st.markdown("### G10 Macro Convergence Model")
    
    rows = []
    for ccy, info in macro_data.items():
        rows.append({
            "Currency": ccy,
            "Central Bank": info["cb"],
            "Policy Rate": f"{info['rate']:.2f}%",
            "Core Bias": info["bias"],
            "CPI (Inflation)": f"{info['cpi']:.1f}%",
            "Unemployment": f"{info['unem']:.1f}%",
            "Algorithmic Score": cache["scores"].get(ccy, 0)
        })
    
    df = pd.DataFrame(rows).sort_values(by="Algorithmic Score", ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True)

with tab_ois:
    st.markdown("### RateProbability.com Central Bank Implied Target Paths")
    selected_ccy = st.selectbox("Select Currency Asset Node :", list(macro_data.keys()))
    
    ccy_p = cache["probs"].get(selected_ccy, {"prob_hike": 50.0, "prob_cut": 50.0})
    
    # Rendu du graphique en secteurs pour les probabilités OIS
    fig = go.Figure(data=[go.Pie(
        labels=['Implied Cut / Hold', 'Implied Hike / Tightening'],
        values=[ccy_p.get("prob_cut", 50.0), ccy_p.get("prob_hike", 50.0)],
        hole=.4,
        marker_colors=["#3b82f6", "#f97316"]
    )])
    fig.update_layout(template="plotly_dark", paper_bgcolor="#121214", height=300, margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)
