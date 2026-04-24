"""
FX Fundamental Dashboard  —  v4.0
Professional design · No emojis · Auto-update London 17:00 + NY 22:00 UTC
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import random
from datetime import datetime, timezone

from data import (
    MACRO, RATE_EXP, FX_RATES, CALENDAR, NEWS,
    MONTHS, HIST_CPI, HIST_RATE, HIST_UNEM,
    start_scheduler, save_snapshot,
    load_history_from_db, load_update_log, get_last_update,
    init_db, score_meta,
)

# ── Harmonized semantic colors ────────────────────────────────────
COLOR_POSITIVE      = "#10b981"   # emerald-500
COLOR_NEGATIVE      = "#f43f5e"   # rose-500
COLOR_WARNING       = "#f59e0b"   # amber-500
COLOR_NEUTRAL       = "#64748b"   # slate-500
COLOR_PRIMARY       = "#4f46e5"   # indigo-600
COLOR_PRIMARY_HOVER = "#4338ca"
COLOR_BG_ACCENT     = "#eef2ff"   # indigo-50



# ── Start background scheduler once ──────────────────────────────
init_db()
start_scheduler()

# ─────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FX Dashboard",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: #0f172a;
}
.stApp { background: #f8fafc; }
.block-container { padding: 1.8rem 2.8rem 3rem !important; max-width: 1600px !important; }

/* Sidebar complètement cachée */
section[data-testid="stSidebar"],
[data-testid="collapsedControl"],
button[data-testid="baseButton-headerNoPadding"] {
    display: none !important;
}

#MainMenu, footer, header, .stDeployButton, .stAppToolbar { display: none !important; }
/* Force white background on all containers */
.stMainBlockContainer, .main .block-container { background: #f8fafc !important; }
[data-testid="stAppViewContainer"] { background: #f8fafc !important; }

div[data-testid="metric-container"] {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 14px 18px !important;
    transition: all 0.2s ease;
    box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}
div[data-testid="metric-container"]:hover {
    border-color: #cbd5e1;
    box-shadow: 0 4px 8px rgba(0,0,0,0.04);
}
div[data-testid="metric-container"] label {
    font-size: 9.5px !important;
    color: #475569 !important;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-weight: 600;
}
div[data-testid="stMetricValue"] {
    font-size: 19px !important;
    font-weight: 700 !important;
    color: #0f172a !important;
}
div[data-testid="stMetricDelta"] { font-size: 11px !important; }

.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #e2e8f0 !important;
    gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #475569 !important;
    font-size: 11.5px !important;
    font-weight: 500 !important;
    letter-spacing: 0.04em !important;
    padding: 10px 20px !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    transition: color 0.15s ease !important;
}
.stTabs [aria-selected="true"] {
    color: #4f46e5 !important;
    border-bottom-color: #4f46e5 !important;
    font-weight: 600 !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.2rem !important; }

.stSelectbox > div > div,
.stMultiSelect > div {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    font-size: 12.5px !important;
    color: #0f172a !important;
}
.stRadio > div { gap: 6px !important; }
.stRadio label {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    padding: 5px 13px !important;
    font-size: 11.5px !important;
    color: #334155 !important;
    cursor: pointer;
    transition: all 0.15s ease;
}
.stRadio label:has(input:checked) {
    background: #eef2ff !important;
    border-color: #4f46e5 !important;
    color: #4f46e5 !important;
}
.stNumberInput input, .stTextInput input {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    color: #0f172a !important;
    font-size: 13px !important;
}
.stSlider [data-baseweb="slider"] > div > div > div { background: #4f46e5 !important; }
.stButton button {
    background: #4f46e5 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}
.stButton button:hover {
    background: #4338ca !important;
    transform: translateY(-1px);
    box-shadow: 0 2px 6px rgba(79,70,229,0.25);
}
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #e2e8f0;
}
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #f1f5f9; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
hr { border-color: #0f172a !important; margin: 0.8rem 0 !important; }
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(5px); }
    to   { opacity: 1; transform: translateY(0); }
}
.block-container > div > div > div { animation: fadeIn 0.25s ease; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────
CURRENCIES = list(MACRO.keys())

def rgba(hex_color, a=1.0):
    try:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        return f"rgba({r},{g},{b},{a})"
    except:
        return hex_color

def chart_layout(title="", h=300, margin=None):
    m = margin or dict(t=36, b=28, l=32, r=12)
    return dict(
        title=dict(text=title, font=dict(size=12, color="#0f172a", family="Inter"), x=0, y=0.98),
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        font=dict(color="#334155", family="Inter", size=11),
        margin=m,
        height=h,
        xaxis=dict(gridcolor="#f1f5f9", zeroline=False, linecolor="#e2e8f0",
                   tickfont=dict(size=10, color="#475569")),
        yaxis=dict(gridcolor="#f1f5f9", zeroline=False, linecolor="#e2e8f0",
                   tickfont=dict(size=10, color="#475569")),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10, color="#0f172a")),
        hoverlabel=dict(bgcolor="#ffffff", bordercolor="#cbd5e1",
                        font=dict(size=11, color="#0f172a", family="Inter")),
    )


def section(label):
    st.markdown(
        f'<div style="font-size:9.5px;font-weight:600;color:#0f172a;'
        f'text-transform:uppercase;letter-spacing:.12em;'
        f'margin:20px 0 10px;padding-bottom:6px;'
        f'border-bottom:1px solid #e2e8f0;">{label}</div>',
        unsafe_allow_html=True
    )

def pill(label, color):
    return (
        f'<span style="background:{rgba(color,0.12)};color:{color};'
        f'font-size:9.5px;font-weight:600;padding:2px 9px;'
        f'border-radius:4px;border:1px solid {rgba(color,0.25)};'
        f'letter-spacing:.04em;">{label}</span>'
    )

def card_start(border_color="#e2e8f0", bg="#ffffff", pad="16px 18px"):
    return (f'<div style="background:{bg};border:1px solid {border_color};'
            f'border-radius:9px;padding:{pad};margin-bottom:10px;'
            f'transition:border-color 0.2s ease;">')

def card_end():
    return '</div>'

def bias_badge(score):
    col, bg, lbl = score_meta(score)
    return f'<span style="background:{bg};color:{col};border:1px solid {rgba(col,0.3)};font-size:9px;font-weight:700;padding:2px 10px;border-radius:3px;letter-spacing:.08em;">{lbl}</span>'

def strength_bar(val, max_val, color):
    pct = max(3, min(100, int(abs(val)/max_val*100)))
    return (f'<div style="background:#f3f4f6;border-radius:2px;height:3px;margin-top:6px;overflow:hidden;">'
            f'<div style="width:{pct}%;height:3px;background:{color};border-radius:2px;'
            f'transition:width 0.4s ease;"></div></div>')

def hline(fig, y, color, label=""):
    fig.add_hline(y=y, line_dash="dash", line_color=color,
                  annotation_text=label, annotation_font_color=color,
                  annotation_font_size=9)


# ─────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:4px 0 18px;">
      <div style="font-size:12px;font-weight:700;color:#4f46e5;
           letter-spacing:.1em;text-transform:uppercase;">FX Dashboard</div>
      <div style="font-size:9.5px;color:#d1d5db;margin-top:3px;
           letter-spacing:.08em;text-transform:uppercase;">Fundamental Analysis</div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio("", [
        "Overview",
        "Currencies",
        "Calendar",
        "News",
        "Insights",
        "Risk Sentiment",
        "Comparison",
        "Trade Simulator",
        "System",
    ], label_visibility="collapsed")

    st.markdown('<div style="height:1px;background:#e2e8f0;margin:12px 0;"></div>', unsafe_allow_html=True)

    sel_ccy = st.multiselect("Currencies", CURRENCIES, default=CURRENCIES)

    st.markdown('<div style="height:1px;background:#e2e8f0;margin:12px 0;"></div>', unsafe_allow_html=True)

    last = get_last_update()
    now_utc = datetime.now(timezone.utc)
    next_ldn = now_utc.replace(hour=17, minute=0, second=0, microsecond=0)
    next_ny  = now_utc.replace(hour=22, minute=0, second=0, microsecond=0)
    if now_utc.hour >= 17: next_ldn = next_ldn + __import__("datetime").timedelta(days=1)
    if now_utc.hour >= 22: next_ny  = next_ny  + __import__("datetime").timedelta(days=1)

    st.markdown(f"""
    <div style="font-size:9.5px;color:#d1d5db;line-height:2.2;">
      <div style="color:#0f172a;font-weight:600;margin-bottom:4px;">Auto-Update Schedule</div>
      <div>London close  <span style="color:#475569;">17:00 UTC</span></div>
      <div>NY close  <span style="color:#475569;">22:00 UTC</span></div>
      <div style="margin-top:6px;">Last update</div>
      <div style="color:#475569;">{last.get('ts','—')}</div>
      <div style="margin-top:6px;">Session: <span style="color:#475569;">{last.get('session','—')}</span></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="height:1px;background:#e2e8f0;margin:12px 0;"></div>', unsafe_allow_html=True)
    if st.button("Force snapshot now", use_container_width=True):
        save_snapshot("manual")
        st.success("Snapshot saved.")

    st.markdown(f"""
    <div style="font-size:9px;color:#d1d5db;margin-top:10px;line-height:1.8;">
      {now_utc.strftime('%d %b %Y  %H:%M UTC')}<br>
      IMF WEO · TradingEconomics<br>
      ECB · BoE · BoJ · Fed · RBA<br>
      <span style="margin-top:6px;display:block;">
        For informational purposes only.<br>Not financial advice.
      </span>
    </div>
    """, unsafe_allow_html=True)

codes = [c for c in CURRENCIES if c in sel_ccy]


