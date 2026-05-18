"""
FX Fundamental Terminal — TradeSave+ Pro Edition (V9.6 Final)
Bloomberg Style Layout — Ambiance colorée, gestion WTI/CAD et normalisation 1-100%
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timezone

from data import (
    MACRO, FX_RATES, MARKET_ASSETS, MONTHS, HIST_RATE, score_meta,
    load_update_log, get_last_update, init_db, detect_market_sentiment
)

init_db()

# Palette vive, gaie et contrastée
COLORS = {
    "primary": "#1e1b4b", "accent": "#4f46e5", "success": "#10b981", "danger": "#ef4444", 
    "warning": "#f59e0b", "bg_card": "#f8fafc", "border": "#cbd5e1"
}

st.set_page_config(page_title="FX Intermarket Pro Terminal", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS pour une interface dynamique
st.markdown(f"""
<style>
    [data-testid="stSidebar"] {{ display: none !important; }}
    .main .block-container {{ padding-top: 1.5rem !important; max-width: 95% !important; }}
    h1, h2, h3, h4 {{ color: {COLORS["primary"]} !important; font-weight: 800 !important; }}
    
    /* Cartes en dégradé */
    .terminal-card {{ background: linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%); border-left: 5px solid {COLORS["accent"]}; border-radius: 8px; padding: 16px; margin-bottom: 16px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }}
    .card-success {{ border-left: 5px solid {COLORS["success"]}; background: linear-gradient(135deg, #ffffff 0%, #f0fdf4 100%); }}
    .card-danger {{ border-left: 5px solid {COLORS["danger"]}; background: linear-gradient(135deg, #ffffff 0%, #fef2f2 100%); }}
    .card-warning {{ border-left: 5px solid {COLORS["warning"]}; background: linear-gradient(135deg, #ffffff 0%, #fffbeb 100%); }}
    
    /* Style du badge d'indice de force */
    .force-badge {{ padding: 10px 20px; border-radius: 6px; color: white; font-weight: 900; font-size: 20px; display: inline-block; margin-top: 10px; }}
    .badge-bullish {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); box-shadow: 0 4px 10px rgba(16, 185, 129, 0.3); }}
    .badge-bearish {{ background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); box-shadow: 0 4px 10px rgba(239, 68, 68, 0.3); }}
</style>
""", unsafe_allow_html=True)

utc_now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC · %Y-%m-%d")
auto_sentiment, sentiment_color = detect_market_sentiment()

st.markdown(f"""
<div style="display: flex; justify-content: space-between; align-items: center; background: linear-gradient(90deg, #6366f1 0%, #06b6d4 100%); padding: 16px; border-radius: 8px; margin-bottom: 25px; box-shadow: 0 10px 15px -3px rgba(6, 182, 212, 0.2);">
    <div>
        <span style="font-size: 22px; font-weight: 900; color: #ffffff; letter-spacing: 1px;">📊 FX INTERMARKET INTELLIGENCE PRO</span>
    </div>
    <div style="text-align: right; font-family: monospace; font-size: 13px; color: #ffffff; background: rgba(0,0,0,0.2); padding: 6px 12px; border-radius: 20px;">
        ⚙️ REGIME SYSTEME : <span style="color:#ffffff; font-weight:900;">{auto_sentiment}</span> | 🕒 {utc_now}
    </div>
</div>
""", unsafe_allow_html=True)

tab_macro, tab_sentiment, tab_compare, tab_intermarket, tab_system = st.tabs([
    "🏛️ MACRO RANKING ENGINE", "🎯 RISK SENTIMENT MATRIX", "🔄 FX COMPARISON & PREDICTION", "📊 COMMODITIES SPREADS", "🗄️ AUDIT LOGS"
])

# ── TAB 1 : ENGINE MONÉTAIRE ─────────────────────────────────────
with tab_macro:
    st.markdown("### Fundamental Jurisdictional Matrix")
    macro_rows = []
    for ccy, info in MACRO.items():
        _, _, txt_status = score_meta(info.get("score", 0))
        macro_rows.append({
            "Devise": ccy, "Banque Centrale": info.get("cb", "N/A"),
            "Taux d'intérêt": f"{info.get('rate', 0.0):.2f}%",
            "10Y Bond Yield": f"{info.get('yield_10y', 0.0):.2f}%",
            "PIB Trimestriel": f"{info.get('gdp', 0.0):+.2f}%",
            "Inflation (CPI)": f"{info.get('cpi_prev', 0.0):.1f}%",
            "Chômage": f"{info.get('unem', 0.0):.1f}%", "Biais": txt_status, "Score": info.get("score", 0)
        })
    st.dataframe(pd.DataFrame(macro_rows).sort_values(by="Score", ascending=False), use_container_width=True, hide_index=True)

    st.markdown("<br>### Live Spot FX Rates", unsafe_allow_html=True)
    cols_fx = st.columns(4)
    for idx, (pair, f_info) in enumerate(FX_RATES.items()):
        col_tgt = cols_fx[idx % 4]
        is_up = f_info.get("chg", 0) >= 0
        card_style = "card-success" if is_up else "card-danger"
        chg_color = COLORS["success"] if is_up else COLORS["danger"]
        
        col_tgt.markdown(f"""
        <div class="terminal-card {card_style}">
            <span style="font-size: 12px; font-weight: 800; color: #475569;">{pair}</span>
            <div style="font-size: 24px; font-weight: 900; color: {COLORS["primary"]}; margin: 2px 0;">{f_info.get('rate', 0.0):.4f}</div>
            <span style="font-size: 12px; font-700; color: {chg_color};">{f_info.get('chg', 0.0):+.2f}% Live</span>
        </div>
        """, unsafe_allow_html=True)

# ── TAB 2 : RISK SENTIMENT MATRIX ───────────────────────────────
with tab_sentiment:
    st.markdown("### Matrix Core Sentiment Monitor")
    col_vix, col_sp, col_safe = st.columns(3)
    vix_data = MARKET_ASSETS.get("VIX", {"price": 13.50, "chg": -2.10})
    sp_data = MARKET_ASSETS.get("US_500", {"price": 5214.30, "chg": 0.28})
    
    vix_color = COLORS["success"] if vix_data['price'] < 18 else COLORS["danger"]
    vix_card = "card-success" if vix_data['price'] < 18 else "card-danger"
    
    col_vix.markdown(f"""<div class="terminal-card {vix_card}"><b>INDICE DE VOLATILITÉ (VIX):</b> <h2 style='margin:0; color:{vix_color};'>{vix_data['price']:.2f} Pts</h2><span>Flux Volatilité: {vix_data['chg']:+.2f}%</span></div>""", unsafe_allow_html=True)
    col_sp.markdown(f"""<div class="terminal-card"><b>MARKET VELOCITY (S&P 500):</b> <h2 style='margin:0;'>{sp_data['price']:,.1f} Pts</h2><span>Variation journalière : {sp_data['chg']:+.2f}%</span></div>""", unsafe_allow_html=True)
    
    safe_bias = "RECHERCHÉ (Achat USD)" if "OFF" in auto_sentiment else "LIQUIDATION EXOGÈNE"
    col_safe.markdown(f"""<div class="terminal-card card-warning"><b>CAPITAUX VALEURS REFUGES:</b> <h3 style='margin:4px 0; color:{COLORS["warning"]};'>{safe_bias}</h3><span>Analyse des flux obligataires interbancaires.</span></div>""", unsafe_allow_html=True)

# ── TAB 3 : FX COMPARISON & PREDICTION (INTELLIGENT 1-100%) ──────
with tab_compare:
    st.markdown("### Model Dissection & Predictive System")
    
    wti_trend = MARKET_ASSETS.get("WTI_CRUDE", {"price": 79.24, "chg": 1.15})
    wti_is_bullish = wti_trend["chg"] > 0
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        mode_contexte = st.radio("Filtre de Sentiment Global :", ["Mode Automatique (Flux)", "Forcer RISK-ON", "Forcer RISK-OFF"], horizontal=True)
    with col_c2:
        wti_status_text = "HAUSSE 🔥 (Bonus CAD activé)" if wti_is_bullish else "BAISSE ❄️ (Malus CAD activé)"
        wti_card_style = "card-success" if wti_is_bullish else "card-danger"
        st.markdown(f"""<div class="terminal-card {wti_card_style}" style="margin:0; padding:8px 16px;"><b>DYNAMIQUE INTERMARCHÉ PÉTROLE (WTI) :</b> {wti_trend['price']:.2f} USD ({wti_trend['chg']:+.2f}%)<br><span style="font-size:12px;">Statut : <b>{wti_status_text}</b></span></div>""", unsafe_allow_html=True)

    if "RISK-ON" in mode_contexte or ("Automatique" in mode_contexte and "RISK-ON" in auto_sentiment):
        regime_actif, poids_score, poids_yield, poids_rate, ajustement_beta = "RISK-ON", 0.30, 0.50, 0.20, 0.5
    elif "RISK-OFF" in mode_contexte or ("Automatique" in mode_contexte and "RISK-OFF" in auto_sentiment):
        regime_actif, poids_score, poids_yield, poids_rate, ajustement_beta = "RISK-OFF", 0.70, 0.15, 0.15, -1.8
    else:
        regime_actif, poids_score, poids_yield, poids_rate, ajustement_beta = "NORMAL", 0.45, 0.40, 0.15, 0.0

    ccy_list = list(MACRO.keys())
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1: base_ccy = st.selectbox("Sélectionner la Devise de Base (Achat/Long)", ccy_list, index=6) # NZD
    with col_sel2: quote_ccy = st.selectbox("Sélectionner la Devise de Contrepartie (Vente/Short)", ccy_list, index=0) # USD
        
    if base_ccy == quote_ccy:
        st.warning("Veuillez sélectionner deux blocs monétaires distincts.")
    else:
        b_data, q_data = MACRO[base_ccy], MACRO[quote_ccy]
        
        b_yield = b_data.get("yield_10y", 0.0)
        q_yield = q_data.get("yield_10y", 0.0)
        b_rate, q_rate = b_data.get("rate", 0.0), q_data.get("rate", 0.0)
        b_score, q_score = b_data.get("score", 0), q_data.get("score", 0)
        
        interest_spread = b_rate - q_rate
        yield_10y_spread = b_yield - q_yield
        score_diff = b_score - q_score
        
        # Gestion dynamique du pétrole (WTI) pour le CAD
        wti_bonus = 0.0
        if wti_is_bullish:
            if base_ccy == "CAD": wti_bonus += 0.85
            if quote_ccy == "CAD": wti_bonus -= 0.85
        else:
            if base_ccy == "CAD": wti_bonus -= 0.50
        
        comp_rows = [
            {"Indicateur Fondamental": "Banque Centrale", base_ccy: str(b_data.get("cb", "N/A")), quote_ccy: str(q_data.get("cb", "N/A")), "Spread / Différentiel": "—"},
            {"Indicateur Fondamental": "Taux d'intérêt Directeur", base_ccy: f"{b_rate:.2f}%", quote_ccy: f"{q_rate:.2f}%", "Spread / Différentiel": f"{interest_spread:+.2f}%"},
            {"Indicateur Fondamental": "Rendement Obligataire Sovereign 10Y", base_ccy: f"{b_yield:.2f}%", quote_ccy: f"{q_yield:.2f}%", "Spread / Différentiel": f"{yield_10y_spread:+.2f}%"},
            {"Indicateur Fondamental": "Score Quanti Fondamental", base_ccy: str(b_score), quote_ccy: str(q_score), "Spread / Différentiel": f"{score_diff:+d}"}
        ]
        st.dataframe(pd.DataFrame(comp_rows), use_container_width=True, hide_index=True)
        
        st.markdown("### 🎯 Indice de Force Quantitatif (1 à 100%)")
        
        # Algorithme fondamental réajusté
        base_expected_move = (score_diff * poids_score) + (yield_10y_spread * poids_yield) + (interest_spread * poids_rate) + wti_bonus
        if regime_actif == "RISK-OFF" and base_ccy in ["NZD", "AUD", "CAD"] and quote_ccy in ["USD", "CHF", "JPY"]:
            base_expected_move += ajustement_beta

        # NORMALISATION DE 1 À 100% (Min-Max)
        v_min, v_max = -4.0, 4.0
        clamped_move = max(v_min, min(v_max, base_expected_move))
        score_pourcentage = int(((clamped_move - v_min) / (v_max - v_min)) * 100)
        score_pourcentage = max(1, min(100, score_pourcentage)) # Sécurité bornes stricts [1, 100]

        # Choix de l'orientation visuelle de la jauge
        if score_pourcentage >= 50:
            st.markdown(f"**Orientation Macro globale :** 🟢 **BULLISH** pour {base_ccy} face à {quote_ccy}")
            st.progress(score_pourcentage / 100)
            st.markdown(f"<div class='force-badge badge-bullish'>Force du Signal Long : {score_pourcentage}%</div>", unsafe_allow_html=True)
        else:
            force_short = 100 - score_pourcentage
            st.markdown(f"**Orientation Macro globale :** 🔴 **BEARISH** pour {base_ccy} face à {quote_ccy}")
            st.progress(force_short / 100)
            st.markdown(f"<div class='force-badge badge-bearish'>Force du Signal Short : {force_short}%</div>", unsafe_allow_html=True)

        # Alertes contextuelles
        if wti_is_bullish and ((base_ccy == "CAD" and score_pourcentage < 50) or (quote_ccy == "CAD" and score_pourcentage >= 50)):
            st.markdown(f"""<div style="background-color: #fffbeb; border-left: 6px solid {COLORS["warning"]}; padding: 12px; border-radius: 4px; margin-top: 15px;"><span style="color: #b45309; font-weight: 800;">⚠️ ALERTE FLUX ÉNERGIE :</span> Le WTI pousse le CAD à la hausse. Attention si le score indique une vente.</div>""", unsafe_allow_html=True)

# ── TAB 4 : COMMODITIES SPREADS ─────────────────────────────────
with tab_intermarket:
    st.markdown("### Intermarket Analytics & Commodities Ledger")
    c_asset1, c_asset2, c_asset3 = st.columns(3)
    
    gold_info = MARKET_ASSETS.get("GOLD", {"price": 2345.80, "chg": 0.45})
    c_asset1.markdown(f"""<div class="terminal-card"><b>GOLD SPOT:</b> <h3 style='margin:0;'>{gold_info.get('price'):,.2f} USD</h3><span>{gold_info.get('chg'):+.2f}%</span></div>""", unsafe_allow_html=True)
    
    c_asset2.markdown(f"""<div class="terminal-card card-success"><b>CRUDE OIL WTI:</b> <h3 style='margin:0; color:{COLORS["success"]};'>{wti_trend.get('price'):.2f} USD</h3><span>{wti_trend.get('chg'):+.2f}%</span></div>""", unsafe_allow_html=True)
    
    sp_info = MARKET_ASSETS.get("US_500", {"price": 5214.30, "chg": 0.28})
    c_asset3.markdown(f"""<div class="terminal-card"><b>S&P 500 INDEX:</b> <h3 style='margin:0;'>{sp_info.get('price'):,.1f} Pts</h3><span>{sp_info.get('chg'):+.2f}%</span></div>""", unsafe_allow_html=True)

# ── TAB 5 : SYSTEM LOGS ─────────────────────────────────────────
with tab_system:
    st.markdown("### Logs")
    logs = load_update_log()
    if logs:
        for entry in logs:
            st.text(f"[{entry.get('ts')}] Session: {entry.get('session')} | Trigger: {entry.get('trigger')} -> Status: {entry.get('status').upper()}")
    else:
        st.info("Aucun traitement enregistré dans les tables de logs.")