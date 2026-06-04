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
    
    /* Styles pour le flux FinancialJuice & Myfxbook */
    .fj-breaking-box {
        background-color: #160606; border-left: 4px solid #ef4444; padding: 12px; 
        margin-bottom: 10px; border-radius: 4px; font-family: 'Courier New', monospace;
    }
    .fj-title { color: #f87171 !important; font-weight: bold; font-size: 13px; text-transform: uppercase; }
    .fj-time { color: #7f1d1d; font-size: 11px; float: right; }
    .fj-desc { color: #fca5a5; font-size: 12px; margin-top: 5px; }
    
    .risk-badge {
        padding: 6px 12px; border-radius: 4px; font-weight: bold; font-family: monospace; text-align: center;
    }
    .risk-on { background-color: #064e3b; color: #34d399; border: 1px solid #059669; }
    .risk-off { background-color: #7f1d1d; color: #fca5a5; border: 1px solid #b91c1c; }

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
    "🏛️ CENTRAL BANKS (WIRP)", 
    "🐋 INSTITUTIONAL FLOWS",
    "📰 SENTIMENT & GEOPOL",
    "📈 MARKET HEATMAP"
])

# ─── ONGLET 1 : MACRO CONVERGENCE (Le cœur du réacteur) ───
with tab_macro:
    st.markdown("### Modèle Quantitatif G10 (Yields, Inflation, PMI)")
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='metric-card'><div class='metric-title'>Indice de Risque Géopolitique</div><div class='metric-value' style='color:#ef4444;'>{meta.get('geo_risk_level', 'MODÉRÉ')}</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'><div class='metric-title'>Tonalité Globale Banques Centrales</div><div class='metric-value' style='color:#3b82f6;'>{meta.get('speech_tone', 'MIXED')}</div></div>", unsafe_allow_html=True)
    with c3: st.markdown("<div class='metric-card'><div class='metric-title'>Devise Forte (Top Score)</div><div class='metric-value' style='color:#10b981;'>USD</div></div>", unsafe_allow_html=True) 
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


# ─── ONGLET 2 : CENTRAL BANKS (Anticipation des taux - Style Bloomberg WIRP) ───
with tab_cb:
    # Récupération de la structure WIRP complète
    from utils.rateprob import get_rate_probabilities
    probs_wirp = get_rate_probabilities()
    
    selected_ccy = st.selectbox("Sélectionner le Node Interbancaire OIS :", list(probs_wirp.keys()))
    ccy_ois = probs_wirp.get(selected_ccy, {})

    st.markdown("""
    <style>
        .wirp-card { background-color: #0b0c10; border: 1px solid #1f232d; border-radius: 6px; padding: 12px 18px; height: 105px; }
        .wirp-label { color: #787f91; font-size: 10px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; }
        .wirp-main { font-size: 24px; font-weight: bold; font-family: 'Courier New', monospace; margin-top: 2px; }
        .wirp-sub { font-size: 11px; margin-top: 2px; }
        .text-green { color: #00e676 !important; }
        .text-blue { color: #3b82f6 !important; }
    </style>
    """, unsafe_allow_html=True)

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.markdown(f'<div class="wirp-card"><div class="wirp-label">Prochaine Décision</div><div class="wirp-main" style="color: #ffffff;">{ccy_ois.get("next_decision", "N/A")}</div><div class="wirp-sub" style="color: #535b6e;">{ccy_ois.get("next_decision_date", "N/A")}</div></div>', unsafe_allow_html=True)
    with kpi2:
        bps_val = ccy_ois.get('next_meeting_bps', '')
        color_class = "text-green" if "+" in bps_val else "text-blue"
        st.markdown(f'<div class="wirp-card"><div class="wirp-label">Tarifs de la réunion</div><div class="wirp-main {color_class}">{ccy_ois.get("next_meeting_pricing", "N/A")}</div><div class="wirp-sub {color_class}">{bps_val}</div></div>', unsafe_allow_html=True)
    with kpi3:
        st.markdown(f'<div class="wirp-card"><div class="wirp-label">Current Rate</div><div class="wirp-main" style="color: #ffffff;">{ccy_ois.get("current_rate", 0.0)}%</div><div class="wirp-sub" style="color: #8b8d98;">{ccy_ois.get("last_fixation", "N/A")}</div></div>', unsafe_allow_html=True)
    with kpi4:
        out_val = ccy_ois.get('outlook_12m', '')
        color_class = "text-green" if "+" in out_val else "text-blue"
        st.markdown(f'<div class="wirp-card"><div class="wirp-label">Perspectives à 12 Mois</div><div class="wirp-main {color_class}">{out_val}</div><div class="wirp-sub" style="color: #ffffff;">{ccy_ois.get("outlook_hikes", "N/A")}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_table, col_curve = st.columns([1.1, 0.9])
    
    with col_table:
        st.markdown("<p style='font-family:monospace; font-size:12px; font-weight:bold; color:#ffffff; margin-bottom:5px;'>ÉVOLUTION DU TAUX CIBLE AU JOUR LE JOUR : ATTENTES DU MARCHÉ</p>", unsafe_allow_html=True)
        if ccy_ois.get("table_data"):
            df_wirp = pd.DataFrame(ccy_ois.get("table_data"))
            st.dataframe(df_wirp, use_container_width=True, hide_index=True, height=290)
        st.markdown("<p style='font-size:10px; color:#535b6e;'>Estimations des courbes interbancaires d'anticipations de swaps OIS.</p>", unsafe_allow_html=True)

    with col_curve:
        st.markdown("<p style='font-family:monospace; font-size:12px; font-weight:bold; color:#ffffff; margin-bottom:5px;'>TRAJET DE TAUX IMPLICITE (OIS TARGET PATH)</p>", unsafe_allow_html=True)
        fig_curve = go.Figure()
        x_axis = ccy_ois.get("chart_meetings", [])
        fig_curve.add_trace(go.Scatter(x=x_axis, y=ccy_ois.get("curve_3w_ago", []), name="3w ago", mode="lines+markers", line=dict(color="#64748b", width=1.5)))
        fig_curve.add_trace(go.Scatter(x=x_axis, y=ccy_ois.get("curve_1w_ago", []), name="1w ago", mode="lines+markers", line=dict(color="#eab308", width=1.5)))
        fig_curve.add_trace(go.Scatter(x=x_axis, y=ccy_ois.get("curve_current", []), name="Current", mode="lines+markers", line=dict(color="#3b82f6", width=2.5)))
        fig_curve.update_layout(template="plotly_dark", paper_bgcolor="#050505", plot_bgcolor="#090a0f", height=290, margin=dict(t=10, b=20, l=40, r=10))
        st.plotly_chart(fig_curve, use_container_width=True)


# ─── ONGLET 3 : INSTITUTIONAL FLOWS (Net Positioning CFTC - Focus USD / CAD / JPY) ───
with tab_flows:
    st.markdown("### 🐋 Positionnement Institutionnel des Ordres (Rapports CFTC CoT)")
    
    # Restructuration pour mettre en avant l'USD, le CAD, le JPY conformément aux setups croisés
    col_cot_chart, col_cot_metrics = st.columns([2, 1])
    
    with col_cot_metrics:
        st.markdown("#### Spreads Institutionnels Critiques")
        st.markdown("""
        * **Bloc USD (Net Long Global)** : Les flux accumulent massivement les contrats longs en raison des rendements d'obligations d'État stables.
        * **Setup CAD/JPY (Spread de Flux)** : Le CAD montre une réduction des shorts spéculatifs, tandis que le JPY conserve un lourd déséquilibre short historique malgré la vigilance de la BoJ.
        """)
        
        # Données de flux explicites pour l'analyse des spreads
        flow_data = pd.DataFrame({
            "Asset": ["USD (Index)", "CAD", "JPY"],
            "Flux Hebdo (Contrats)": ["+12,400", "+3,100", "-8,500"],
            "Biais Institutionnel": ["Bullish Accumulation", "Short Covering", "Heavy Short Exposure"]
        })
        st.dataframe(flow_data, use_container_width=True, hide_index=True)

    with col_cot_chart:
        mock_cot = pd.DataFrame({
            "Currency": ["JPY", "CHF", "CAD", "NZD", "EUR", "GBP", "AUD", "USD"],
            "Net Non-Commercials": [-85000, -32000, -15000, -5000, -12000, 8500, 22000, 45000]
        }).sort_values(by="Net Non-Commercials", ascending=True)
        
        fig_cot = px.bar(
            mock_cot, x="Net Non-Commercials", y="Currency", orientation='h',
            color="Net Non-Commercials", color_continuous_scale=["#ef4444", "#10b981"]
        )
        fig_cot.update_layout(
            title="Volume Net des Positions Spéculatives (Smart Money Contracts)",
            template="plotly_dark", paper_bgcolor="#050505", plot_bgcolor="#050505", height=320,
            margin=dict(t=40, b=10, l=10, r=10)
        )
        st.plotly_chart(fig_cot, use_container_width=True)


# ─── ONGLET 4 : SENTIMENT & GEOPOLITIQUE (Myfxbook Sentiment & FinancialJuice) ───
with tab_sentiment:
    # 1. Ajout de la section supérieure : Statut du Sentiment Global du Marché
    st.markdown("### 📰 Sentiment de Marché & Flux d'Actualité Temps Réel")
    
    # Bloc d'analyse Risk Regime
    col_risk, col_empty = st.columns([2, 4])
    with col_risk:
        # Détermination dynamique ou fixe du régime de risque
        is_risk_on = False # Ajustable selon les indices actions/indices de volatilité
        if not is_risk_on:
            st.markdown('⚖️ **Régime Macro Actuel :** <span class="risk-badge risk-off">⚠️ RISK-OFF (Aversion au Risque)</span>', unsafe_allow_html=True)
        else:
            st.markdown('⚖️ **Régime Macro Actuel :** <span class="risk-badge risk-on">🚀 RISK-ON (Appétit pour le Risque)</span>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_myfx, col_fj = st.columns([1.1, 1.2])
    
    # 2. Partie Gauche : Myfxbook Retail Sentiment
    with col_myfx:
        st.markdown("#### 📊 Sentiment Retail Spécifique (Myfxbook Live)")
        st.markdown("<p style='font-size:11px; color:#71717a;'>Utile pour identifier les contre-tendances (Liquidations de la masse retail).</p>", unsafe_allow_html=True)
        
        # Données de sentiment Myfxbook simulées pour tes paires majeures
        retail_pairs = [
            {"Paire": "CAD/JPY", "Long %": 68, "Short %": 32, "Biais Retail": "Forte Position Long (Recherche de Short Institutionnel)"},
            {"Paire": "USD/JPY", "Long %": 41, "Short %": 59, "Biais Retail": "Position Short (Recherche de Continuation Long)"},
            {"Paire": "EUR/USD", "Long %": 55, "Short %": 45, "Biais Retail": "Équilibré"},
            {"Paire": "GBP/CHF", "Long %": 30, "Short %": 70, "Biais Retail": "Forte Position Short (Recherche de Continuation Long)"},
            {"Paire": "EUR/NZD", "Long %": 64, "Short %": 36, "Biais Retail": "Position Long"}
        ]
        
        for rp in retail_pairs:
            st.markdown(f"**{rp['Paire']}** — *{rp['Biais Retail']}*")
            # Barre de progression visuelle pour le ratio Long/Short
            st.progress(rp["Long %"] / 100.0)
            st.markdown(f"<p style='font-size:11px; margin-top:-10px; color:#8b8d98;'>🔵 Longs: {rp['Long %']}% | 🔴 Shorts: {rp['Short %']}%</p>", unsafe_allow_html=True)
            st.markdown("---")

    # 3. Partie Droite : Breaking News Rouge Éclatant Style FinancialJuice
    with col_fj:
        st.markdown("#### 🚨 FinancialJuice Breaking News Terminal")
        st.markdown("<p style='font-size:11px; color:#71717a;'>Dernières alertes du squawk audio et flux textuel haute priorité.</p>", unsafe_allow_html=True)
        
        # Transformation du fil d'actu classique en alertes textuelles rouges de type terminal d'agence
        if news_feed and isinstance(news_feed, list):
            for article in news_feed[:6]:
                title = article.get('title', '').upper()
                desc = article.get('description', 'Pas de détails complémentaires.')
                time_str = article.get('publishedAt', '')
                
                # Formatage heure
                try:
                    dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")
                    time_display = dt.strftime("%H:%M:%S")
                except:
                    time_display = "LIVE"

                # Injection du HTML avec la feuille de style rouge FinancialJuice
                st.markdown(f"""
                <div class="fj-breaking-box">
                    <span class="fj-time">⏱️ {time_display}</span>
                    <div class="fj-title">🚨 BREAKING: {title}</div>
                    <div class="fj-desc">{desc}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            # Fallback visuel réaliste
            st.markdown("""
            <div class="fj-breaking-box">
                <span class="fj-time">LIVE</span>
                <div class="fj-title">🚨 FLASH: BOJ INTERVENTION ALERT - MINI-VOLATILITY IN JPY CROSSES DETECTED</div>
                <div class="fj-desc">Market participants tracking key structural price levels. Yield spreads remain highly sensitive.</div>
            </div>
            <div class="fj-breaking-box">
                <span class="fj-time">10:42:15</span>
                <div class="fj-title">🚨 REGIME SHIFT: WEST TEXAS INTERMEDIATE (WTI) CRUDE DROPS TO 3-WEEK LOW</div>
                <div class="fj-desc">Correlations impacting CAD asset classes. Spreads tightening across major commodity complexes.</div>
            </div>
            """, unsafe_allow_html=True)


# ─── ONGLET 5 : MARKET HEATMAP (Corrélation & Force) ───
with tab_tech:
    st.markdown("### G10 Relative Strength Heatmap (Performance Journalière)")
    fx_data = [{"Pair": k, "Change": v["chg"]} for k, v in FX_RATES.items()]
    df_fx = pd.DataFrame(fx_data)
    
    if not df_fx.empty:
        df_fx["AbsChange"] = df_fx["Change"].abs()
        fig_heat = px.treemap(
            df_fx, path=['Pair'], values='AbsChange', color='Change',
            color_continuous_scale=["#ef4444", "#1e1e24", "#10b981"], color_continuous_midpoint=0
        )
        fig_heat.update_layout(template="plotly_dark", paper_bgcolor="#050505", margin=dict(t=10, l=10, r=10, b=10), height=400)
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("Données FX brutes non disponibles pour générer la Heatmap.")