# ═════════════════════════════════════════════════════════════════
# OVERVIEW
# ═════════════════════════════════════════════════════════════════
if page == "Overview":
    st.markdown("""
    <div style="margin-bottom:22px;">
      <div style="font-size:20px;font-weight:700;color:#0f172a;letter-spacing:-.01em;">
        Macro Overview
      </div>
      <div style="font-size:11px;color:#0f172a;margin-top:4px;">
        Week of 21–30 April 2026  ·  Monetary policy &amp; macro fundamentals
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#fefce8;border:1px solid #fde047;border-left:3px solid #eab308;border-radius:12px;padding:10px 16px;margin-bottom:22px;font-size:11px;color:#854d0e;line-height:1.7;font-weight:500;">
      <b style="color:#b45309;">Market Alert</b>  —  US-Iran talks collapsed  ·
      BoJ meeting Apr 28 (hike expected, 78% probability)  ·
      UK CPI 3.3%  ·  NZD CPI beat 3.1%  ·  DXY 98.5  ·  WTI -12% week
    </div>
    """, unsafe_allow_html=True)

    # ── Strength ranking ──────────────────────────────────────────
    section("Currency Strength Ranking")
    cols_s = st.columns(len(codes))
    ordered = sorted([c for c in codes], key=lambda c: MACRO[c]["score"], reverse=True)
    for i, c in enumerate(ordered):
        d = MACRO[c]
        col, bg, lbl = score_meta(d["score"])
        fill = max(5, min(100, int((d["score"]+3)/6*100)))
        with cols_s[i]:
            st.markdown(
                f'{card_start(rgba(col,0.2), bg)}'
                f'<div style="font-size:13px;font-weight:700;color:#0f172a;margin-bottom:3px;">{c}</div>'
                f'<div style="font-size:8.5px;color:{col};font-weight:700;text-transform:uppercase;letter-spacing:.08em;">{lbl}</div>'
                f'{strength_bar(d["score"], 3, col)}'
                f'<div style="font-size:9.5px;color:#0f172a;margin-top:6px;">{d["rate"]}%  ·  {d["bias"][:14]}</div>'
                f'{card_end()}',
                unsafe_allow_html=True
            )

    # ── Key metrics ───────────────────────────────────────────────
    section("Global Indicators")
    m1,m2,m3,m4,m5,m6 = st.columns(6)
    with m1: st.metric("DXY Index",   "98.5",   "+0.18%")
    with m2: st.metric("WTI Crude",   "$82.3",  "-11.5% wk")
    with m3: st.metric("Gold XAU",    "$3,320", "+0.8%")
    with m4: st.metric("VIX",         "18.4",   "-2.1")
    with m5: st.metric("US 10Y",      "4.52%",  "+3bps")
    with m6: st.metric("EUR/USD",     "1.1793", "-0.12%")

    # ── Charts ────────────────────────────────────────────────────
    section("Central Bank Rates  &  CPI Inflation")
    cg1, cg2 = st.columns(2)

    with cg1:
        fig = go.Figure()
        vals  = [MACRO[c]["rate"] for c in codes]
        bcolors = [MACRO[c]["color"] for c in codes]
        fig.add_trace(go.Bar(
            x=codes, y=vals,
            marker=dict(color=bcolors, line=dict(width=0)),
            text=[f"{v}%" for v in vals],
            textposition="outside",
            textfont=dict(size=10, color="#334155"),
            hovertemplate="%{x}: %{y:.2f}%<extra></extra>",
        ))
        fig.update_layout(**chart_layout("Central bank rates (%)", 268))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    with cg2:
        fig2 = go.Figure()
        infl  = [MACRO[c]["cpi"] for c in codes]
        bc2   = [(COLOR_NEGATIVE if v>3 else "#f59e0b" if v>2 else COLOR_POSITIVE) for v in infl]
        fig2.add_trace(go.Bar(
            x=codes, y=infl,
            marker=dict(color=bc2, line=dict(width=0)),
            text=[f"{v}%" for v in infl],
            textposition="outside",
            textfont=dict(size=10, color="#334155"),
            hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
        ))
        hline(fig2, 2.0, COLOR_PRIMARY, "2% target")
        fig2.update_layout(**chart_layout("CPI Inflation (%)", 268))
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})

    # ── FX Grid ───────────────────────────────────────────────────
    section("FX Rates")
    fx_cols = st.columns(4)
    for i, (pair, d) in enumerate(list(FX_RATES.items())[:12]):
        chg  = d["chg"];  wchg = d["wchg"]
        cc   = COLOR_POSITIVE if chg  > 0 else COLOR_NEGATIVE
        wcc  = COLOR_POSITIVE if wchg > 0 else COLOR_NEGATIVE
        with fx_cols[i%4]:
            st.markdown(
                f'{card_start()}'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<div><div style="font-size:12px;font-weight:700;color:#0f172a;">{pair}</div>'
                f'<div style="font-size:9.5px;color:{wcc};margin-top:2px;">{wchg:+.1f}% wk</div></div>'
                f'<div style="text-align:right;">'
                f'<div style="font-size:13px;font-weight:700;color:#0f172a;">{d["rate"]}</div>'
                f'<div style="font-size:10px;color:{cc};">{chg:+.2f}%</div></div></div>'
                f'{card_end()}',
                unsafe_allow_html=True
            )

    # ── Key Events ────────────────────────────────────────────────
    section("Key Events This Week")
    high_ev = [e for e in CALENDAR if e["imp"]=="high"][:4]
    ev_cols = st.columns(4)
    for i, e in enumerate(high_ev):
        ccy_col = MACRO.get(e["ccy"],{}).get("color","#1e293b")
        is_cb   = any(x in e["event"] for x in ["BoJ","BoE","FOMC","Fed","ECB","RBA","RBNZ","BoC"])
        bg_ev   = "#fff7ed" if is_cb else "#ffffff"
        brd_ev  = "#78350f" if is_cb else "#e2e8f0"
        with ev_cols[i]:
            st.markdown(
                f'<div style="background:{bg_ev};border:1px solid {brd_ev};'
                f'border-radius:8px;padding:13px;">'
                f'<div style="font-size:9px;color:#0f172a;margin-bottom:5px;">'
                f'{e["date"]}  ·  {e["time"]} UTC</div>'
                f'<div style="font-size:11.5px;font-weight:600;color:#e2e8f0;'
                f'line-height:1.4;margin-bottom:7px;">{e["event"]}</div>'
                f'<div style="display:flex;justify-content:space-between;">'
                f'<span style="font-size:9.5px;color:#0f172a;">Prev: {e["prev"]}</span>'
                f'<span style="font-size:9.5px;color:{ccy_col};font-weight:600;">'
                f'Fcst: {e["fore"]}</span></div></div>',
                unsafe_allow_html=True
            )


