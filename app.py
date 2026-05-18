# app.py
import os
from datetime import datetime, timezone

import streamlit as st
import plotly.graph_objects as go

from data import MACRO, FX_RATES, MARKET_ASSETS, detect_market_sentiment, HIST_RATE, load_update_log
from utils.fx_calculations import compute_spreads, normalize_score, build_comparison_table
from utils.sentiment_engine import regime_weights
from utils.commodities_logic import wti_adjustment
from utils.recommendations import rank_all_pairs
from utils.news import fetch_news

# --- Page config ---
st.set_page_config(page_title="FX Fundamental Terminal", layout="wide", initial_sidebar_state="collapsed")

# --- CSS / Theme ---
st.markdown(
    """
    <style>
    :root {
      --primary: #0f172a;
      --accent: #4f46e5;
      --accent-2: #06b6d4;
      --success: #10b981;
      --danger: #ef4444;
      --warning: #f59e0b;
      --card-bg: #ffffff;
      --muted: #6b7280;
    }
    /* Header */
    .ft-header {
      display:flex; justify-content:space-between; align-items:center;
      background: linear-gradient(90deg,var(--accent) 0%, var(--accent-2) 100%);
      padding:14px; border-radius:10px; color:white;
      box-shadow: 0 8px 20px rgba(79,70,229,0.12); margin-bottom:18px;
    }
    .ft-title { font-weight:800; font-size:20px; letter-spacing:0.6px; }
    .ft-meta { font-family: monospace; font-size:13px; opacity:0.95; }
    /* KPI cards */
    .kpi-card { background: linear-gradient(180deg,#ffffff 0%, #f8fafc 100%); border-radius:12px; padding:12px; box-shadow: 0 6px 18px rgba(2,6,23,0.06); }
    .kpi-title { font-size:12px; color:var(--muted); font-weight:700; }
    .kpi-value { font-size:20px; font-weight:900; color:var(--primary); }
    .small-muted { color:var(--muted); font-size:12px; }
    /* Insight cards */
    .insight-card { background: linear-gradient(135deg,#ffffff,#f1f5f9); border-left:6px solid var(--accent); padding:12px; border-radius:10px; box-shadow:0 6px 18px rgba(79,70,229,0.06); }
    .badge { display:inline-block; padding:6px 10px; border-radius:999px; font-weight:800; color:white; font-size:12px; margin-left:8px; }
    .badge-bull { background: linear-gradient(90deg,var(--success),#059669); }
    .badge-bear { background: linear-gradient(90deg,var(--danger),#dc2626); }
    .event-high { border-left:6px solid var(--danger); background:#fff7f7; padding:10px; border-radius:6px; }
    .event-med { border-left:6px solid var(--warning); background:#fffaf0; padding:10px; border-radius:6px; }
    .event-low { border-left:6px solid var(--success); background:#f0fdf4; padding:10px; border-radius:6px; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Header ---
utc_now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC · %Y-%m-%d")
auto_sentiment, sentiment_color = detect_market_sentiment()
st.markdown(
    f"""
    <div class="ft-header">
      <div class="ft-title">📊 FX INTERMARKET PRO — Fundamental FX Terminal</div>
      <div class="ft-meta">Mode: <b>AUTO</b> · Régime: <b style="color:{sentiment_color}">{auto_sentiment}</b> · 🕒 {utc_now}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Tabs ---
tab_macro, tab_sentiment, tab_compare, tab_intermarket, tab_insights, tab_logs = st.tabs(
    ["🏛️ Macro Ranking", "🎯 Risk Sentiment", "🔄 FX Comparison", "📊 Commodities", "🔎 Insights", "🗄️ Logs"]
)

# --- Helper: sparkline ---
def sparkline(y, color="#4f46e5", height=60):
    fig = go.Figure(go.Scatter(y=y, mode="lines", line=dict(color=color, width=2), hoverinfo="none"))
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(visible=False), yaxis=dict(visible=False), height=height)
    return fig

# --- TAB: Macro Ranking ---
with tab_macro:
    st.markdown("### Fundamental Jurisdictional Matrix")
    macro_rows = []
    for ccy, info in MACRO.items():
        macro_rows.append({
            "Devise": ccy,
            "Banque Centrale": info.get("cb", "N/A"),
            "Taux d'intérêt": f"{info.get('rate', 0.0):.2f}%",
            "10Y Yield": f"{info.get('yield_10y', 0.0):.2f}%",
            "PIB": f"{info.get('gdp', 0.0):+.2f}%",
            "Inflation": f"{info.get('cpi_prev', 0.0):.1f}%",
            "Chômage": f"{info.get('unem', 0.0):.1f}%",
            "Score": info.get("score", 0)
        })
    st.dataframe(macro_rows, use_container_width=True)

    st.markdown("### 📈 Évolution des taux directeurs (historique)")
    fig = go.Figure()
    for ccy, rates in HIST_RATE.items():
        fig.add_trace(go.Scatter(y=rates, x=list(range(len(rates))), mode="lines+markers", name=ccy))
    fig.update_layout(title="Taux directeurs", xaxis_title="Période", yaxis_title="Taux (%)", height=360)
    st.plotly_chart(fig, use_container_width=True)

