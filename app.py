import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timezone

from data import MACRO, FX_RATES, MARKET_ASSETS, detect_market_sentiment, HIST_RATE, load_update_log
from utils.fx_calculations import compute_spreads, normalize_score, build_comparison_table
from utils.sentiment_engine import regime_weights
from utils.commodities_logic import wti_adjustment

# --- Configuration ---
st.set_page_config(page_title="FX Fundamental Terminal", layout="wide")

utc_now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC · %Y-%m-%d")
auto_sentiment, _ = detect_market_sentiment()

st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;background:linear-gradient(90deg,#6366f1 0%,#06b6d4 100%);padding:16px;border-radius:8px;margin-bottom:25px;">
    <div><span style="font-size:22px;font-weight:900;color:#fff;">📊 FX FUNDAMENTAL TERMINAL</span></div>
    <div style="text-align:right;font-family:monospace;font-size:13px;color:#fff;background:rgba(0,0,0,0.2);padding:6px 12px;border-radius:20px;">
        ⚙️ Régime : <b>{auto_sentiment}</b> | 🕒 {utc_now}
    </div>
</div>
""", unsafe_allow_html=True)

# --- Onglets principaux ---
tab_macro, tab_sentiment, tab_compare, tab_intermarket, tab_logs = st.tabs([
    "🏛️ Macro Ranking", "🎯 Risk Sentiment", "🔄 FX Comparison", "📊 Commodities", "🗄️ Logs"
])

# --- Onglet Macro ---
with tab_macro:
    st.subheader("Fundamental Jurisdictional Matrix")
    rows = []
    for ccy, info in MACRO.items():
        rows.append({
            "Devise": ccy,
            "Banque Centrale": info.get("cb"),
            "Taux d'intérêt": f"{info.get('rate',0):.2f}%",
            "10Y Yield": f"{info.get('yield_10y',0):.2f}%",
            "PIB": f"{info.get('gdp',0):+.2f}%",
            "Inflation": f"{info.get('cpi_prev',0):.1f}%",
            "Chômage": f"{info.get('unem',0):.1f}%",
            "Score": info.get("score",0)
        })
    st.dataframe(rows, use_container_width=True)

    st.subheader("📈 Évolution des taux directeurs")
    fig = go.Figure()
    for ccy, rates in HIST_RATE.items():
        fig.add_trace(go.Scatter(y=rates, x=list(range(len(rates))), mode='lines+markers', name=ccy))
    fig.update_layout(title="Taux directeurs", xaxis_title="Période", yaxis_title="Taux (%)")
    st.plotly_chart(fig, use_container_width=True)

# --- Onglet Sentiment ---
with tab_sentiment:
    st.subheader("Matrix Core Sentiment Monitor")
    vix = MARKET_ASSETS.get("VIX", {})
    sp500 = MARKET_ASSETS.get("US_500", {})
    gold = MARKET_ASSETS.get("GOLD", {})
    st.write(f"Indice VIX : {vix.get('price')} ({vix.get('chg')}%)")
    st.write(f"S&P 500 : {sp500.get('price')} ({sp500.get('chg')}%)")
    st.write(f"Or : {gold.get('price')} ({gold.get('chg')}%)")

# --- Onglet Comparaison ---
with tab_compare:
    st.subheader("FX Comparison & Prediction")
    base_ccy = st.selectbox("Devise de Base (Long)", list(MACRO.keys()), index=6)
    quote_ccy = st.selectbox("Devise de Contrepartie (Short)", list(MACRO.keys()), index=0)

    if base_ccy != quote_ccy:
        b_data, q_data = MACRO[base_ccy], MACRO[quote_ccy]
        spreads = compute_spreads(b_data, q_data)
        df_comp = build_comparison_table(base_ccy, quote_ccy, b_data, q_data, spreads)
        st.dataframe(df_comp, use_container_width=True, hide_index=True)

        regime, w_score, w_yield, w_rate, beta = regime_weights("Automatique", auto_sentiment)
        wti_bonus = wti_adjustment(base_ccy, quote_ccy, MARKET_ASSETS["WTI_CRUDE"]["chg"] > 0)

        expected_move = (spreads[2]*w_score) + (spreads[1]*w_yield) + (spreads[0]*w_rate) + wti_bonus
        score_pct = normalize_score(expected_move)

        if score_pct >= 50:
            st.success(f"Orientation BULLISH pour {base_ccy} vs {quote_ccy} ({score_pct}%)")
        else:
            st.error(f"Orientation BEARISH pour {base_ccy} vs {quote_ccy} ({100-score_pct}%)")

# --- Onglet Commodities ---
with tab_intermarket:
    st.subheader("Commodities Ledger")
    for asset, info in MARKET_ASSETS.items():
        st.write(f"{asset}: {info.get('price')} ({info.get('chg')}%)")

# --- Onglet Logs ---
with tab_logs:
    st.subheader("System Logs")
    logs = load_update_log()
    if logs:
        for entry in logs:
            st.text(f"[{entry.get('ts')}] Session: {entry.get('session')} | Trigger: {entry.get('trigger')} -> Status: {entry.get('status')}")
    else:
        st.info("Aucun log disponible.")