# ═════════════════════════════════════════════════════════════════
# CURRENCIES
# ═════════════════════════════════════════════════════════════════
elif page == "Currencies":
    st.markdown('<div style="font-size:20px;font-weight:700;color:#e2e8f0;margin-bottom:18px;">Currency Analysis</div>', unsafe_allow_html=True)

    sel = st.selectbox("", codes, format_func=lambda c: f"{c}  —  {MACRO[c]['name']}", label_visibility="collapsed")
    d   = MACRO[sel]
    exp = RATE_EXP[sel]
    col, bg, lbl = score_meta(d["score"])

    # Header card
    st.markdown(
        f'<div style="background:linear-gradient(120deg,#ffffff 60%,{bg} 100%);'
        f'border:1px solid {rgba(col,0.2)};border-radius:10px;'
        f'padding:20px 24px;margin-bottom:18px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
        f'<div>'
        f'<div style="font-size:18px;font-weight:700;color:#0f172a;">{sel}  —  {d["name"]}</div>'
        f'<div style="font-size:10.5px;color:#0f172a;margin-top:5px;line-height:2;">'
        f'Central bank: <b style="color:#475569;">{d["cb"]}</b>'
        f'&nbsp;&nbsp;·&nbsp;&nbsp;Next meeting: <b style="color:#475569;">{d["next_mtg"]}</b>'
        f'&nbsp;&nbsp;·&nbsp;&nbsp;<span style="color:{d["color"]};">{d["updated"]}</span>'
        f'</div>'
        f'</div>'
        f'<div style="text-align:right;">'
        f'<div style="font-size:30px;font-weight:800;color:{col};line-height:1;">{d["rate"]}%</div>'
        f'<div style="font-size:9.5px;color:{col};text-transform:uppercase;'
        f'letter-spacing:.08em;margin-top:5px;">{d["bias"]}</div>'
        f'<div style="margin-top:7px;">{bias_badge(d["score"])}</div>'
        f'</div>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    # Metrics
    m1,m2,m3,m4,m5,m6 = st.columns(6)
    with m1: st.metric("GDP 2026", f"{d['gdp']}%",   f"{d['gdp']-d['gdp_prev']:+.1f}%")
    with m2: st.metric("CPI",      f"{d['cpi']}%",   f"{d['cpi']-d['cpi_prev']:+.1f}%",  delta_color="inverse")
    with m3: st.metric("Unemployment", f"{d['unem']}%", f"{d['unem']-d['unem_prev']:+.1f}%", delta_color="inverse")
    with m4: st.metric("Wages",    f"{d['wages']}%",  None)
    with m5: st.metric("Retail MoM", f"{d['retail']}%", None)
    with m6: st.metric("Core CPI", f"{d['core_cpi']}%", None)

    st.markdown("<br>", unsafe_allow_html=True)
    cl, cr = st.columns([3,2])

    with cl:
        ta, tb, tc = st.tabs(["Inflation", "CB Rate", "Unemployment"])
        cfgs = [
            (ta, HIST_CPI,  d["color"],  f"CPI Inflation — {sel}",         "2% target", 2.0, COLOR_PRIMARY),
            (tb, HIST_RATE, COLOR_POSITIVE,   f"Central Bank Rate — {sel}",      None, None, None),
            (tc, HIST_UNEM, "#f59e0b",   f"Unemployment Rate — {sel}",     None, None, None),
        ]
        for tab, hist, color, title, ann, ann_y, ann_c in cfgs:
            with tab:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=MONTHS, y=hist[sel],
                    mode="lines+markers",
                    line=dict(color=color, width=2),
                    fill="tozeroy", fillcolor=rgba(color, 0.06),
                    marker=dict(size=5, color=color),
                    hovertemplate="%{x}: %{y:.2f}%<extra></extra>",
                ))
                if ann: hline(fig, ann_y, ann_c, ann)
                fig.update_layout(**chart_layout(title, 248))
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    with cr:
        section("Recent Drivers")
        for n in d["news"]:
            st.markdown(
                f'<div style="border-left:2px solid #e2e8f0;padding:8px 12px;'
                f'margin-bottom:6px;font-size:11.5px;color:#475569;line-height:1.55;">'
                f'{n}</div>',
                unsafe_allow_html=True
            )
        section("Fundamental View")
        st.markdown(
            f'<div style="background:{bg};border:1px solid {rgba(col,0.15)};'
            f'border-radius:8px;padding:13px 15px;font-size:11.5px;'
            f'color:#475569;line-height:1.7;">{d["view"]}</div>',
            unsafe_allow_html=True
        )
        section("Rate Expectations (OIS)")
        ois = exp["ois"]
        for tenor, val in ois.items():
            delta = round(val - d["rate"], 2)
            dc = COLOR_POSITIVE if delta > 0 else COLOR_NEGATIVE if delta < 0 else "#1e293b"
            st.markdown(
                f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:7px;'
                f'padding:8px 12px;margin-bottom:5px;display:flex;justify-content:space-between;">'
                f'<span style="font-size:11px;color:#64748b;">OIS {tenor}</span>'
                f'<span style="font-size:11.5px;font-weight:600;color:#0f172a;">'
                f'{val:.2f}%  <span style="color:{dc};font-size:10px;">({delta:+.2f}%)</span></span>'
                f'</div>',
                unsafe_allow_html=True
            )
        section("Related Pairs")
        for pair, pd2 in FX_RATES.items():
            if sel in pair:
                chg = pd2["chg"]
                cc  = COLOR_POSITIVE if chg > 0 else COLOR_NEGATIVE
                st.markdown(
                    f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:7px;'
                    f'padding:8px 12px;margin-bottom:5px;display:flex;justify-content:space-between;">'
                    f'<span style="font-size:12px;font-weight:600;color:#0f172a;">{pair}</span>'
                    f'<span style="font-size:12px;color:{cc};">{pd2["rate"]}  {chg:+.2f}%</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )


# ═════════════════════════════════════════════════════════════════
# CALENDAR
# ═════════════════════════════════════════════════════════════════
elif page == "Calendar":
    st.markdown('<div style="font-size:20px;font-weight:700;color:#e2e8f0;margin-bottom:6px;">Economic Calendar</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:11px;color:#0f172a;margin-bottom:18px;">23 April — 30 April 2026</div>', unsafe_allow_html=True)

    cf1, cf2 = st.columns([2,1])
    with cf1: f_imp = st.radio("Impact", ["All","High only","Medium+"], horizontal=True)
    with cf2: f_ccy = st.selectbox("Currency", ["All"]+CURRENCIES)

    events = CALENDAR[:]
    if f_imp == "High only":  events = [e for e in events if e["imp"]=="high"]
    elif f_imp == "Medium+":  events = [e for e in events if e["imp"] in ("high","medium")]
    if f_ccy != "All":        events = [e for e in events if e["ccy"]==f_ccy]

    imp_cfg = {
        "high":   (COLOR_NEGATIVE,"#fff1f2","#fca5a5"),
        "medium": ("#d97706","#0d0600","#78350f"),
        "low":    (COLOR_POSITIVE,"#ecfdf5","#6ee7b7"),
    }

    cur_date = None
    for ev in events:
        if ev["date"] != cur_date:
            cur_date = ev["date"]
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;margin:20px 0 8px;">'
                f'<div style="width:2px;height:16px;background:#4f46e5;border-radius:1px;"></div>'
                f'<span style="font-size:12px;font-weight:700;color:#0f172a;">{ev["date"]}</span>'
                f'<span style="font-size:10px;color:#0f172a;">({ev["day"]})</span>'
                f'</div>',
                unsafe_allow_html=True
            )

        col_imp, bg_imp, brd_imp = imp_cfg[ev["imp"]]
        ccy_col = MACRO.get(ev["ccy"],{}).get("color","#1e293b")
        has_act = bool(str(ev.get("act","")).strip())
        act_val = str(ev.get("act","")).strip()
        prev_v  = str(ev.get("prev","")).strip()
        fore_v  = str(ev.get("fore","")).strip()
        ev_text = str(ev.get("event","")).strip()
        time_v  = str(ev.get("time","")).strip()
        flag_v  = str(ev.get("flag","")).strip()
        ccy_v   = str(ev.get("ccy","")).strip()

        act_html = (f'<span style="background:#052e16;color:#10b981;'
                    f'font-size:9.5px;font-weight:700;padding:2px 8px;'
                    f'border-radius:3px;">ACT: {act_val}</span>') if has_act else ""

        html = (
            f'<div style="background:{bg_imp};border:1px solid {brd_imp};border-radius:8px;'
            f'padding:11px 16px;margin-bottom:5px;display:flex;align-items:center;gap:14px;">'
            f'<div style="min-width:52px;text-align:center;">'
            f'<div style="font-size:9px;color:{col_imp};font-weight:700;'
            f'text-transform:uppercase;letter-spacing:.06em;">{ev["imp"]}</div>'
            f'<div style="font-size:10.5px;color:#64748b;margin-top:2px;">{time_v}</div>'
            f'</div>'
            f'<div style="width:24px;font-size:9px;color:#0f172a;font-weight:600;">{flag_v}</div>'
            f'<div style="flex:1;">'
            f'<div style="font-size:12px;font-weight:600;color:#0f172a;">{ev_text}</div>'
            f'<div style="font-size:9.5px;color:{ccy_col};margin-top:2px;font-weight:600;">{ccy_v}</div>'
            f'</div>'
            f'<div style="text-align:right;min-width:170px;">'
            f'{act_html}'
            f'<div style="font-size:9.5px;color:#0f172a;margin-top:3px;">'
            f'Prev: <b style="color:#475569;">{prev_v}</b>'
            f'&nbsp;&#8594;&nbsp;'
            f'Fcst: <b style="color:{ccy_col};">{fore_v}</b>'
            f'</div></div></div>'
        )
        st.markdown(html, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════
# NEWS
# ═════════════════════════════════════════════════════════════════
elif page == "News":
    st.markdown('<div style="font-size:20px;font-weight:700;color:#e2e8f0;margin-bottom:18px;">Market News</div>', unsafe_allow_html=True)

    cats = ["All","Inflation","PMI","Sentiment","Central Bank","Geopolitics"]
    f_cat = st.radio("Category", cats, horizontal=True)
    filtered = [n for n in NEWS if f_cat=="All" or n["cat"]==f_cat]

    cat_colors = {
        "Inflation":    COLOR_NEGATIVE,
        "PMI":          COLOR_PRIMARY,
        "Central Bank": COLOR_PRIMARY,
        "Geopolitics":  "#f59e0b",
        "Sentiment":    COLOR_POSITIVE,
    }
    dir_colors = {"positive":COLOR_POSITIVE,"negative":COLOR_NEGATIVE,"mixed":"#f59e0b"}

    for n in filtered:
        cc  = cat_colors.get(n["cat"],"#1e293b")
        dc  = dir_colors.get(n["dir"],"#1e293b")
        ccy_pills = " ".join([
            f'<span style="background:{rgba(MACRO.get(c,{}).get("color","#1e293b"),0.12)};'
            f'color:{MACRO.get(c,{}).get("color","#1e293b")};'
            f'font-size:9px;font-weight:700;padding:2px 8px;border-radius:3px;">{c}</span>'
            for c in n["ccys"]
        ])
        st.markdown(
            f'<div style="background:#ffffff;border:1px solid #e2e8f0;'
            f'border-left:2px solid {cc};border-radius:8px;'
            f'padding:16px 18px;margin-bottom:10px;">'
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:center;margin-bottom:9px;">'
            f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">'
            f'<span style="background:{rgba(cc,0.1)};color:{cc};border:1px solid {rgba(cc,0.25)};'
            f'font-size:9px;font-weight:700;padding:2px 9px;border-radius:3px;'
            f'letter-spacing:.06em;">{n["cat"]}</span>'
            f'{ccy_pills}</div>'
            f'<span style="font-size:9.5px;color:#0f172a;white-space:nowrap;">{n["ts"]}</span>'
            f'</div>'
            f'<div style="font-size:13px;font-weight:600;color:#e2e8f0;'
            f'line-height:1.45;margin-bottom:8px;">{n["title"]}</div>'
            f'<div style="font-size:11.5px;color:#64748b;line-height:1.65;margin-bottom:10px;">{n["body"]}</div>'
            f'<div style="font-size:9.5px;color:#0f172a;">'
            f'Direction: <span style="color:{dc};font-weight:600;">{n["dir"].upper()}</span></div>'
            f'</div>',
            unsafe_allow_html=True
        )


# ═════════════════════════════════════════════════════════════════
# INSIGHTS
# ═════════════════════════════════════════════════════════════════
elif page == "Insights":
    st.markdown('<div style="font-size:20px;font-weight:700;color:#e2e8f0;margin-bottom:6px;">Fundamental Insights</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:11px;color:#0f172a;margin-bottom:20px;">Qualitative macro themes — week of 23 Apr 2026</div>', unsafe_allow_html=True)

    themes = [
        {"title":"Energy Shock — Middle East","color":"#f59e0b",
         "body":"Strait of Hormuz partially blocked. Net energy importers (Eurozone, Japan) most exposed. CPI acceleration driven by fuel costs across Europe.",
         "impact":"EUR negative  ·  JPY negative  ·  USD positive  ·  CAD ambiguous"},
        {"title":"Central Bank Divergence — Critical Week","color":COLOR_PRIMARY,
         "body":"BoJ poised to act Apr 28, BoE and Fed both on hold. Rate differential between USD and JPY narrowing for first time since 2022. Core theme of the week.",
         "impact":"JPY strongly positive  ·  GBP positive  ·  USD risk to downside"},
        {"title":"Persistent Inflation — UK &amp; NZD","color":COLOR_NEGATIVE,
         "body":"UK CPI 3.3% (services 4.5%) and NZD CPI 3.1% (beat). Both central banks constrained — hawkish bias underpins both currencies vs peers.",
         "impact":"GBP positive  ·  NZD positive"},
        {"title":"German Weakness — EUR Risk","color":"#1e293b",
         "body":"ZEW -17.2 and PMI Composite in contraction. Germany weighing on EUR sentiment. ECB cautious but market pricing some hike risk — a policy error could amplify weakness.",
         "impact":"EUR negative  ·  CHF positive (safe haven)"},
        {"title":"CHF &amp; JPY — Safe Haven Rotation","color":"#a855f7",
         "body":"Geopolitical uncertainty and US-Iran breakdown sustaining safe-haven demand. CHF structurally strong; JPY potential hawkish catalyst from BoJ.",
         "impact":"CHF positive  ·  JPY positive"},
        {"title":"AUD &amp; NZD — Commodity &amp; Rate Support","color":COLOR_POSITIVE,
         "body":"Gold, copper and soft commodities well-bid. China fiscal stimulus supporting terms-of-trade. Both RBA and RBNZ leaning hawkish. Risk-on sentiment favours both.",
         "impact":"AUD positive  ·  NZD positive"},
    ]

    for i in range(0, len(themes), 2):
        tc1, tc2 = st.columns(2)
        for col_idx, t in enumerate(themes[i:i+2]):
            col_w = tc1 if col_idx==0 else tc2
            with col_w:
                st.markdown(
                    f'<div style="background:#ffffff;border:1px solid {rgba(t["color"],0.2)};'
                    f'border-top:2px solid {t["color"]};border-radius:8px;'
                    f'padding:16px 18px;margin-bottom:12px;">'
                    f'<div style="font-size:12.5px;font-weight:700;color:#e2e8f0;margin-bottom:10px;">{t["title"]}</div>'
                    f'<div style="font-size:11.5px;color:#64748b;line-height:1.7;margin-bottom:12px;">{t["body"]}</div>'
                    f'<div style="background:#f3f4f6;border-radius:5px;padding:7px 10px;'
                    f'font-size:10px;color:{t["color"]};font-weight:500;">{t["impact"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    section("Currency Views")
    for c in codes:
        d = MACRO[c]
        col, bg, lbl = score_meta(d["score"])
        st.markdown(
            f'<div style="background:{bg};border:1px solid {rgba(col,0.15)};'
            f'border-radius:8px;padding:13px 16px;margin-bottom:7px;'
            f'display:flex;gap:16px;align-items:flex-start;">'
            f'<div style="min-width:72px;">'
            f'<div style="font-size:13px;font-weight:700;color:#0f172a;">{c}</div>'
            f'<div style="font-size:8.5px;color:{col};font-weight:700;'
            f'text-transform:uppercase;letter-spacing:.06em;margin-top:3px;">{lbl}</div>'
            f'</div>'
            f'<div style="font-size:11.5px;color:#64748b;line-height:1.7;flex:1;">{d["view"]}</div>'
            f'</div>',
            unsafe_allow_html=True
        )


# ═════════════════════════════════════════════════════════════════
# RISK SENTIMENT
# ═════════════════════════════════════════════════════════════════
elif page == "Risk Sentiment":
    st.markdown('<div style="font-size:20px;font-weight:700;color:#e2e8f0;margin-bottom:6px;">Risk Sentiment Barometer</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:11px;color:#0f172a;margin-bottom:20px;">Market risk appetite assessment — 23 Apr 2026</div>', unsafe_allow_html=True)

    factors = {
        "Middle East geopolitics":    (-3, "US-Iran talks collapsed. Strait of Hormuz partially blocked."),
        "Global inflation":           (-2, "Elevated CPI in UK, NZD, AUD, USD — limits CB easing globally."),
        "BoJ policy normalisation":   ( 1, "Rate hike cycle underway — positive for market stability."),
        "Global growth momentum":     (-1, "Euro Area slowing, US stable, Asia mixed."),
        "Commodity markets":          ( 2, "Gold and copper well supported. Energy falling post-ceasefire."),
        "Market volatility (VIX)":    ( 0, "VIX 18.4 — moderate. Not extreme in either direction."),
    }
    total = sum(v for v,_ in factors.values())
    pct   = max(5, min(95, int((total+9)/18*100)))

    if   total >= 4:  rlbl,rc,rbg = "RISK-ON",        COLOR_POSITIVE,"#ecfdf5"
    elif total >= 1:  rlbl,rc,rbg = "MILD RISK-ON",   "#6ee7b7","#0a2818"
    elif total == 0:  rlbl,rc,rbg = "NEUTRAL",         "#1e293b","#0f172a"
    elif total >= -3: rlbl,rc,rbg = "MILD RISK-OFF",  "#fbbf24","#fffbeb"
    else:             rlbl,rc,rbg = "RISK-OFF",        COLOR_NEGATIVE,"#fff1f2"

    cg, cs = st.columns([2,1])
    with cg:
        fig_g = go.Figure(go.Indicator(
            mode="gauge+number",
            value=pct,
            title={"text":"Risk Appetite Score","font":{"size":12,"color":"#1e293b","family":"Inter"}},
            number={"suffix":"%","font":{"size":26,"color":rc}},
            gauge={
                "axis":{"range":[0,100],"tickwidth":0.5,"tickcolor":"#334155",
                         "tickvals":[0,25,50,75,100],
                         "ticktext":["Risk-Off","Mild Off","Neutral","Mild On","Risk-On"],
                         "tickfont":{"size":9,"color":"#0f172a"}},
                "bar":{"color":rc,"thickness":0.22},
                "bgcolor":"#f3f4f6","borderwidth":0,
                "steps":[
                    {"range":[0,20],"color":"#fff1f2"},
                    {"range":[20,40],"color":"#fff7ed"},
                    {"range":[40,60],"color":"#ffffff"},
                    {"range":[60,80],"color":"#ecfdf5"},
                    {"range":[80,100],"color":"#d1fae5"},
                ],
                "threshold":{"line":{"color":rc,"width":2.5},"thickness":0.7,"value":pct},
            }
        ))
        fig_g.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", font_color="#1e293b",
            height=300, margin=dict(t=50,b=10,l=30,r=30),
        )
        st.plotly_chart(fig_g, use_container_width=True, config={"displayModeBar":False})
        st.markdown(
            f'<div style="text-align:center;background:{rbg};border:1px solid {rgba(rc,0.3)};'
            f'border-radius:8px;padding:11px;margin-top:-10px;">'
            f'<div style="font-size:16px;font-weight:800;color:{rc};letter-spacing:.06em;">{rlbl}</div>'
            f'<div style="font-size:10px;color:#0f172a;margin-top:3px;">Score: {total:+d} / 9</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    with cs:
        section("Risk Factors")
        for factor, (score, desc) in factors.items():
            fc = COLOR_POSITIVE if score>0 else COLOR_NEGATIVE if score<0 else "#64748b"
            st.markdown(
                f'{card_start()}'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">'
                f'<span style="font-size:11px;font-weight:600;color:#0f172a;">{factor}</span>'
                f'<span style="font-size:11.5px;font-weight:700;color:{fc};">{score:+d}</span>'
                f'</div>'
                f'<div style="font-size:10px;color:#0f172a;">{desc}</div>'
                f'{card_end()}',
                unsafe_allow_html=True
            )

    section("Currency Positioning by Risk Regime")
    cr1, cr2, cr3 = st.columns(3)
    groups = [
        ("Risk-On Currencies", COLOR_POSITIVE, "#ecfdf5",
         [("AUD","Commodity exposure, hawkish RBA"),
          ("NZD","CPI surprise, RBNZ pivot"),
          ("GBP","Persistent inflation, BoE hawkish")]),
        ("Safe Haven Currencies", COLOR_NEGATIVE, "#fff1f2",
         [("CHF","Primary safe haven, SNB limited"),
          ("JPY","Safe haven + hawkish BoJ pivot")]),
        ("Neutral / Mixed", "#1e293b", "#0f172a",
         [("USD","Safe haven but inflation drag"),
          ("EUR","Energy risk, weak Germany"),
          ("CAD","Oil falls, BoC may ease")]),
    ]
    for (title, col_g, bg_g, items), col_w in zip(groups, [cr1,cr2,cr3]):
        with col_w:
            inner = "".join([
                f'<div style="margin-bottom:9px;">'
                f'<b style="color:#e2e8f0;font-size:11.5px;">{ccy}</b>'
                f'<div style="font-size:10px;color:#0f172a;margin-top:2px;">{reason}</div>'
                f'</div>'
                for ccy, reason in items
            ])
            st.markdown(
                f'<div style="background:{bg_g};border:1px solid {rgba(col_g,0.2)};'
                f'border-radius:8px;padding:14px 16px;">'
                f'<div style="font-size:10px;font-weight:700;color:{col_g};'
                f'text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px;">{title}</div>'
                f'{inner}</div>',
                unsafe_allow_html=True
            )

    # Scatter GDP vs CPI
    section("GDP vs Inflation — Currency Positioning")
    fig_sc = go.Figure()
    for c in codes:
        d = MACRO[c]
        col, _, lbl = score_meta(d["score"])
        fig_sc.add_trace(go.Scatter(
            x=[d["cpi"]], y=[d["gdp"]],
            mode="markers+text",
            text=[c], textposition="top center",
            marker=dict(size=14+abs(d["score"])*3, color=d["color"],
                        line=dict(color="#f3f4f6",width=2), opacity=0.9),
            textfont=dict(color="#0f172a",size=11,family="Inter"),
            name=c, showlegend=False,
            hovertemplate=f"<b>{c}</b><br>CPI: %{{x:.1f}}%<br>GDP: %{{y:.1f}}%<extra></extra>",
        ))
    hline(fig_sc, 2.0, COLOR_PRIMARY, "2% GDP threshold")
    fig_sc.add_vline(x=2.0, line_dash="dash", line_color="#0f172a",
                     annotation_text="2% CPI target",
                     annotation_font_color="#334155", annotation_font_size=9)
    lo = chart_layout("", 360, dict(t=20,b=40,l=40,r=20))
    lo.update({"xaxis":{"gridcolor":"#e2e8f0","title":{"text":"CPI Inflation (%)","font":{"size":11,"color":"#1e293b"}}},
               "yaxis":{"gridcolor":"#e2e8f0","title":{"text":"GDP Growth (%)","font":{"size":11,"color":"#1e293b"}}}})
    fig_sc.update_layout(**lo)
    st.plotly_chart(fig_sc, use_container_width=True, config={"displayModeBar":False})


# ═════════════════════════════════════════════════════════════════
# COMPARISON
# ═════════════════════════════════════════════════════════════════
elif page == "Comparison":
    st.markdown('<div style="font-size:20px;font-weight:700;color:#e2e8f0;margin-bottom:18px;">Fundamental Comparison</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "Data Table",
        "Rate Expectations",
        "Radar",
        "Historical",
    ])

    # ── Tab 1 — Data table ────────────────────────────────────────
    with tab1:
        rows = []
        for c in codes:
            d = MACRO[c]; e = RATE_EXP[c]
            col, _, lbl = score_meta(d["score"])
            rows.append({
                "Currency":   c,
                "CB Rate %":  d["rate"],
                "End-2026 %": e["end_year"],
                "Hikes":      e["hikes"],
                "Cuts":       e["cuts"],
                "GDP %":      d["gdp"],
                "CPI %":      d["cpi"],
                "Core %":     d["core_cpi"],
                "Unem %":     d["unem"],
                "Wages %":    d["wages"],
                "PMI":        d["pmi"],
                "Bias":       lbl,
                "_score":     d["score"],
            })
        df = pd.DataFrame(rows).sort_values("_score", ascending=False)

        def style_df(row):
            styles = []
            for col_name in row.index:
                if   col_name == "CPI %":    v=row[col_name]; styles.append("color:#f43f5e" if v>3 else "color:#f59e0b" if v>2 else "color:#10b981")
                elif col_name == "GDP %":    v=row[col_name]; styles.append("color:#10b981" if v>2 else "color:#f59e0b" if v>1 else "color:#f43f5e")
                elif col_name == "Unem %":   v=row[col_name]; styles.append("color:#f43f5e" if v>6 else "color:#f59e0b" if v>4 else "color:#10b981")
                elif col_name == "End-2026 %":
                    curr = row["CB Rate %"]; v=row[col_name]
                    styles.append("color:#10b981" if v>curr else "color:#f43f5e" if v<curr else "color:#64748b")
                elif col_name == "Hikes":    v=row[col_name]; styles.append("color:#f43f5e" if v>0 else "color:#64748b")
                elif col_name == "Cuts":     v=row[col_name]; styles.append("color:#10b981" if v>0 else "color:#64748b")
                else: styles.append("color:#e2e8f0")
            return styles

        disp = [c for c in df.columns if not c.startswith("_")]
        styled = (
            df[disp].style
            .apply(style_df, axis=1)
            .set_properties(**{
                "background-color":"#ffffff","border":"1px solid #e2e8f0",
                "font-size":"12px","font-family":"Inter","padding":"8px 12px",
            })
            .set_table_styles([{"selector":"th","props":[
                ("background-color","#06080f"),("color","#334155"),
                ("font-size","9.5px"),("text-transform","uppercase"),
                ("letter-spacing","0.1em"),("border","1px solid #e2e8f0"),
                ("padding","8px 12px"),
            ]}])
        )
        st.dataframe(styled, use_container_width=True, hide_index=True, height=310)

    # ── Tab 2 — Rate Expectations (Bond Yield Spreads) ──────────────
    with tab2:
        st.markdown("""
        <div style="background:#f0fdf4;border:1px solid #6ee7b7;border-radius:8px;
        padding:10px 16px;margin-bottom:18px;font-size:11px;color:#065f46;line-height:1.7;">
          <b>Methodology</b> — Rate expectations are derived from <b>government bond yield spreads vs USD</b>.
          The 2Y spread is the most policy-sensitive indicator (predicts 6-12m CB path).
          Rising / narrowing spread = currency support. Widening negative spread = currency pressure.
          Curve slope (10Y-2Y) signals growth expectations and likelihood of further tightening.
        </div>
        """, unsafe_allow_html=True)

        # ── 1. 2Y Yield Spread vs USD ─────────────────────────────────
        section("2-Year Government Bond Yield Spread vs USD (bps)")
        spreads_2y = [round(RATE_EXP[c]["spread_2y_vs_usd"]*100) for c in codes]
        sc2 = [COLOR_POSITIVE if s > -50 else COLOR_NEGATIVE if s < -200 else "#f59e0b" for s in spreads_2y]
        fig_sp2 = go.Figure(go.Bar(
            x=codes, y=spreads_2y,
            marker=dict(color=sc2, line=dict(width=0)),
            text=[f"{v:+d}" for v in spreads_2y],
            textposition="outside",
            textfont=dict(size=11, color="#334155"),
            hovertemplate="%{x}: %{y:+d}bps vs USD 2Y<extra></extra>",
        ))
        hline(fig_sp2, 0, "#334155")
        hline(fig_sp2, -100, "#f59e0b", "−100bps threshold")
        hline(fig_sp2, -200, COLOR_NEGATIVE, "−200bps caution")
        lo2 = chart_layout("2Y Spread vs USD (bps) — positive = yield advantage over USD", 280)
        lo2.update({"yaxis": {"gridcolor":"#f1f5f9","title":{"text":"bps","font":{"size":11,"color":"#475569"}}}})
        fig_sp2.update_layout(**lo2)
        st.plotly_chart(fig_sp2, use_container_width=True, config={"displayModeBar":False})

        # ── 2. Yield Levels + Curve Slope ────────────────────────────
        ca, cb = st.columns(2)
        with ca:
            section("2Y vs 10Y Government Bond Yields (%)")
            sel_y = st.multiselect("Currencies", codes, default=codes, key="yield_sel")
            fig_yld = go.Figure()
            for c in sel_y:
                e = RATE_EXP[c]
                fig_yld.add_trace(go.Scatter(
                    x=["2Y", "10Y"],
                    y=[e["yield_2y"], e["yield_10y"]],
                    mode="lines+markers",
                    name=c,
                    line=dict(color=MACRO[c]["color"], width=2.5),
                    marker=dict(size=8, color=MACRO[c]["color"]),
                    hovertemplate=f"{c} %{{x}}: %{{y:.2f}}%<extra></extra>",
                ))
            lo_yld = chart_layout("Yield Curve by Currency (%)", 300)
            lo_yld.update({"legend":{"orientation":"h","yanchor":"bottom","y":1.02,"x":0}})
            fig_yld.update_layout(**lo_yld)
            st.plotly_chart(fig_yld, use_container_width=True, config={"displayModeBar":False})

        with cb:
            section("Curve Slope (10Y − 2Y) per Currency (bps)")
            slopes = [round(RATE_EXP[c]["curve_slope"]*100) for c in codes]
            slope_c = [COLOR_POSITIVE if s > 30 else "#f59e0b" if s > 0 else COLOR_NEGATIVE for s in slopes]
            fig_slope = go.Figure(go.Bar(
                x=codes, y=slopes,
                marker=dict(color=slope_c, line=dict(width=0)),
                text=[f"{v:+d}bps" for v in slopes],
                textposition="outside",
                textfont=dict(size=10, color="#334155"),
                hovertemplate="%{x} curve: %{y:+d}bps<extra></extra>",
            ))
            hline(fig_slope, 0, "#334155")
            lo_sl = chart_layout("Steeper = growth/hike expectations  ·  Flatter = caution", 300)
            fig_slope.update_layout(**lo_sl)
            st.plotly_chart(fig_slope, use_container_width=True, config={"displayModeBar":False})

        # ── 3. 2Y Yield Historical ─────────────────────────────────────
        section("2-Year Yield Trend — Last 6 Months")
        YIELD_MONTHS = ["Oct 25","Nov 25","Dec 25","Jan 26","Feb 26","Mar 26"]
        sel_hist_y = st.multiselect("Currencies", codes, default=codes[:5], key="yhist_sel")
        fig_yh = go.Figure()
        for c in sel_hist_y:
            e = RATE_EXP[c]
            fig_yh.add_trace(go.Scatter(
                x=YIELD_MONTHS, y=e["yield_2y_hist"],
                mode="lines+markers", name=f"{c} 2Y",
                line=dict(color=MACRO[c]["color"], width=2),
                marker=dict(size=5, color=MACRO[c]["color"]),
                hovertemplate=f"{c} 2Y %{{x}}: %{{y:.2f}}%<extra></extra>",
            ))
        lo_yh = chart_layout("Rising 2Y yield = tighter policy path  ·  Falling = easing", 300)
        lo_yh.update({"legend":{"orientation":"h","yanchor":"bottom","y":1.02,"x":0}})
        fig_yh.update_layout(**lo_yh)
        st.plotly_chart(fig_yh, use_container_width=True, config={"displayModeBar":False})

        # ── 4. Spread Summary Table ───────────────────────────────────
        section("Yield Spread Summary vs USD")
        spread_rows = []
        for c in codes:
            e   = RATE_EXP[c]
            sp2 = e["spread_2y_vs_usd"]
            sp10= e["spread_10y_vs_usd"]
            slp = e["curve_slope"]
            # Trend: compare last vs first in hist
            trend_2y = round(e["yield_2y_hist"][-1] - e["yield_2y_hist"][0], 2)
            spread_rows.append({
                "Currency":      c,
                "2Y Yield %":    e["yield_2y"],
                "10Y Yield %":   e["yield_10y"],
                "2Y Spread bps": round(sp2*100),
                "10Y Spread bps":round(sp10*100),
                "Curve (bps)":   round(slp*100),
                "2Y Trend 6m":   trend_2y,
                "CB Rate %":     MACRO[c]["rate"],
                "Bias":          e["bias"],
            })
        df_sp = pd.DataFrame(spread_rows).sort_values("2Y Spread bps", ascending=False)

        def color_spread(row):
            styles = []
            for col_name in row.index:
                if col_name in ("2Y Spread bps","10Y Spread bps"):
                    v = row[col_name]
                    styles.append("color:#15803d;font-weight:600" if v > -50
                                  else "color:#b45309" if v > -150
                                  else "color:#dc2626")
                elif col_name == "2Y Trend 6m":
                    v = row[col_name]
                    styles.append("color:#15803d;font-weight:600" if v > 0 else "color:#dc2626")
                elif col_name == "Curve (bps)":
                    v = row[col_name]
                    styles.append("color:#15803d" if v > 30 else "color:#dc2626" if v < 0 else "color:#b45309")
                else:
                    styles.append("color:#0f172a")
            return styles

        styled_sp = (
            df_sp.style
            .apply(color_spread, axis=1)
            .set_properties(**{
                "background-color":"#ffffff","border":"1px solid #e2e8f0",
                "font-size":"12px","font-family":"Inter","padding":"8px 12px",
            })
            .set_table_styles([{"selector":"th","props":[
                ("background-color","#eef2ff"),("color","#4f46e5"),
                ("font-size","9.5px"),("text-transform","uppercase"),
                ("letter-spacing","0.1em"),("border","1px solid #e2e8f0"),
                ("padding","8px 12px"),("font-weight","600"),
            ]}])
        )
        st.dataframe(styled_sp, use_container_width=True, hide_index=True, height=290)

        # ── 5. CB Meeting Probabilities ───────────────────────────────
        section("CB Meeting Probabilities — derived from yield pricing")
        sel_prob = st.selectbox("Currency", codes, key="prob_sel",
                                format_func=lambda c: f"{c}  —  {MACRO[c]['name']}")
        exp_p = RATE_EXP[sel_prob]
        e_sel = RATE_EXP[sel_prob]

        st.markdown(
            f'''<div style="background:#f8fafc;border:1px solid #e2e8f0;border-left:3px solid {COLOR_PRIMARY};
            border-radius:8px;padding:11px 16px;margin-bottom:14px;font-size:11.5px;color:#334155;line-height:1.7;">
              <b style="color:#0f172a;">2Y Yield:</b> {e_sel["yield_2y"]:.2f}%
              &nbsp;·&nbsp;
              <b style="color:#0f172a;">10Y Yield:</b> {e_sel["yield_10y"]:.2f}%
              &nbsp;·&nbsp;
              2Y Spread vs USD: <b style="color:{COLOR_POSITIVE if e_sel["spread_2y_vs_usd"]>-0.5 else COLOR_NEGATIVE};">
              {round(e_sel["spread_2y_vs_usd"]*100):+d}bps</b>
              &nbsp;·&nbsp;
              Curve: <b style="color:{COLOR_POSITIVE if e_sel["curve_slope"]>0.3 else "#f59e0b"};">
              {round(e_sel["curve_slope"]*100):+d}bps</b>
              <br>{e_sel["comment"]}
            </div>''',
            unsafe_allow_html=True
        )

        def prob_bar(pct, color):
            return (
                f'<div style="flex:1;margin:0 4px;text-align:center;">'
                f'<div style="font-size:10px;font-weight:600;color:{color};margin-bottom:4px;">{pct}%</div>'
                f'<div style="background:#f1f5f9;border-radius:3px;height:6px;overflow:hidden;">'
                f'<div style="width:{pct}%;height:6px;background:{color};border-radius:3px;'
                f'transition:width 0.4s ease;"></div></div></div>'
            )

        for m in exp_p["meetings"]:
            hike_c = COLOR_NEGATIVE if m["hike"]>30 else "#f59e0b" if m["hike"]>10 else "#94a3b8"
            hold_c = COLOR_PRIMARY
            cut_c  = COLOR_POSITIVE if m["cut"]>30 else "#f59e0b" if m["cut"]>10 else "#94a3b8"
            chg_str= f"{m['chg']:+d}bps" if m["chg"] != 0 else "Hold"
            chg_c  = COLOR_NEGATIVE if m["chg"]>0 else COLOR_POSITIVE if m["chg"]<0 else "#64748b"
            st.markdown(
                f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:9px;'
                f'padding:13px 16px;margin-bottom:7px;box-shadow:0 1px 2px rgba(0,0,0,0.02);">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:11px;">'
                f'<span style="font-size:12px;font-weight:600;color:#0f172a;">{m["label"]}</span>'
                f'<div>'
                f'<span style="font-size:11px;color:#475569;">Rate: </span>'
                f'<span style="font-size:12.5px;font-weight:700;color:#0f172a;">{m["rate"]:.2f}%</span>'
                f'&nbsp;&nbsp;'
                f'<span style="background:{rgba(chg_c,0.1)};color:{chg_c};border:1px solid {rgba(chg_c,0.2)};'
                f'font-size:9.5px;font-weight:700;padding:2px 9px;border-radius:4px;">{chg_str}</span>'
                f'</div></div>'
                f'<div style="display:flex;gap:4px;">'
                f'<div style="flex:1;text-align:center;"><div style="font-size:9px;color:#475569;text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px;">Hike</div>'
                + prob_bar(m["hike"], hike_c) +
                f'</div><div style="flex:1;text-align:center;"><div style="font-size:9px;color:#475569;text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px;">Hold</div>'
                + prob_bar(m["hold"], hold_c) +
                f'</div><div style="flex:1;text-align:center;"><div style="font-size:9px;color:#475569;text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px;">Cut</div>'
                + prob_bar(m["cut"], cut_c) +
                f'</div></div></div>',
                unsafe_allow_html=True
            )


    # ── Tab 3 — Radar ─────────────────────────────────────────────
    with tab3:
        radar_sel = st.selectbox("Currency", codes, key="radar_s",
                                 format_func=lambda c: f"{c}  —  {MACRO[c]['name']}")
        d = MACRO[radar_sel]
        def norm(v, mn, mx, rev=False):
            s = (v-mn)/(mx-mn)*10
            return round(max(0, min(10, 10-s if rev else s)), 1)
        cats = ["GDP","Wages","Confidence","PMI","Current Acct","CB Rate"]
        vals_r = [
            norm(d["gdp"],   0,4),
            norm(d["wages"], 0,6),
            norm(d["conf"],  -30,110),
            norm(d["pmi"],   47,54),
            norm(d["ca"],    -10,10),
            norm(d["rate"],  0,5),
        ]
        fig_r = go.Figure()
        fig_r.add_trace(go.Scatterpolar(
            r=vals_r+[vals_r[0]], theta=cats+[cats[0]],
            fill="toself",
            fillcolor=rgba(d["color"],0.12),
            line=dict(color=d["color"],width=2),
            name=radar_sel,
            hovertemplate="%{theta}: %{r:.1f}/10<extra></extra>",
        ))
        fig_r.update_layout(
            polar=dict(
                bgcolor="#f3f4f6",
                radialaxis=dict(visible=True, range=[0,10],
                                gridcolor="#e2e8f0", tickfont=dict(color="#1e293b",size=9)),
                angularaxis=dict(gridcolor="#e2e8f0", tickfont=dict(color="#1e293b",size=10)),
            ),
            paper_bgcolor="rgba(0,0,0,0)", font_color="#1e293b",
            title=dict(text=f"Fundamental Radar — {radar_sel}",
                       font=dict(size=12,color="#1e293b",family="Inter"), x=0),
            height=420, margin=dict(t=46,b=30,l=40,r=40),
            showlegend=False,
        )
        st.plotly_chart(fig_r, use_container_width=True, config={"displayModeBar":False})

    # ── Tab 4 — Historical ────────────────────────────────────────
    with tab4:
        h_met = st.selectbox("Indicator", ["cpi","rate","unem"],
                             format_func=lambda x: {"cpi":"CPI Inflation","rate":"CB Rate","unem":"Unemployment"}[x])
        hist_map = {"cpi": HIST_CPI, "rate": HIST_RATE, "unem": HIST_UNEM}
        hist_sel = hist_map[h_met]

        # Try DB first, fall back to static
        db_labels, db_data = load_history_from_db(8)
        if len(db_labels) >= 2:
            x_vals    = db_labels
            plot_hist = db_data[h_met if h_met!="rate" else "rate"]
        else:
            x_vals    = MONTHS
            plot_hist = hist_sel

        fig_h = go.Figure()
        for c in codes:
            y_vals = plot_hist.get(c, [])
            if not y_vals or all(v is None for v in y_vals): continue
            fig_h.add_trace(go.Scatter(
                x=x_vals, y=y_vals,
                mode="lines+markers", name=c,
                line=dict(color=MACRO[c]["color"], width=2),
                marker=dict(size=5, color=MACRO[c]["color"]),
                hovertemplate=f"{c} %{{x}}: %{{y:.2f}}%<extra></extra>",
            ))
        titles = {"cpi":"CPI Inflation (%)","rate":"Central Bank Rate (%)","unem":"Unemployment (%)"}
        if h_met == "cpi": hline(fig_h, 2.0, COLOR_PRIMARY, "2% target")
        lo_h = chart_layout(titles[h_met], 380)
        lo_h.update({"legend":{"orientation":"h","yanchor":"bottom","y":1.02,"x":0,
                                "bgcolor":"rgba(0,0,0,0)","font":{"size":10}}})
        fig_h.update_layout(**lo_h)
        st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar":False})

        src = "Live DB snapshots" if len(db_labels)>=2 else "Static data (no DB snapshots yet)"
        st.markdown(f'<div style="font-size:9.5px;color:#0f172a;margin-top:4px;">Source: {src}</div>', unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════
# TRADE SIMULATOR
# ═════════════════════════════════════════════════════════════════
elif page == "Trade Simulator":
    st.markdown('<div style="font-size:20px;font-weight:700;color:#e2e8f0;margin-bottom:6px;">Trade Simulator</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:11px;color:#0f172a;margin-bottom:16px;">Fundamental score · Risk management · Entry timing advice</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="background:#fffbeb;border:1px solid #fde68a;border-left:3px solid #d97706;
    border-radius:7px;padding:9px 14px;margin-bottom:18px;font-size:11px;color:#78350f;font-weight:500;">
      Educational purposes only. Not financial advice. Always apply your own risk management.
    </div>
    """, unsafe_allow_html=True)

    all_pairs = list(FX_RATES.keys()) + [
        "EUR/JPY","GBP/JPY","AUD/JPY","NZD/JPY","CAD/JPY","CHF/JPY",
        "EUR/AUD","EUR/NZD","GBP/AUD","GBP/NZD","GBP/CHF",
        "AUD/CAD","AUD/CHF","NZD/CAD","NZD/CHF",
    ]
    all_pairs = list(dict.fromkeys(all_pairs))
    extra_px = {
        "EUR/JPY":187.85,"GBP/JPY":215.43,"AUD/JPY":113.45,
        "NZD/JPY":94.12, "CAD/JPY":116.60,"CHF/JPY":198.20,
        "EUR/AUD":1.6550,"EUR/NZD":1.9980,"GBP/AUD":1.8960,
        "GBP/NZD":2.2971,"GBP/CHF":1.6840,"AUD/CAD":0.9720,
        "AUD/CHF":0.5720,"NZD/CAD":0.8040,"NZD/CHF":0.4740,
    }

    def get_px(pair):
        return FX_RATES[pair]["rate"] if pair in FX_RATES else extra_px.get(pair, 1.0)

    def pip_val(pair, lots):
        px = get_px(pair); pip = 0.01 if "JPY" in pair else 0.0001
        v = (pip/px)*lots*100000 if "JPY" in pair else pip*lots*100000
        return round(v, 2)

    def fund_score(pair, direction):
        b, q = pair.split("/")
        bs   = MACRO.get(b,{}).get("score",0)
        qs   = MACRO.get(q,{}).get("score",0)
        diff = bs-qs if direction=="LONG" else qs-bs
        return max(5, min(95, int((diff+6)/12*100)))

    def best_days(pair):
        b, q = pair.split("/")
        day_map = {
            "USD":["Wed","Thu","Fri"],"EUR":["Mon","Tue","Wed"],
            "GBP":["Wed","Thu"],     "JPY":["Mon","Tue","Wed"],
            "CAD":["Wed","Fri"],     "AUD":["Tue","Wed"],
            "NZD":["Tue","Wed"],     "CHF":["Thu","Fri"],
        }
        return list(dict.fromkeys(day_map.get(b,["Wed","Thu"])+day_map.get(q,["Wed","Thu"])))[:3]

    cf, cr = st.columns([2,3])

    with cf:
        section("Trade Parameters")
        pair      = st.selectbox("Pair", all_pairs)
        base, quote = pair.split("/")
        curr_px   = get_px(pair)
        direction = st.radio("Direction", ["LONG","SHORT"], horizontal=True)
        dir_c     = COLOR_POSITIVE if direction=="LONG" else COLOR_NEGATIVE

        st.markdown(
            f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:7px;'
            f'padding:9px 14px;margin:8px 0;display:flex;justify-content:space-between;">'
            f'<span style="font-size:11px;color:#0f172a;">Current {pair}</span>'
            f'<span style="font-size:13px;font-weight:700;color:#0f172a;">{curr_px}</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.markdown('<div style="height:1px;background:#e2e8f0;margin:10px 0;"></div>', unsafe_allow_html=True)

        account  = st.number_input("Account size (USD)", 100, 1_000_000, 10_000, 500)
        risk_pct = st.slider("Risk per trade (%)", 0.1, 5.0, 1.0, 0.1)
        lots     = st.select_slider("Lot size", [0.01,0.02,0.05,0.1,0.25,0.5,1.0,2.0,5.0,10.0], 0.1)

        st.markdown('<div style="height:1px;background:#e2e8f0;margin:10px 0;"></div>', unsafe_allow_html=True)
        section("Price Levels")
        entry = st.number_input("Entry price", value=float(curr_px), format="%.5f", step=0.0001)
        is_jpy = "JPY" in pair
        sl_def = round(entry-(0.50 if is_jpy else 0.0050),3 if is_jpy else 5)
        tp_def = round(entry+(1.00 if is_jpy else 0.0100),3 if is_jpy else 5)
        if direction=="SHORT":
            sl_def, tp_def = round(entry+(0.50 if is_jpy else 0.0050),3 if is_jpy else 5), round(entry-(1.00 if is_jpy else 0.0100),3 if is_jpy else 5)
        sl = st.number_input("Stop Loss", value=float(sl_def), format="%.5f", step=0.0001)
        tp = st.number_input("Take Profit", value=float(tp_def), format="%.5f", step=0.0001)

    # ── Calculations ─────────────────────────────────────────────
    pv       = pip_val(pair, lots)
    pip_sz   = 0.01 if is_jpy else 0.0001
    sl_pips  = round(abs(entry-sl)/pip_sz, 1)
    tp_pips  = round(abs(tp-entry)/pip_sz, 1)
    sl_usd   = round(sl_pips*pv, 2)
    tp_usd   = round(tp_pips*pv, 2)
    rr       = round(tp_pips/sl_pips, 2) if sl_pips>0 else 0
    risk_usd = round(account*risk_pct/100, 2)
    rec_lots = round(risk_usd/(sl_pips*pv/lots), 3) if sl_pips>0 and pv>0 else 0
    fscore   = fund_score(pair, direction)
    days     = best_days(pair)
    rr_c     = COLOR_POSITIVE if rr>=2 else "#f59e0b" if rr>=1.5 else COLOR_NEGATIVE
    fs_c     = COLOR_POSITIVE if fscore>=70 else "#f59e0b" if fscore>=50 else COLOR_NEGATIVE
    _, fs_bg, _ = score_meta(2 if fscore>=70 else 0 if fscore>=50 else -2)

    with cr:
        # Score header
        b_info = MACRO.get(base,{}); q_info = MACRO.get(quote,{})
        b_sc   = MACRO.get(base,{}).get("score",0)
        q_sc   = MACRO.get(quote,{}).get("score",0)
        st.markdown(
            f'<div style="background:linear-gradient(120deg,#ffffff,{fs_bg});'
            f'border:2px solid {rgba(fs_c,0.4)};border-radius:10px;padding:18px 22px;margin-bottom:16px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
            f'<div>'
            f'<div style="font-size:16px;font-weight:700;color:#0f172a;margin-bottom:4px;">'
            f'{direction}  {pair}</div>'
            f'<div style="font-size:10.5px;color:#0f172a;">'
            f'{base} fundamental score <b style="color:{b_info.get("color","#0f172a")}">{b_sc:+d}</b>'
            f'  vs  {quote} <b style="color:{q_info.get("color","#0f172a")}">{q_sc:+d}</b>'
            f'</div>'
            f'</div>'
            f'<div style="text-align:center;">'
            f'<div style="font-size:36px;font-weight:900;color:{fs_c};line-height:1;">{fscore}%</div>'
            f'<div style="font-size:9px;color:{fs_c};text-transform:uppercase;letter-spacing:.08em;margin-top:3px;">'
            f'Fundamental alignment</div>'
            f'</div></div>'
            f'<div style="background:#f3f4f6;border-radius:3px;height:4px;margin-top:14px;overflow:hidden;">'
            f'<div style="width:{fscore}%;height:4px;background:{fs_c};border-radius:3px;"></div>'
            f'</div></div>',
            unsafe_allow_html=True
        )

        # KPI cards
        k1,k2,k3,k4 = st.columns(4)
        for col_w, lbl, val, sub, sub_c in [
            (k1,"Stop Loss (pips)",f"{sl_pips}",f"-${sl_usd}",COLOR_NEGATIVE),
            (k2,"Take Profit (pips)",f"{tp_pips}",f"+${tp_usd}",COLOR_POSITIVE),
            (k3,"Risk / Reward",f"1:{rr}","Good" if rr>=2 else "Fair" if rr>=1.5 else "Poor",rr_c),
            (k4,"Advised Lots",f"{rec_lots}",f"${risk_usd} at risk",COLOR_PRIMARY),
        ]:
            with col_w:
                st.markdown(
                    f'<div style="background:#ffffff;border:1px solid {rgba(sub_c,0.2)};'
                    f'border-radius:8px;padding:13px 14px;text-align:center;">'
                    f'<div style="font-size:9px;color:#0f172a;text-transform:uppercase;letter-spacing:.1em;margin-bottom:5px;">{lbl}</div>'
                    f'<div style="font-size:17px;font-weight:700;color:#0f172a;">{val}</div>'
                    f'<div style="font-size:10px;color:{sub_c};margin-top:3px;">{sub}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        # Best days
        st.markdown("<br>", unsafe_allow_html=True)
        section("Recommended Entry Days")
        all_days = ["Mon","Tue","Wed","Thu","Fri"]
        day_html = '<div style="display:flex;gap:7px;flex-wrap:wrap;margin-bottom:14px;">'
        for d_s in all_days:
            best   = d_s in days
            bg_d   = "#ecfdf5" if best else "#ffffff"
            brd_d  = rgba(COLOR_POSITIVE,0.3) if best else "#e2e8f0"
            col_d  = COLOR_POSITIVE if best else "#334155"
            star   = "  *" if best else ""
            day_html += (
                f'<div style="background:{bg_d};border:1px solid {brd_d};'
                f'border-radius:6px;padding:7px 14px;text-align:center;min-width:64px;">'
                f'<div style="font-size:11px;font-weight:600;color:{col_d};">{d_s}{star}</div>'
                f'</div>'
            )
        day_html += '</div>'
        st.markdown(day_html, unsafe_allow_html=True)

        # Meeting warning
        st.markdown("""
        <div style="background:#fefce8;border:1px solid #fde047;border-left:3px solid #eab308;border-radius:12px;padding:10px 16px;margin-bottom:22px;font-size:11px;color:#854d0e;line-height:1.7;font-weight:500;">
          CB meetings this week: BoJ Apr 28  ·  BoE Apr 30  ·  FOMC Apr 30
          <br>Avoid entering 24h before these events. Wait for post-decision reaction.
        </div>
        """, unsafe_allow_html=True)

        # Advice cards
        section("Fundamental Advice")
        def advice(icon_c, title, body, brd):
            st.markdown(
                f'<div style="border-left:2px solid {brd};padding:10px 14px;'
                f'margin-bottom:7px;border-radius:0 7px 7px 0;background:#ffffff;">'
                f'<div style="font-size:11.5px;font-weight:700;color:{brd};margin-bottom:3px;">{title}</div>'
                f'<div style="font-size:11px;color:#64748b;line-height:1.6;">{body}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        if fscore>=70: advice("","Strong fundamental alignment",f"{base} ({MACRO.get(base,{}).get('bias','')}) vs {quote} ({MACRO.get(quote,{}).get('bias','')}) supports this {direction}.",COLOR_POSITIVE)
        elif fscore>=50: advice("","Moderate alignment",f"Partial fundamental support. {base} score {b_sc:+d} vs {quote} {q_sc:+d}.","#f59e0b")
        else: advice("","Weak fundamental alignment",f"This {direction} goes against macro fundamentals. Consider reversing or waiting for a better setup.",COLOR_NEGATIVE)

        if rr>=2: advice("","Risk/Reward acceptable",f"R:R of 1:{rr} meets the minimum 1:2 threshold.",COLOR_POSITIVE)
        elif rr>=1.5: advice("","Risk/Reward marginal",f"R:R of 1:{rr}. Try widening TP or tightening SL.","#f59e0b")
        else: advice("","Risk/Reward insufficient",f"R:R of 1:{rr} is below the 1:1.5 minimum. Reconsider levels.",COLOR_NEGATIVE)

        if risk_pct<=1: advice("","Conservative position sizing",f"{risk_pct:.1f}% risk per trade — well within best-practice limits.",COLOR_POSITIVE)
        elif risk_pct<=2: advice("","Moderate risk",f"{risk_pct:.1f}% per trade. Acceptable, but watch for correlated positions.","#f59e0b")
        else: advice("","Oversized position",f"{risk_pct:.1f}% per trade exceeds the 2% rule. Reduce lot size.",COLOR_NEGATIVE)

        if "JPY" in pair: advice("","JPY — BoJ pivot imminent",f"78% probability of +25bp hike Apr 28. Strongly favours JPY long positions. USD/JPY vulnerable to sharp reversal.",COLOR_PRIMARY)
        if "GBP" in pair: advice("","GBP — Services CPI sticky",f"Services CPI at 4.5% constrains BoE. GBP longs fundamentally supported near-term.","#10b981")
        if "CAD" in pair: advice("","CAD — Oil shock",f"WTI -12% this week. CAD loses primary support. Bearish CAD positions have fundamental backing.","#f97316")
        if "CHF" in pair: advice("","CHF — Safe haven demand",f"Geopolitical tensions sustaining CHF demand. SNB limited in its ability to weaken CHF.","#a855f7")

    # ── Trade chart ───────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section("Trade Setup Visualisation")
    vc1, vc2 = st.columns([3,1])

    with vc1:
        fig_t = go.Figure()
        if direction=="LONG":
            fig_t.add_hrect(y0=entry,y1=tp,fillcolor=rgba(COLOR_POSITIVE,0.05),line_width=0)
            fig_t.add_hrect(y0=sl,y1=entry,fillcolor=rgba(COLOR_NEGATIVE,0.05),line_width=0)
        else:
            fig_t.add_hrect(y0=tp,y1=entry,fillcolor=rgba(COLOR_POSITIVE,0.05),line_width=0)
            fig_t.add_hrect(y0=entry,y1=sl,fillcolor=rgba(COLOR_NEGATIVE,0.05),line_width=0)

        fig_t.add_hline(y=entry, line_color=COLOR_PRIMARY, line_width=1.5,
                        annotation_text=f"Entry  {entry}", annotation_font_color="#334155",annotation_font_size=10)
        fig_t.add_hline(y=sl, line_color=COLOR_NEGATIVE, line_width=1.5, line_dash="dash",
                        annotation_text=f"SL  {sl}  (-{sl_pips}p  -${sl_usd})",
                        annotation_font_color="#334155",annotation_font_size=10)
        fig_t.add_hline(y=tp, line_color=COLOR_POSITIVE, line_width=1.5, line_dash="dash",
                        annotation_text=f"TP  {tp}  (+{tp_pips}p  +${tp_usd})",
                        annotation_font_color="#334155",annotation_font_size=10)

        random.seed(42)
        trend = (0.03 if direction=="LONG" else -0.03) if is_jpy else (0.00003 if direction=="LONG" else -0.00003)
        sim = [entry]
        for _ in range(49):
            noise = (random.random()-0.5)*(0.5 if is_jpy else 0.0001*5)
            sim.append(sim[-1]+trend+noise)

        fig_t.add_trace(go.Scatter(
            x=list(range(50)), y=sim,
            mode="lines",
            line=dict(color="#334155",width=1.5,dash="dot"),
            showlegend=False, hoverinfo="skip",
        ))
        yr = max(abs(tp-entry),abs(entry-sl))*1.5
        lo_t = chart_layout("", 310, dict(t=20,b=30,l=50,r=160))
        lo_t.update({"xaxis":{"showticklabels":False,"gridcolor":"#0a0f1a"},
                     "yaxis":{"gridcolor":"#0a0f1a","range":[min(sl,tp)-yr*0.1,max(sl,tp)+yr*0.1]}})
        fig_t.update_layout(**lo_t)
        st.plotly_chart(fig_t, use_container_width=True, config={"displayModeBar":False})

    with vc2:
        fig_p = go.Figure(go.Pie(
            values=[sl_pips, tp_pips],
            labels=["Risk","Reward"],
            marker_colors=[COLOR_NEGATIVE,COLOR_POSITIVE],
            hole=0.62,
            textinfo="label+percent",
            textfont=dict(size=10, color="#334155"),
            showlegend=False,
            hovertemplate="%{label}: %{value} pips<extra></extra>",
        ))
        fig_p.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#1e293b",
            height=280,
            margin=dict(t=30,b=10,l=10,r=10),
            annotations=[dict(text=f"1:{rr}",x=0.5,y=0.5,
                              font_size=18,font_color="#1e293b",showarrow=False)],
        )
        st.plotly_chart(fig_p, use_container_width=True, config={"displayModeBar":False})

    # Verdict
    good = fscore>=65 and rr>=1.5
    warn = fscore>=45
    vc   = COLOR_POSITIVE if good else "#f59e0b" if warn else COLOR_NEGATIVE
    vl   = "TRADE VIABLE" if good else "ELEVATED RISK" if warn else "NOT RECOMMENDED"
    vd   = ("Fundamentals and R:R support this trade. Stay disciplined on your SL."
            if good else "Trade carries risk. Reduce size and confirm timing."
            if warn else "Fundamentals oppose this trade. Wait for a better setup or reverse direction.")
    st.markdown(
        f'<div style="background:linear-gradient(120deg,#ffffff,{rgba(vc,0.06)});'
        f'border:2px solid {rgba(vc,0.4)};border-radius:10px;padding:18px 24px;'
        f'text-align:center;margin-top:14px;">'
        f'<div style="font-size:18px;font-weight:800;color:{vc};letter-spacing:.04em;">{vl}</div>'
        f'<div style="font-size:11.5px;color:#64748b;margin-top:7px;max-width:600px;margin-left:auto;margin-right:auto;">{vd}</div>'
        f'<div style="display:flex;justify-content:center;gap:24px;margin-top:14px;flex-wrap:wrap;">'
        f'<span style="font-size:10.5px;color:#0f172a;">Fundamental score <b style="color:{vc};">{fscore}%</b></span>'
        f'<span style="font-size:10.5px;color:#0f172a;">R:R <b style="color:{vc};">1:{rr}</b></span>'
        f'<span style="font-size:10.5px;color:#0f172a;">Advised lots <b style="color:#4f46e5;">{rec_lots}</b></span>'
        f'<span style="font-size:10.5px;color:#0f172a;">Max risk <b style="color:#f43f5e;">${risk_usd}</b></span>'
        f'</div></div>',
        unsafe_allow_html=True
    )


# ═════════════════════════════════════════════════════════════════
# SYSTEM
# ═════════════════════════════════════════════════════════════════
elif page == "System":
    st.markdown('<div style="font-size:20px;font-weight:700;color:#e2e8f0;margin-bottom:18px;">System Status</div>', unsafe_allow_html=True)

    last = get_last_update()
    now_utc = datetime.now(timezone.utc)

    s1,s2,s3 = st.columns(3)
    with s1: st.metric("Last Snapshot",    last.get("ts","Never"), last.get("trigger","—"))
    with s2: st.metric("Current UTC Time", now_utc.strftime("%H:%M"), now_utc.strftime("%d %b %Y"))
    with s3: st.metric("DB File",          "fx_data.db", "SQLite")

    section("Auto-Update Schedule")
    st.markdown("""
    <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;padding:16px 18px;">
      <div style="display:flex;gap:24px;flex-wrap:wrap;">
        <div>
          <div style="font-size:9.5px;color:#0f172a;text-transform:uppercase;letter-spacing:.1em;">London Close</div>
          <div style="font-size:14px;font-weight:700;color:#0f172a;margin-top:4px;">17:00 UTC  Mon-Fri</div>
          <div style="font-size:10px;color:#0f172a;margin-top:2px;">Session key: YYYY-MM-DD-LDN</div>
        </div>
        <div style="width:1px;background:#e2e8f0;"></div>
        <div>
          <div style="font-size:9.5px;color:#0f172a;text-transform:uppercase;letter-spacing:.1em;">New York Close</div>
          <div style="font-size:14px;font-weight:700;color:#0f172a;margin-top:4px;">22:00 UTC  Mon-Fri</div>
          <div style="font-size:10px;color:#0f172a;margin-top:2px;">Session key: YYYY-MM-DD-NY</div>
        </div>
        <div style="width:1px;background:#e2e8f0;"></div>
        <div>
          <div style="font-size:9.5px;color:#0f172a;text-transform:uppercase;letter-spacing:.1em;">Storage</div>
          <div style="font-size:14px;font-weight:700;color:#0f172a;margin-top:4px;">SQLite  fx_data.db</div>
          <div style="font-size:10px;color:#0f172a;margin-top:2px;">Tables: snapshots · fx_snapshots · update_log</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    section("Update Log")
    logs = load_update_log(20)
    if logs:
        for log in logs:
            sc = COLOR_POSITIVE if log["status"]=="success" else COLOR_NEGATIVE
            st.markdown(
                f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:7px;'
                f'padding:9px 14px;margin-bottom:5px;display:flex;gap:14px;align-items:center;">'
                f'<div style="width:6px;height:6px;border-radius:50%;background:{sc};flex-shrink:0;"></div>'
                f'<span style="font-size:10px;color:#0f172a;min-width:160px;">{log.get("ts","")}</span>'
                f'<span style="font-size:10.5px;font-weight:600;color:#475569;">{log.get("session","")}</span>'
                f'<span style="font-size:10px;color:#475569;">{log.get("trigger","")}</span>'
                f'<span style="font-size:10px;color:{sc};margin-left:auto;">{log.get("status","")}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
    else:
        st.markdown('<div style="font-size:11px;color:#0f172a;padding:12px;">No snapshots recorded yet. Run the app and wait for 17:00 or 22:00 UTC, or click "Force snapshot now" in the sidebar.</div>', unsafe_allow_html=True)

    section("How Data Updates Work")
    st.markdown("""
    <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;padding:16px 18px;font-size:11.5px;color:#64748b;line-height:1.9;">
      <b style="color:#475569;">Automatic (background scheduler)</b><br>
      The APScheduler runs inside the Streamlit process. At 17:00 UTC (London close) and 22:00 UTC
      (New York close) on weekdays, it calls <code style="color:#4f46e5;">save_snapshot()</code>
      which writes the current macro data to <code>fx_data.db</code>.<br><br>
      <b style="color:#475569;">Historical charts</b><br>
      The Historical tab in Comparison reads from the DB first. After 2+ sessions are stored,
      charts show live session data instead of static fallback data.<br><br>
      <b style="color:#475569;">Manual updates</b><br>
      Edit <code>MACRO</code>, <code>RATE_EXP</code>, <code>FX_RATES</code>, <code>CALENDAR</code>
      and <code>NEWS</code> in <code>data.py</code> each week after major releases.
      The scheduler then persists those values automatically.
    </div>
    """, unsafe_allow_html=True)