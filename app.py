# app.py
"""
FX Intermarket Pro — v3.0
Dark fintech terminal. Finalized full app with high-contrast Macro table rendering.
This file is based on your provided code and ensures the "Matrice Juridictionnelle Fondamentale"
table is clearly readable on a dark blue background (white text, larger font, accessible contrast).
"""

import os
import json
import time
import requests
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go

# Optional: BeautifulSoup for scraping RateProbability
try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

# Project imports (these modules must exist in your repo)
from data import (
    MACRO,
    FX_RATES,
    MARKET_ASSETS,
    detect_market_sentiment,
    HIST_RATE,
    load_update_log,
    start_background_updater,
    refresh_and_persist,
    PAIRS,
)
from utils.fx_calculations import compute_spreads, normalize_score, build_comparison_table
from utils.sentiment_engine import regime_weights
from utils.commodities_logic import wti_adjustment
from utils.recommendations import rank_unique_pairs as rank_all_pairs
from utils.news import fetch_news

# -------------------------
# Page config
# -------------------------
st.set_page_config(
    page_title="FX Intermarket Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Start background updater (idempotent)
try:
    start_background_updater(interval_seconds=120)
except Exception:
    pass

# -------------------------
# Global CSS / theme (dark blue / mauve accents)
# Ensures table text is highly readable (white text, larger font)
# -------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root{
  --bg: #041022;
  --surface: #0d1424;
  --panel: #0b1624;
  --panel-2: #0f2233;
  --accent: #7c3aed;
  --accent-2: #0891b2;
  --accent-g: linear-gradient(135deg, #7c3aed 0%, #0891b2 100%);
  --txt: #ffffff;
  --txt-2: #cbd5e1;
  --txt-3: #94a3b8;
  --border: rgba(255,255,255,0.06);
  --r: 12px;
  --z1: 0 1px 4px rgba(0,0,0,.4);
  --z2: 0 4px 16px rgba(0,0,0,.55);
  --z3: 0 8px 32px rgba(0,0,0,.65);
}

/* App background */
html, body, .stApp, .main, [data-testid="stAppViewContainer"] {
  background: linear-gradient(180deg, var(--bg) 0%, #03121b 100%) !important;
  color: var(--txt);
  font-family: 'Inter', system-ui, sans-serif;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden !important; }
[data-testid="stDecoration"] { display: none !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-thumb { background: rgba(124,58,237,.4); border-radius: 6px; }

/* Topbar */
.topbar { display:flex; justify-content:space-between; align-items:center; background:linear-gradient(90deg, rgba(124,58,237,0.14), rgba(8,145,178,0.08)); border-radius:14px; padding:14px 20px; margin-bottom:18px; border:1px solid var(--border); box-shadow:var(--z3); }
.topbar-title { font-size:18px; font-weight:800; background:var(--accent-g); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.topbar-sub { font-size:12px; color:var(--txt-2); margin-top:2px; }
.topbar-ts { font-family: 'JetBrains Mono', monospace; font-size:12px; color:var(--txt-3); }

/* Sidebar */
[data-testid="stSidebar"] { background: var(--surface) !important; border-right:1px solid var(--border) !important; }
.sidebar-section { background: linear-gradient(180deg,var(--panel),var(--panel-2)); border:1px solid var(--border); border-radius:10px; padding:12px; margin-bottom:12px; color:var(--txt-2); }

/* KPI card */
.kpi { background: linear-gradient(180deg,var(--panel),var(--panel-2)); border:1px solid var(--border); border-radius:10px; padding:12px; box-shadow:var(--z2); color:var(--txt); }

/* Streamlit dataframe overrides (ensure white text) */
.stDataFrame, .stTable { color: var(--txt) !important; }
.stDataFrame th, .stTable thead th { color: var(--txt) !important; background: rgba(124,58,237,0.06) !important; font-weight:700 !important; font-size:13px !important; padding:10px !important; }
.stDataFrame td, .stTable tbody td { color: var(--txt) !important; font-family:'JetBrains Mono', monospace !important; font-size:13px !important; padding:10px !important; background:transparent !important; }

/* Macro HTML table wrapper (components.html) */
.macro-html-wrapper { padding:8px; height:420px; overflow:auto; }
.macro-table { width:100%; border-collapse:collapse; background:transparent; }
.macro-table thead th { color: var(--txt); font-weight:800; font-size:13px; padding:12px; text-align:center; background: rgba(124,58,237,0.06); border-bottom:1px solid rgba(255,255,255,0.04); }
.macro-table tbody td { color: var(--txt); padding:12px; text-align:center; font-family: 'JetBrains Mono', monospace; font-size:13px; border-bottom:1px solid rgba(255,255,255,0.02); }
.macro-score { display:flex; flex-direction:column; align-items:center; gap:6px; }
.macro-score .num { font-weight:800; color:var(--txt); }
.macro-score .bar { width:100%; height:8px; background: rgba(255,255,255,0.03); border-radius:999px; overflow:hidden; }
.macro-score .bar > div { height:100%; border-radius:999px; }

/* Responsive */
@media (max-width: 800px) {
  .macro-table thead th, .macro-table tbody td { font-size:12px; padding:8px; }
}
</style>
""",
    unsafe_allow_html=True,
)

# -------------------------
# Helpers
# -------------------------
def sparkline(values, color="#10b981", height=44):
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    rgb = hex_to_rgb(color) if isinstance(color, str) and color.startswith("#") else (16,185,129)
    fill = f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0.08)"
    fig = go.Figure(go.Scatter(
        y=values, mode="lines",
        line=dict(color=color, width=2),
        fill="tozeroy",
        fillcolor=fill,
        hoverinfo="none",
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False, fixedrange=True),
        yaxis=dict(visible=False, fixedrange=True),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig

def delta_html(chg):
    arrow = "▲" if chg >= 0 else "▼"
    color = "#10b981" if chg >= 0 else "#f43f5e"
    return f'<span style="color:{color}; font-weight:700;">{arrow} {abs(chg):.2f}%</span>'

def regime_class(sentiment):
    s = (sentiment or "").lower()
    if "bull" in s or "risk on" in s: return "regime-bull", "🟢"
    if "bear" in s or "risk off" in s: return "regime-bear", "🔴"
    return "regime-neut", "⚪"

# High-contrast HTML table renderer for Macro
def score_style_html(val):
    try:
        v = float(val)
    except Exception:
        return f'<div style="color:#fff;font-weight:700;">{val}</div>'
    if v >= 70:
        color = "#10b981"
    elif v >= 40:
        color = "#f59e0b"
    else:
        color = "#f43f5e"
    pct = max(0, min(100, int(v)))
    bar_html = f'<div class="bar"><div style="width:{pct}%; background: linear-gradient(90deg, {color}, rgba(255,255,255,0.06));"></div></div>'
    return f'<div class="macro-score"><div class="num" style="color:{color}; font-weight:800;">{v:.0f}</div>{bar_html}</div>'

def df_to_html_table_high_contrast(df, height=360):
    cols = list(df.columns)
    thead = "<tr>" + "".join([f'<th>{c}</th>' for c in cols]) + "</tr>"
    tbody_rows = []
    for _, row in df.iterrows():
        cells = []
        for c in cols:
            val = row[c]
            if c == "Score":
                cell_html = score_style_html(val)
                cells.append(f'<td style="vertical-align:middle;">{cell_html}</td>')
            else:
                cells.append(f'<td style="color:#fff; font-family:JetBrains Mono;">{val}</td>')
        tbody_rows.append("<tr>" + "".join(cells) + "</tr>")
    tbody = "\n".join(tbody_rows)
    table_html = f'''
    <div class="macro-html-wrapper">
      <table class="macro-table">
        <thead>{thead}</thead>
        <tbody>{tbody}</tbody>
      </table>
    </div>
    '''
    return table_html

# -------------------------
# Header
# -------------------------
utc_now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC · %Y-%m-%d")
auto_sentiment, sentiment_color = detect_market_sentiment()
r_cls, r_dot = regime_class(auto_sentiment)

st.markdown(f"""
<div class="topbar">
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:linear-gradient(90deg,#7c3aed,#0891b2);box-shadow:0 6px 18px rgba(124,58,237,.35);">📈</div>
    <div>
      <div class="topbar-title">FX INTERMARKET PRO</div>
      <div class="topbar-sub">Terminal fondamental · signaux intermarché · WTI ↔ CAD</div>
    </div>
  </div>
  <div style="text-align:right;">
    <div style="margin-bottom:6px;"><span style="padding:6px 12px;border-radius:999px;background:rgba(255,255,255,0.02);font-weight:700;color:#cbd5e1;">{r_dot} Régime: {auto_sentiment}</span></div>
    <div class="topbar-ts">{utc_now}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# -------------------------
# Sidebar
# -------------------------
with st.sidebar:
    st.markdown("### Paramètres")
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    auto_refresh = st.checkbox("Auto-refresh", value=True, help="Mise à jour en arrière-plan")
    interval = st.slider("Intervalle (sec)", min_value=60, max_value=900, value=120, step=30)
    kpi_count = st.selectbox("Paires KPI affichées", options=[3, 4, 6, 9], index=2)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Actions")
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    if st.button("⚡ Forcer mise à jour"):
        ok = refresh_and_persist()
        if ok:
            st.success("✓ Mise à jour terminée")
        else:
            st.error("✗ Échec — consulter les logs")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Export")
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div style="color:#cbd5e1;font-size:13px;">Configurez votre clé API pour publier vers des services externes.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

if auto_refresh:
    try:
        start_background_updater(interval_seconds=interval)
    except Exception:
        pass

# -------------------------
# Tabs
# -------------------------
tab_macro, tab_sentiment, tab_compare, tab_intermarket, tab_insights, tab_logs = st.tabs(
    ["🏛  Macro", "🎯  Sentiment", "🔄  Comparaison", "📊  Commodités", "🔎  Insights", "🗄  Logs"]
)

# -------------------------
# TAB — MACRO
# -------------------------
with tab_macro:
    st.markdown('<div style="font-weight:700;color:#cbd5e1;margin-bottom:8px;">Matrice Juridictionnelle Fondamentale</div>', unsafe_allow_html=True)

    df_macro = pd.DataFrame([
        {
            "Devise":          ccy,
            "Banque Centrale": info.get("cb", "N/A"),
            "Taux (%)":        round(info.get("rate", 0.0), 2),
            "10Y Yield (%)":   round(info.get("yield_10y", 0.0), 2),
            "PIB (%)":         round(info.get("gdp", 0.0), 2),
            "Inflation (%)":   round(info.get("cpi_prev", 0.0), 1),
            "Chômage (%)":     round(info.get("unem", 0.0), 1),
            "Score":           info.get("score", 0),
        }
        for ccy, info in MACRO.items()
    ])

    # Render high-contrast HTML table first, fallback to dataframe
    try:
        html_table = df_to_html_table_high_contrast(df_macro, height=360)
        components.html(html_table, height=420, scrolling=True)
        st.markdown("<div style='margin-top:8px;color:#cbd5e1;font-size:12px;'>Si le tableau stylé n'apparaît pas, version alternative ci‑dessous :</div>", unsafe_allow_html=True)
        st.dataframe(df_macro, use_container_width=True, height=220)
    except Exception:
        st.warning("Rendu HTML du tableau indisponible — affichage de secours.")
        st.dataframe(df_macro, use_container_width=True, height=360)

    st.markdown('<div style="height:18px;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-weight:700;color:#cbd5e1;margin-bottom:8px;">Évolution des Taux Directeurs</div>', unsafe_allow_html=True)

    palette = ["#7c3aed", "#0891b2", "#10b981", "#f59e0b", "#f43f5e", "#60a5fa"]
    fig = go.Figure()
    for i, (ccy, rates) in enumerate(HIST_RATE.items()):
        fig.add_trace(go.Scatter(y=rates, x=list(range(len(rates))), mode="lines+markers", name=ccy, line=dict(color=palette[i % len(palette)], width=2.5), marker=dict(size=5)))
    fig.update_layout(height=360, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1", family="Inter"), xaxis=dict(title="Période", gridcolor="rgba(255,255,255,.04)", linecolor="rgba(255,255,255,.06)", tickfont=dict(size=11)), yaxis=dict(title="Taux (%)", gridcolor="rgba(255,255,255,.04)", linecolor="rgba(255,255,255,.06)", tickfont=dict(size=11)), legend=dict(bgcolor="rgba(13,20,36,.9)", bordercolor="rgba(255,255,255,.06)", borderwidth=1, font=dict(size=12)), hovermode="x unified", margin=dict(l=8, r=8, t=8, b=8))
    st.plotly_chart(fig, use_container_width=True)

# -------------------------
# TAB — SENTIMENT / KPI
# -------------------------
with tab_sentiment:
    st.markdown('<div style="font-weight:700;color:#cbd5e1;margin-bottom:8px;">Core FX Indicators</div>', unsafe_allow_html=True)

    fx_items = list(FX_RATES.items())[:kpi_count]
    cols_per_row = 3
    rows_fx = [fx_items[i:i+cols_per_row] for i in range(0, len(fx_items), cols_per_row)]

    for row in rows_fx:
        cols = st.columns(len(row))
        for col, (pair, info) in zip(cols, row):
            rate = info.get("rate", 0) or 0
            chg  = info.get("chg",  0) or 0.0
            color = "#10b981" if chg >= 0 else "#f43f5e"
            hist = [round(rate * (0.994 + i * 0.0015 + (0.001 if i % 3 == 0 else 0)), 6) for i in range(16)]
            with col:
                st.markdown(f"""
                <div class="kpi">
                  <div style="font-size:11px;color:#cbd5e1;font-weight:700;">{pair}</div>
                  <div style="font-family:JetBrains Mono;font-size:20px;font-weight:800;color:#fff;margin-top:6px;">{rate:.4f}</div>
                  <div style="margin-top:6px;">{delta_html(chg)}</div>
                </div>
                """, unsafe_allow_html=True)
                st.plotly_chart(sparkline(hist, color=color), use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div style="height:18px;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-weight:700;color:#cbd5e1;margin-bottom:8px;">Market Assets Snapshot</div>', unsafe_allow_html=True)

    asset_defs = [("VIX", "🌊", "VIX"), ("WTI_CRUDE", "🛢", "WTI Crude"), ("US_500", "📈", "S&P 500"), ("GOLD", "✦", "Gold Spot")]
    acols = st.columns(4)
    for col, (key, icon, label) in zip(acols, asset_defs):
        a = MARKET_ASSETS.get(key, {"price": "—", "chg": 0})
        price = a.get("price") or "—"
        chg   = a.get("chg", 0) or 0
        with col:
            st.markdown(f"""
            <div class="kpi">
              <div style="font-size:12px;color:#cbd5e1;">{label}</div>
              <div style="font-family:JetBrains Mono;font-size:18px;font-weight:800;color:#fff;margin-top:6px;">{price}</div>
              <div style="margin-top:6px;">{delta_html(chg)}</div>
            </div>
            """, unsafe_allow_html=True)

# -------------------------
# TAB — COMPARISON
# -------------------------
with tab_compare:
    st.markdown('<div style="font-weight:700;color:#cbd5e1;margin-bottom:8px;">Comparaison FX & Signal Prédictif</div>', unsafe_allow_html=True)

    ccy_list = list(MACRO.keys())
    c1, c2 = st.columns(2)
    with c1:
        base_ccy  = st.selectbox("Devise Long (Base)", ccy_list, index=min(6, len(ccy_list)-1))
    with c2:
        quote_ccy = st.selectbox("Devise Short (Contrepartie)", ccy_list, index=0)

    if base_ccy == quote_ccy:
        st.markdown('<div style="background:#2b2f36;padding:10px;border-radius:8px;color:#f59e0b;">⚠ Sélectionnez deux devises distinctes.</div>', unsafe_allow_html=True)
    else:
        b_data, q_data = MACRO.get(base_ccy, {}), MACRO.get(quote_ccy, {})
        spreads = compute_spreads(b_data, q_data)
        df_comp = build_comparison_table(base_ccy, quote_ccy, b_data, q_data, spreads)
        st.dataframe(df_comp, use_container_width=True)

        regime_tuple = regime_weights("Automatique", auto_sentiment)
        wti_bull = MARKET_ASSETS.get("WTI_CRUDE", {}).get("chg", 0) > 0
        wti_bonus = wti_adjustment(base_ccy, quote_ccy, wti_bull)

        expected_move = (spreads[2] * regime_tuple[1]) + (spreads[1] * regime_tuple[2]) + (spreads[0] * regime_tuple[3]) + wti_bonus
        score_pct = normalize_score(expected_move)

        st.markdown('<div style="background:linear-gradient(180deg,var(--panel),var(--panel-2));padding:16px;border-radius:12px;border:1px solid var(--border);">', unsafe_allow_html=True)
        if score_pct >= 50:
            st.markdown(f'<div style="font-size:20px;font-weight:800;color:#10b981;">BULLISH — {score_pct}%</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="height:10px;background:rgba(255,255,255,0.03);border-radius:999px;margin-top:8px;"><div style="width:{score_pct}%;height:100%;background:linear-gradient(90deg,#10b981,#34d399);border-radius:999px;"></div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="font-size:20px;font-weight:800;color:#f43f5e;">BEARISH — {100-score_pct}%</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="height:10px;background:rgba(255,255,255,0.03);border-radius:999px;margin-top:8px;"><div style="width:{100-score_pct}%;height:100%;background:linear-gradient(90deg,#f43f5e,#fb7185);border-radius:999px;"></div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# TAB — COMMODITIES / INTERMARKET (RateProbability)
# -------------------------
RATEPROB_CACHE = os.path.join(os.path.dirname(__file__), "rateprob_cache.json")
RATEPROB_URL = "https://rateprobability.com"

def _load_rateprob_cache():
    try:
        with open(RATEPROB_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"ts": None, "data": []}

def _save_rateprob_cache(data):
    try:
        payload = {"ts": datetime.utcnow().isoformat() + "Z", "data": data}
        with open(RATEPROB_CACHE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def fetch_rateprobability(force=False, ttl_seconds=600):
    cache = _load_rateprob_cache()
    if not force and cache.get("ts"):
        try:
            age = (datetime.utcnow() - datetime.fromisoformat(cache["ts"].replace("Z", ""))).total_seconds()
            if age < ttl_seconds:
                return cache.get("data", []), cache.get("ts")
        except Exception:
            pass
    if BeautifulSoup is None:
        return cache.get("data", []), cache.get("ts")
    try:
        resp = requests.get(RATEPROB_URL, timeout=10, headers={"User-Agent": "fx-terminal/1.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        table = None
        for h in soup.find_all(["h1","h2","h3","h4","h5"]):
            txt = h.get_text(strip=True).lower()
            if "upcoming meeting" in txt or "upcoming meetings" in txt:
                table = h.find_next("table")
                if table:
                    break
        rows = []
        if table:
            first_tr = table.find("tr")
            if first_tr:
                headers = [th.get_text(strip=True) for th in first_tr.find_all(["th","td"])]
                if headers:
                    rows.append(headers)
            for tr in table.find_all("tr")[1:]:
                cols = [td.get_text(strip=True) for td in tr.find_all(["td","th"])]
                if cols:
                    rows.append(cols)
        else:
            for table in soup.find_all("table"):
                header_text = " ".join([th.get_text(strip=True).lower() for th in table.find_all("th")])
                if any(k in header_text for k in ["bank","probability","meeting","rate","implied"]):
                    first_tr = table.find("tr")
                    if first_tr:
                        headers = [th.get_text(strip=True) for th in first_tr.find_all(["th","td"])]
                        if headers:
                            rows.append(headers)
                    for tr in table.find_all("tr")[1:]:
                        cols = [td.get_text(strip=True) for td in tr.find_all(["td","th"])]
                        if cols:
                            rows.append(cols)
                    break
        if rows:
            _save_rateprob_cache(rows)
            return rows, datetime.utcnow().isoformat() + "Z"
        return cache.get("data", []), cache.get("ts")
    except Exception:
        return cache.get("data", []), cache.get("ts")

with tab_intermarket:
    st.markdown('<div style="font-weight:700;color:#cbd5e1;margin-bottom:8px;">Intermarket Analytics & Commodities</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    gold = MARKET_ASSETS.get("GOLD", {"price": None, "chg": None})
    wti = MARKET_ASSETS.get("WTI_CRUDE", {"price": None, "chg": None})
    sp500 = MARKET_ASSETS.get("US_500", {"price": None, "chg": None})
    cols[0].markdown(f"<div class='kpi'><div style='font-size:12px;color:#cbd5e1;'>Gold Spot</div><div style='font-weight:800;font-family:JetBrains Mono;font-size:18px;margin-top:6px;color:#fff;'>{gold.get('price')}</div></div>", unsafe_allow_html=True)
    cols[1].markdown(f"<div class='kpi'><div style='font-size:12px;color:#cbd5e1;'>WTI Crude</div><div style='font-weight:800;font-family:JetBrains Mono;font-size:18px;margin-top:6px;color:#fff;'>{wti.get('price')}</div></div>", unsafe_allow_html=True)
    cols[2].markdown(f"<div class='kpi'><div style='font-size:12px;color:#cbd5e1;'>S&P 500</div><div style='font-weight:800;font-family:JetBrains Mono;font-size:18px;margin-top:6px;color:#fff;'>{sp500.get('price')}</div></div>", unsafe_allow_html=True)

    st.markdown("#### Market-implied Upcoming Meetings (RateProbability)")
    rp_force = st.button("Forcer refresh RateProbability")
    rows, ts = fetch_rateprobability(force=rp_force)
    if not rows:
        st.info("Impossible de récupérer RateProbability — affichage du cache si disponible.")
    else:
        st.markdown(f"*Dernière récupération: {ts}*")
        with st.container():
            st.markdown('<div style="padding:8px;">', unsafe_allow_html=True)
            if isinstance(rows, list) and rows and all(isinstance(r, list) for r in rows):
                headers = rows[0]
                data_rows = rows[1:]
                try:
                    df = pd.DataFrame(data_rows, columns=headers)
                except Exception:
                    df = pd.DataFrame(data_rows)
                prob_col = next((c for c in df.columns if "prob" in c.lower()), None)
                if prob_col:
                    def parse_pct(x):
                        try:
                            return float(str(x).replace("%","").strip())
                        except Exception:
                            return None
                    df["_prob_pct"] = df[prob_col].apply(parse_pct)
                else:
                    df["_prob_pct"] = None
                st.dataframe(df, use_container_width=True)
            else:
                st.table(rows)
            st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# TAB — INSIGHTS
# -------------------------
with tab_insights:
    st.markdown('<div style="font-weight:700;color:#cbd5e1;margin-bottom:8px;">Insights & Recommandations</div>', unsafe_allow_html=True)
    regime_tuple = regime_weights("Automatique", auto_sentiment)
    wti_bull = MARKET_ASSETS.get("WTI_CRUDE", {}).get("chg", 0) > 0
    ranked = rank_all_pairs(regime_tuple, wti_bull)

    top_bull = [r for r in ranked if r["score_pct"] >= 50][:3]
    top_bear = sorted(ranked, key=lambda x: x["score_pct"])[:3]

    cols = st.columns(2)
    with cols[0]:
        if not top_bull:
            st.info("Aucune paire bullish détectée.")
        for item in top_bull:
            pct = item.get("score_pct", 0)
            raw = item.get("raw", 0)
            st.markdown(f"<div style='padding:10px;border-radius:10px;background:linear-gradient(180deg,var(--panel),var(--panel-2));margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;color:#fff;'><div><div style='font-weight:800;font-family:JetBrains Mono;'>{item['pair']}</div><div style='color:#cbd5e1;font-size:12px;'>raw: {raw:.2f}</div></div><div style='font-weight:800;color:#10b981;'>{pct}%</div></div>", unsafe_allow_html=True)
    with cols[1]:
        if not top_bear:
            st.info("Aucune paire bearish détectée.")
        for item in top_bear:
            pct = item.get("score_pct", 0)
            raw = item.get("raw", 0)
            st.markdown(f"<div style='padding:10px;border-radius:10px;background:linear-gradient(180deg,var(--panel),var(--panel-2));margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;color:#fff;'><div><div style='font-weight:800;font-family:JetBrains Mono;'>{item['pair']}</div><div style='color:#cbd5e1;font-size:12px;'>raw: {raw:.2f}</div></div><div style='font-weight:800;color:#f43f5e;'>{pct}%</div></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 📅 Catalyseurs à venir (sélection rapide)")
    catalysts = [
        {"time": "2026-05-20 13:30 UTC", "event": "US Nonfarm Payrolls (NFP)", "impact": "High", "pairs": ["USD/*"]},
        {"time": "2026-05-21 08:00 UTC", "event": "ECB Rate Decision", "impact": "High", "pairs": ["EUR/*"]},
        {"time": "2026-05-22 02:00 UTC", "event": "BoC Rate Statement", "impact": "Medium", "pairs": ["CAD/*"]},
    ]
    for c in catalysts:
        st.markdown(f"<div style='padding:12px;border-radius:10px;background:linear-gradient(180deg,var(--panel),var(--panel-2));margin-bottom:8px;color:#fff;'><div style='font-weight:700;'>{c['event']}</div><div style='color:#cbd5e1;font-family:JetBrains Mono;margin-top:6px;'>{c['time']} · Pairs: {', '.join(c['pairs'])}</div></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 📰 News & Catalyseurs (flux)")
    articles = fetch_news(limit=6)
    if articles:
        for i, a in enumerate(articles, 1):
            title = a.get("title") or "Untitled"
            src = a.get("source") or ""
            ts = (a.get("publishedAt") or "")[:19].replace("T", " ")
            url = a.get("url") or "#"
            st.markdown(f"<div style='padding:10px;border-bottom:1px solid rgba(255,255,255,0.03);color:#fff;'><div style='font-weight:700;'><a href='{url}' target='_blank' style='color:#38bdf8;text-decoration:none;'>{title}</a></div><div style='color:#cbd5e1;font-family:JetBrains Mono;margin-top:6px;'>{src} · {ts}</div></div>", unsafe_allow_html=True)
    else:
        st.info("Aucune news disponible — vérifie la variable d'environnement NEWS_API_KEY ou le cache local.")

# -------------------------
# TAB — LOGS
# -------------------------
with tab_logs:
    st.markdown('<div style="font-weight:700;color:#cbd5e1;margin-bottom:8px;">System Logs</div>', unsafe_allow_html=True)
    try:
        logs = load_update_log()
    except Exception:
        logs = []
    if logs:
        for entry in logs:
            status_cls = "log-ok" if entry.get("status") == "success" else "log-fail"
            st.markdown(f"<div style='font-family:JetBrains Mono;color:#cbd5e1;padding:8px;border-bottom:1px solid rgba(255,255,255,0.03);'><span style='color:#94a3b8;width:160px;display:inline-block;'>{entry.get('ts')}</span> {entry.get('session')} · {entry.get('trigger')} · <span style='color:{('#10b981' if entry.get('status')=='success' else '#f43f5e')};'>{entry.get('status')}</span></div>", unsafe_allow_html=True)
    else:
        st.info("Aucun log disponible.")

# -------------------------
# Footer
# -------------------------
st.markdown("---")
st.markdown(
    f"<div style='display:flex;justify-content:space-between;align-items:center;'><div style='color:#cbd5e1;'>Données: Yahoo Finance (yfinance), sources macro locales; modèle: indicateurs fondamentaux pondérés.</div><div style='color:#cbd5e1;'>Dernière mise à jour: {utc_now}</div></div>",
    unsafe_allow_html=True,
)