# --- TAB: Risk Sentiment ---
with tab_sentiment:
    st.markdown("### Market Sentiment & Core Indicators")
    col1, col2, col3, col4 = st.columns(4)
    # FX spot cards
    fx_items = list(FX_RATES.items())[:4]
    for idx, (pair, info) in enumerate(fx_items):
        col = [col1, col2, col3, col4][idx % 4]
        is_up = info.get("chg", 0) >= 0
        change_color = "#10b981" if is_up else "#ef4444"
        col.markdown(
            f"""
            <div class="kpi-card">
              <div class="kpi-title">{pair}</div>
              <div class="kpi-value">{info.get('rate', 0):.4f}</div>
              <div class="small-muted" style="color:{change_color};">{info.get('chg', 0):+.2f}% Live</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Market assets
    st.markdown("#### Market Assets Snapshot")
    a1, a2, a3 = st.columns(3)
    vix = MARKET_ASSETS.get("VIX", {"price": None, "chg": None})
    wti = MARKET_ASSETS.get("WTI_CRUDE", {"price": None, "chg": None})
    sp = MARKET_ASSETS.get("US_500", {"price": None, "chg": None})
    a1.markdown(f"<div class='kpi-card'><div class='kpi-title'>VIX</div><div class='kpi-value'>{vix.get('price')}</div><div class='small-muted'>{vix.get('chg',0):+.2f}%</div></div>", unsafe_allow_html=True)
    a2.markdown(f"<div class='kpi-card'><div class='kpi-title'>WTI Crude</div><div class='kpi-value'>{wti.get('price')}</div><div class='small-muted'>{wti.get('chg',0):+.2f}%</div></div>", unsafe_allow_html=True)
    a3.markdown(f"<div class='kpi-card'><div class='kpi-title'>S&P 500</div><div class='kpi-value'>{sp.get('price')}</div><div class='small-muted'>{sp.get('chg',0):+.2f}%</div></div>", unsafe_allow_html=True)

# --- TAB: FX Comparison ---
with tab_compare:
    st.markdown("### FX Comparison & Predictive Signal")
    col_sel1, col_sel2 = st.columns(2)
    ccy_list = list(MACRO.keys())
    with col_sel1:
        base_ccy = st.selectbox("Devise de Base (Long)", ccy_list, index=6)
    with col_sel2:
        quote_ccy = st.selectbox("Devise de Contrepartie (Short)", ccy_list, index=0)

    if base_ccy == quote_ccy:
        st.warning("Veuillez sélectionner deux devises distinctes.")
    else:
        b_data, q_data = MACRO.get(base_ccy, {}), MACRO.get(quote_ccy, {})
        spreads = compute_spreads(b_data, q_data)
        df_comp = build_comparison_table(base_ccy, quote_ccy, b_data, q_data, spreads)
        st.dataframe(df_comp, use_container_width=True, hide_index=True)

        regime_tuple = regime_weights("Automatique", auto_sentiment)
        wti_bull = MARKET_ASSETS.get("WTI_CRUDE", {}).get("chg", 0) > 0
        wti_bonus = wti_adjustment(base_ccy, quote_ccy, wti_bull)

        expected_move = (spreads[2] * regime_tuple[1]) + (spreads[1] * regime_tuple[2]) + (spreads[0] * regime_tuple[3]) + wti_bonus
        score_pct = normalize_score(expected_move)

        # Visual gauge + interpretation
        if score_pct >= 50:
            st.markdown(f"**Orientation Macro globale :** 🟢 **BULLISH** pour {base_ccy}/{quote_ccy}")
            st.progress(score_pct / 100)
            st.markdown(f"<div style='margin-top:8px;'><span class='badge badge-bull'>{score_pct}%</span></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"**Orientation Macro globale :** 🔴 **BEARISH** pour {base_ccy}/{quote_ccy}")
            st.progress((100 - score_pct) / 100)
            st.markdown(f"<div style='margin-top:8px;'><span class='badge badge-bear'>{100 - score_pct}%</span></div>", unsafe_allow_html=True)

        # Auto-interpretation (short)
        drivers = []
        if spreads[0] > 0:
            drivers.append("Taux directeur favorable")
        if spreads[1] > 0:
            drivers.append("Rendement 10Y favorable")
        if spreads[2] > 0:
            drivers.append("Score fondamental supérieur")
        if wti_bonus != 0:
            drivers.append("Impact WTI/CAD")
        interp = " ; ".join(drivers) if drivers else "Aucun signal fondamental dominant"
        st.info(f"Interprétation rapide: {interp}")

# --- TAB: Commodities / Intermarket ---
with tab_intermarket:
    st.markdown("### Intermarket Analytics & Commodities")
    cols = st.columns(3)
    gold = MARKET_ASSETS.get("GOLD", {"price": None, "chg": None})
    wti = MARKET_ASSETS.get("WTI_CRUDE", {"price": None, "chg": None})
    sp500 = MARKET_ASSETS.get("US_500", {"price": None, "chg": None})
    cols[0].markdown(f"<div class='kpi-card'><div class='kpi-title'>Gold Spot</div><div class='kpi-value'>{gold.get('price')}</div><div class='small-muted'>{gold.get('chg',0):+.2f}%</div></div>", unsafe_allow_html=True)
    cols[1].markdown(f"<div class='kpi-card'><div class='kpi-title'>WTI Crude</div><div class='kpi-value'>{wti.get('price')}</div><div class='small-muted'>{wti.get('chg',0):+.2f}%</div></div>", unsafe_allow_html=True)
    cols[2].markdown(f"<div class='kpi-card'><div class='kpi-title'>S&P 500</div><div class='kpi-value'>{sp500.get('price')}</div><div class='small-muted'>{sp500.get('chg',0):+.2f}%</div></div>", unsafe_allow_html=True)

    st.markdown("#### Commodities vs FX (WTI ↔ CAD)")
    st.write("Le WTI influence souvent le CAD. Activez le filtre 'Insights' pour voir les paires CAD impactées.")

# --- TAB: Insights (Top/Bot pairs, Catalysts, News) ---
with tab_insights:
    st.markdown("### Insights & Recommandations")
    regime_tuple = regime_weights("Automatique", auto_sentiment)
    wti_bull = MARKET_ASSETS.get("WTI_CRUDE", {}).get("chg", 0) > 0
    ranked = rank_all_pairs(regime_tuple, wti_bull)

    # Top 3 bullish
    top_bull = [r for r in ranked if r["score_pct"] >= 50][:3]
    # Top 3 bearish (lowest scores)
    top_bear = sorted(ranked, key=lambda x: x["score_pct"])[:3]

    cols = st.columns(2)
    with cols[0]:
        st.markdown("<div class='insight-card'><b>🔥 Top 3 Bullish</b></div>", unsafe_allow_html=True)
        for item in top_bull:
            st.markdown(
                f"<div style='margin:8px 0;'><b>{item['pair']}</b> <span class='badge badge-bull'>{item['score_pct']}%</span><div class='small-muted'>raw: {item['raw']:.2f}</div></div>",
                unsafe_allow_html=True,
            )
    with cols[1]:
        st.markdown("<div class='insight-card'><b>❄️ Top 3 Bearish</b></div>", unsafe_allow_html=True)
        for item in top_bear:
            st.markdown(
                f"<div style='margin:8px 0;'><b>{item['pair']}</b> <span class='badge badge-bear'>{item['score_pct']}%</span><div class='small-muted'>raw: {item['raw']:.2f}</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown("#### 📅 Catalyseurs à venir (sélection rapide)")
    # Static example catalysts — replace with calendar API integration if available
    catalysts = [
        {"time": "2026-05-20 13:30 UTC", "event": "US Nonfarm Payrolls (NFP)", "impact": "High", "pairs": ["USD/*"]},
        {"time": "2026-05-21 08:00 UTC", "event": "ECB Rate Decision", "impact": "High", "pairs": ["EUR/*"]},
        {"time": "2026-05-22 02:00 UTC", "event": "BoC Rate Statement", "impact": "Medium", "pairs": ["CAD/*"]},
    ]
    for c in catalysts:
        cls = "event-high" if c["impact"] == "High" else ("event-med" if c["impact"] == "Medium" else "event-low")
        st.markdown(
            f"<div class='{cls}' style='margin-bottom:8px;'><b>{c['event']}</b> · <span class='small-muted'>{c['time']}</span><div class='small-muted'>Pairs impactées: {', '.join(c['pairs'])}</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("#### 📰 News & Catalyseurs (flux)")
    articles = fetch_news(limit=6)
    if articles:
        for a in articles:
            title = a.get("title") or "Untitled"
            src = a.get("source") or ""
            ts = (a.get("publishedAt") or "")[:19].replace("T", " ")
            url = a.get("url") or "#"
            st.markdown(f"- <b>{title}</b> <span class='small-muted'>({src} · {ts})</span> — <a href='{url}' target='_blank'>lire</a>", unsafe_allow_html=True)
    else:
        st.info("Aucune news disponible — vérifie la variable d'environnement NEWS_API_KEY ou le cache local.")

# --- TAB: Logs ---
with tab_logs:
    st.markdown("### System Logs")
    try:
        logs = load_update_log()
    except Exception:
        logs = []
    if logs:
        for entry in logs:
            st.text(f"[{entry.get('ts')}] Session: {entry.get('session')} | Trigger: {entry.get('trigger')} -> Status: {entry.get('status')}")
    else:
        st.info("Aucun log disponible.")

# --- Footer / Sources ---
st.markdown("---")
st.markdown(
    "<div style='display:flex;justify-content:space-between;align-items:center;'><div class='small-muted'>Données: Yahoo Finance (yfinance), sources macro locales; modèle: indicateurs fondamentaux pondérés.</div><div class='small-muted'>Dernière mise à jour: {}</div></div>".format(utc_now),
    unsafe_allow_html=True,
)
