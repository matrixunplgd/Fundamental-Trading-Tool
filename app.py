# app.py
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
    
    /* Customisation des onglets Streamlit */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #0f0f13; border-radius: 4px 4px 0 0; 
        padding: 10px 20px; color: #8b8d98; border: 1px solid #1c1c21; border-bottom: none;
    }
    .stTabs [aria-selected="true"] { background-color: #1c1c21; color: #fff; border-top: 2px solid #3b82f6; }
</style>
""", unsafe_allow_html=True)

# --- HEADER & BOUTON DE RAFRAÎCHISSEMENT ---
col_logo, col_btn = st.columns([5, 1])
with col_logo:
    st.markdown("<h1 style='margin:0; font-size: 28px; letter-spacing: 2px;'>🔭 LNE WATCH TOWER | <span style='color:#3b82f6; font-size: 18px;'>G10 MACRO TERMINAL</span></h1>", unsafe_allow_html=True)
with col_btn:
    if st.button("⚡ FORCE SYNC", use_container_width=True):
        with st.spinner("Extraction des données institutionnelles..."):
            from scraper import run_global_scraper
            run_global_scraper()
        st.rerun()

# ─── MOTEUR DE CACHE SÉCURISÉ ───
cache = None
try:
    with open("news_cache.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, dict) and "macro_data" in data: cache = data
except Exception:
    pass

if not cache:
    with st.spinner("Génération du modèle macro initial..."):
        from scraper import run_global_scraper
        run_global_scraper()
        with open("news_cache.json", "r", encoding="utf-8") as f:
            cache = json.load(f)

meta = cache.get("metadata", {})
macro_data = cache.get("macro_data", {})
scores = cache.get("scores", {})
probs = cache.get("probs", {})
news_feed = cache.get("news_feed", [])

# ─── BARRE DE DOCK SUPÉRIEUR (TICKER) ───
ticker_html = '<div class="ticker-container">'
for ccy, info in macro_data.items():
    bias_style = "bias-hawkish" if info.get("bias", "") in ["Hawkish", "Tightening"] else "bias-dovish"
    ticker_html += f"<div><b>{ccy}</b> ({info.get('cb', '')}): {info.get('rate', 0):.2f}% <span class='{bias_style}'>[{info.get('bias', '').upper()}]</span></div> • "
ticker_html += f"<div style='margin-left: auto; color:#71717a;'>STATUS: ONLINE | SYNC: {meta.get('updated_at', 'N/A')}</div></div>"
st.markdown(ticker_html, unsafe_allow_html=True)


# ==========================================
# ─── LES 5 ONGLETS DU TERMINAL ULTIME ───
# ==========================================
tab_macro, tab_cb, tab_flows, tab_sentiment, tab_tech = st.tabs([
    "📊 MACRO CONVERGENCE", 
    "🏛️ CENTRAL BANKS (OIS)", 
    "🐋 INSTITUTIONAL FLOWS",
    "📰 SENTIMENT & GEOPOL",
    "📈 MARKET HEATMAP"
])

# ─── ONGLET 1 : MACRO CONVERGENCE (Le cœur du réacteur) ───
with tab_macro:
    st.markdown("### Modèle Quantitatif G10 (Yields, Inflation, PMI)")
    
    # KPIs globaux en haut de l'onglet
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='metric-card'><div class='metric-title'>Indice de Risque Géopolitique</div><div class='metric-value' style='color:#ef4444;'>{meta.get('geo_risk_level', 'MODÉRÉ')}</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'><div class='metric-title'>Tonalité Globale Banques Centrales</div><div class='metric-value' style='color:#3b82f6;'>{meta.get('speech_tone', 'MIXED')}</div></div>", unsafe_allow_html=True)
    with c3: st.markdown("<div class='metric-card'><div class='metric-title'>Devise Forte (Top Score)</div><div class='metric-value' style='color:#10b981;'>USD</div></div>", unsafe_allow_html=True) # Dynamiser plus tard
    with c4: st.markdown("<div class='metric-card'><div class='metric-title'>Devise Faible (Pire Score)</div><div class='metric-value' style='color:#ef4444;'>CHF</div></div>", unsafe_allow_html=True)

    rows = []
    for ccy, info in macro_data.items():
        rows.append({
            "Asset": ccy,
            "Target Rate": f"{info.get('rate', 0.0):.2f}%",
            "10Y Yield": f"{info.get('yield_10y', 0.0):.2f}%",
            "Core Inflation (CPI)": f"{info.get('cpi', 0.0):.1f}%",
            "PMI (Activity)": f"{info.get('pmi', 50.0):.1f}",
            "Retail Sales": f"{info.get('retail_sales', 0.0):+.1f}%",
            "Unemployment": f"{info.get('unem', 0.0):.1f}%",
            "ALGO SCORE": scores.get(ccy, 0)
        })
    df_macro = pd.DataFrame(rows).sort_values(by="ALGO SCORE", ascending=False)
    st.dataframe(df_macro, use_container_width=True, hide_index=True, height=350)


# ─── ONGLET 2 : CENTRAL BANKS (Anticipation des taux) ───
with tab_cb:
    col_chart, col_data = st.columns([2, 1])
    
    with col_data:
        st.markdown("### Node Selection")
        selected_ccy = st.selectbox("Sélectionner la Banque Centrale :", list(macro_data.keys()))
        info_cb = macro_data.get(selected_ccy, {})
        ccy_p = probs.get(selected_ccy, {"prob_hike": 50.0, "prob_cut": 50.0})
        
        st.markdown(f"**Institution:** {info_cb.get('cb', 'N/A')}")
        st.markdown(f"**Taux Actuel:** {info_cb.get('rate', 0.0)}%")
        st.markdown(f"**Biais Déclaré:** {info_cb.get('bias', 'Neutral')}")
    
    with col_chart:
        fig = go.Figure(data=[go.Pie(
            labels=['Probabilité de Baisse (Cut)', 'Probabilité de Hausse (Hike)'],
            values=[ccy_p.get("prob_cut", 50.0), ccy_p.get("prob_hike", 50.0)],
            hole=.5,
            marker_colors=["#3b82f6", "#f97316"]
        )])
        fig.update_layout(
            title=f"Implied OIS Target Paths - {selected_ccy}",
            template="plotly_dark", paper_bgcolor="#050505", plot_bgcolor="#050505", 
            height=350, margin=dict(t=40, b=10, l=10, r=10)
        )
        st.plotly_chart(fig, use_container_width=True)


# ─── ONGLET 3 : INSTITUTIONAL FLOWS (Positionnement) ───
with tab_flows:
    st.markdown("### Smart Money vs Retail Sentiment (Prototypage COT)")
    st.info("Données de flux institutionnels simulées en attendant le scraping du CFTC COT Report.")
    
    # Simulation visuelle d'un graphique de positionnement (Smart Money)
    mock_cot = pd.DataFrame({
        "Currency": ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"],
        "Net Non-Commercials": [45000, -12000, 8500, -85000, -22000, -15000, -32000, -5000]
    }).sort_values(by="Net Non-Commercials", ascending=True)
    
    fig_cot = px.bar(
        mock_cot, x="Net Non-Commercials", y="Currency", orientation='h',
        color="Net Non-Commercials", color_continuous_scale=["#ef4444", "#10b981"]
    )
    fig_cot.update_layout(template="plotly_dark", paper_bgcolor="#050505", plot_bgcolor="#050505", height=350)
    st.plotly_chart(fig_cot, use_container_width=True)


# ─── ONGLET 4 : SENTIMENT & GEOPOLITIQUE (News en temps réel) ───
with tab_sentiment:
    st.markdown("### Flux d'Actualité Financière & Chocs Géopolitiques")
    
    if news_feed and isinstance(news_feed, list):
        for article in news_feed[:6]: # Affiche les 6 dernières news
            with st.expander(f"🔴 {article.get('title', 'Titre indisponible')}"):
                st.write(article.get('description', 'Pas de description.'))
                st.caption(f"Source: {article.get('source', 'Inconnue')} | Date: {article.get('publishedAt', '')}")
    else:
        st.warning("Aucun flux d'actualité détecté dans le cache. Lance un Force Sync.")


# ─── ONGLET 5 : MARKET HEATMAP (Corrélation & Force) ───
with tab_tech:
    st.markdown("### G10 Relative Strength Heatmap (Performance Journalière)")
    
    # Création d'une Heatmap basée sur le dictionnaire de base FX_RATES
    fx_data = [{"Pair": k, "Change": v["chg"]} for k, v in FX_RATES.items()]
    df_fx = pd.DataFrame(fx_data)
    
    if not df_fx.empty:
        # Création de colonnes et lignes factices pour une heatmap type "Treemap" de performance
        df_fx["AbsChange"] = df_fx["Change"].abs()
        fig_heat = px.treemap(
            df_fx, path=['Pair'], values='AbsChange', color='Change',
            color_continuous_scale=["#ef4444", "#1e1e24", "#10b981"],
            color_continuous_midpoint=0
        )
        fig_heat.update_layout(template="plotly_dark", paper_bgcolor="#050505", margin=dict(t=10, l=10, r=10, b=10), height=400)
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("Données FX brutes non disponibles pour générer la Heatmap.")
