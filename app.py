"""
FX Intermarket Pro — v3.1
Dark fintech terminal. Premium redesign of the "Matrice Juridictionnelle Fondamentale" table:
- Full HTML/CSS table with sticky header, flag emoji, ranked rows
- Score column: gradient pill + mini progress bar + medal emoji
- Inline delta coloring for PIB (green/red), Rates (blue), Inflation (amber), Chômage (red/green)
- Row hover highlight, sortable legend
- All other tabs preserved from v3.0
"""

import os
import json
import requests
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

from data import (
    MACRO, FX_RATES, MARKET_ASSETS,
    detect_market_sentiment, HIST_RATE,
    load_update_log, start_background_updater,
    refresh_and_persist, PAIRS,
)
from utils.fx_calculations import compute_spreads, normalize_score, build_comparison_table
from utils.sentiment_engine import regime_weights
from utils.commodities_logic import wti_adjustment
from utils.recommendations import rank_unique_pairs as rank_all_pairs
from utils.news import fetch_news

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="FX Intermarket Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

try:
    start_background_updater(interval_seconds=120)
except Exception:
    pass

# ─────────────────────────────────────────────
# Currency flags map
# ─────────────────────────────────────────────
CCY_FLAGS = {
    "USD": "🇺🇸", "EUR": "🇪🇺", "GBP": "🇬🇧", "JPY": "🇯🇵",
    "CAD": "🇨🇦", "AUD": "🇦🇺", "NZD": "🇳🇿", "CHF": "🇨🇭",
    "SEK": "🇸🇪", "NOK": "🇳🇴", "DKK": "🇩🇰", "CNY": "🇨🇳",
    "SGD": "🇸🇬", "HKD": "🇭🇰", "MXN": "🇲🇽", "BRL": "🇧🇷",
}

# ─────────────────────────────────────────────
# Risk Sentiment Engine (VIX + SP500)
# ─────────────────────────────────────────────
def compute_risk_sentiment(market_assets: dict) -> dict:
    """
    Derives a structured risk-sentiment reading from VIX and S&P 500.

    Returns a dict:
      regime        : "RISK-ON" | "RISK-OFF" | "NEUTRE"
      vix           : float | None
      vix_chg       : float | None
      sp500_chg     : float | None
      vix_label     : str   ("Faible" / "Modéré" / "Élevé" / "Extrême")
      score         : float  0–100  (100 = max risk-on)
      bias_label    : str   description one-liner
      fx_impact     : dict  {ccy: "BULLISH"|"BEARISH"|"NEUTRE"}
      bonus         : dict  {ccy: float}  additive score adjustment
      color         : str   hex color for the regime
      icon          : str   emoji
    """
    vix_data  = market_assets.get("VIX",    {})
    sp_data   = market_assets.get("US_500", {})

    try:    vix     = float(vix_data.get("price") or 0)
    except: vix     = None
    try:    vix_chg = float(vix_data.get("chg")   or 0)
    except: vix_chg = 0.0
    try:    sp_chg  = float(sp_data.get("chg")    or 0)
    except: sp_chg  = 0.0

    # VIX thresholds: <15 calm, 15-20 moderate, 20-30 elevated, >30 extreme
    if vix is not None:
        if   vix < 15:  vix_label = "Faible"
        elif vix < 20:  vix_label = "Modéré"
        elif vix < 30:  vix_label = "Élevé"
        else:           vix_label = "Extrême"
    else:
        vix_label = "Inconnu"

    # Score: high SP500 + low VIX = risk-on (100), low SP500 + high VIX = risk-off (0)
    sp_score  = max(0.0, min(100.0, 50 + sp_chg * 10))    # sp500 chg drives score
    vix_score = max(0.0, min(100.0, 100 - (vix or 20) * 2.5)) if vix else 50.0
    score     = round((sp_score * 0.6 + vix_score * 0.4), 1)

    # Regime
    if   score >= 62: regime = "RISK-ON"
    elif score <= 38: regime = "RISK-OFF"
    else:             regime = "NEUTRE"

    # FX bias per regime
    # Risk-ON  → AUD NZD CAD favored; JPY CHF USD penalized
    # Risk-OFF → JPY CHF USD favored; AUD NZD CAD penalized
    RISK_ON_BULL  = {"AUD", "NZD", "CAD", "GBP", "EUR", "SEK", "NOK"}
    RISK_ON_BEAR  = {"JPY", "CHF", "USD"}
    RISK_OFF_BULL = {"JPY", "CHF", "USD"}
    RISK_OFF_BEAR = {"AUD", "NZD", "CAD", "GBP", "EUR", "MXN", "BRL"}

    if regime == "RISK-ON":
        bull_set, bear_set = RISK_ON_BULL, RISK_ON_BEAR
        color, icon = "#10b981", "🟢"
        bias_label  = f"Appétit au risque élevé · VIX {vix_label} · SP500 {sp_chg:+.2f}%"
    elif regime == "RISK-OFF":
        bull_set, bear_set = RISK_OFF_BULL, RISK_OFF_BEAR
        color, icon = "#f43f5e", "🔴"
        bias_label  = f"Aversion au risque · VIX {vix_label} · SP500 {sp_chg:+.2f}%"
    else:
        bull_set, bear_set = set(), set()
        color, icon = "#f59e0b", "🟡"
        bias_label  = f"Sentiment neutre · VIX {vix_label} · SP500 {sp_chg:+.2f}%"

    fx_impact = {}
    bonus     = {}
    intensity = abs(score - 50) / 50.0          # 0–1, how strong the regime is
    max_bonus = 8.0 * intensity                  # cap additive bonus at ±8

    all_ccys = list(CCY_FLAGS.keys()) + ["USD","EUR","GBP","JPY","CAD","AUD","NZD","CHF"]
    for ccy in set(all_ccys):
        if   ccy in bull_set: fx_impact[ccy] = "BULLISH"; bonus[ccy] =  max_bonus
        elif ccy in bear_set: fx_impact[ccy] = "BEARISH"; bonus[ccy] = -max_bonus
        else:                 fx_impact[ccy] = "NEUTRE";  bonus[ccy] =  0.0

    return {
        "regime":    regime,
        "vix":       vix,
        "vix_chg":   vix_chg,
        "vix_label": vix_label,
        "sp500_chg": sp_chg,
        "score":     score,
        "bias_label":bias_label,
        "fx_impact": fx_impact,
        "bonus":     bonus,
        "color":     color,
        "icon":      icon,
    }


def risk_sentiment_panel_html(rs: dict) -> str:
    """Renders a compact risk-sentiment status bar as HTML."""
    regime  = rs["regime"]
    color   = rs["color"]
    icon    = rs["icon"]
    score   = rs["score"]
    vix     = rs["vix"]
    vix_chg = rs["vix_chg"] or 0
    sp_chg  = rs["sp500_chg"] or 0
    vix_lbl = rs["vix_label"]
    bias    = rs["bias_label"]

    bar_w   = int(score)
    vix_color  = "#10b981" if vix_chg < 0 else "#f43f5e"
    sp_color   = "#10b981" if sp_chg  >= 0 else "#f43f5e"

    vix_arrow  = "▼" if vix_chg < 0 else "▲"
    sp_arrow   = "▲" if sp_chg  >= 0 else "▼"

    return f"""
    <div style="background:linear-gradient(135deg,rgba(124,58,237,0.06),rgba(8,145,178,0.04));
                border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:14px 18px;
                margin-bottom:14px;font-family:'Inter',system-ui,sans-serif;">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
        <div style="display:flex;align-items:center;gap:10px;">
          <span style="font-size:20px;">{icon}</span>
          <div>
            <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;
                        color:#94a3b8;margin-bottom:2px;">Risque de Marché</div>
            <div style="font-size:16px;font-weight:800;color:{color};">{regime}</div>
          </div>
        </div>
        <div style="display:flex;gap:16px;flex-wrap:wrap;">
          <div style="text-align:center;">
            <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:2px;">VIX</div>
            <div style="font-family:'JetBrains Mono',monospace;font-weight:700;color:#fff;font-size:14px;">{vix if vix else '—'}</div>
            <div style="font-size:11px;color:{vix_color};font-weight:600;">{vix_arrow} {abs(vix_chg):.2f}%</div>
          </div>
          <div style="width:1px;background:rgba(255,255,255,0.06);"></div>
          <div style="text-align:center;">
            <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:2px;">S&P 500</div>
            <div style="font-family:'JetBrains Mono',monospace;font-weight:700;color:{sp_color};font-size:14px;">{sp_arrow} {abs(sp_chg):.2f}%</div>
            <div style="font-size:11px;color:#94a3b8;">variation</div>
          </div>
          <div style="width:1px;background:rgba(255,255,255,0.06);"></div>
          <div style="text-align:center;">
            <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:2px;">Score</div>
            <div style="font-family:'JetBrains Mono',monospace;font-weight:700;color:{color};font-size:14px;">{score:.0f}/100</div>
            <div style="font-size:11px;color:#94a3b8;">{vix_lbl}</div>
          </div>
        </div>
      </div>
      <div style="margin-top:10px;">
        <div style="height:5px;background:rgba(255,255,255,0.05);border-radius:999px;overflow:hidden;">
          <div style="width:{bar_w}%;height:100%;background:linear-gradient(90deg,#f43f5e,#f59e0b,#10b981);
                      border-radius:999px;transition:width 400ms ease;"></div>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:3px;">
          <span style="font-size:10px;color:#f43f5e;">Risk-OFF</span>
          <span style="font-size:10px;color:#94a3b8;">{bias}</span>
          <span style="font-size:10px;color:#10b981;">Risk-ON</span>
        </div>
      </div>
    </div>"""


def ccy_risk_chips_html(base: str, quote: str, rs: dict) -> str:
    """Shows per-currency risk-bias chips for a given pair."""
    def chip(ccy, impact):
        colors = {"BULLISH": ("#10b981","rgba(16,185,129,0.12)","rgba(16,185,129,0.25)"),
                  "BEARISH": ("#f43f5e","rgba(244,63,94,0.12)","rgba(244,63,94,0.25)"),
                  "NEUTRE":  ("#94a3b8","rgba(148,163,184,0.08)","rgba(148,163,184,0.2)")}
        arrows = {"BULLISH":"▲","BEARISH":"▼","NEUTRE":"–"}
        c, bg, brd = colors.get(impact, colors["NEUTRE"])
        a = arrows.get(impact,"–")
        flag = CCY_FLAGS.get(ccy,"")
        return (f'<span style="display:inline-flex;align-items:center;gap:5px;background:{bg};border:1px solid {brd};'
                f'color:{c};font-weight:700;font-size:12px;padding:5px 12px;border-radius:999px;margin:3px;">'
                f'{flag} {ccy} {a}</span>')

    base_impact  = rs["fx_impact"].get(base,  "NEUTRE")
    quote_impact = rs["fx_impact"].get(quote, "NEUTRE")
    base_bonus   = rs["bonus"].get(base,  0)
    quote_bonus  = rs["bonus"].get(quote, 0)
    net_bonus    = base_bonus - quote_bonus

    net_color = "#10b981" if net_bonus > 0.5 else "#f43f5e" if net_bonus < -0.5 else "#94a3b8"
    net_arrow = "▲" if net_bonus > 0.5 else "▼" if net_bonus < -0.5 else "–"

    return f"""
    <div style="display:flex;align-items:center;flex-wrap:wrap;gap:6px;margin-top:8px;margin-bottom:4px;">
      <span style="font-size:11px;color:#94a3b8;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;margin-right:4px;">Biais risque:</span>
      {chip(base, base_impact)}
      <span style="color:#94a3b8;font-size:14px;">vs</span>
      {chip(quote, quote_impact)}
      <span style="margin-left:8px;font-size:12px;color:{net_color};font-weight:700;">
        Impact net {net_arrow} {abs(net_bonus):.1f}pts
      </span>
    </div>"""


# ─────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --bg:      #041022;
  --surface: #0d1424;
  --panel:   #0b1624;
  --panel-2: #0f2233;
  --accent:  #7c3aed;
  --accent-2:#0891b2;
  --accent-g:linear-gradient(135deg,#7c3aed 0%,#0891b2 100%);
  --txt:     #ffffff;
  --txt-2:   #cbd5e1;
  --txt-3:   #94a3b8;
  --border:  rgba(255,255,255,0.06);
  --r:       12px;
  --z2:      0 4px 16px rgba(0,0,0,.55);
  --z3:      0 8px 32px rgba(0,0,0,.65);
}

html, body, .stApp, .main, [data-testid="stAppViewContainer"] {
  background: linear-gradient(180deg,var(--bg) 0%,#03121b 100%) !important;
  color: var(--txt);
  font-family: 'Inter', system-ui, sans-serif;
}

#MainMenu, footer, header { visibility: hidden !important; }
[data-testid="stDecoration"] { display: none !important; }

::-webkit-scrollbar { width:6px; height:6px; }
::-webkit-scrollbar-thumb { background:rgba(124,58,237,.4); border-radius:6px; }

.topbar {
  display:flex; justify-content:space-between; align-items:center;
  background:linear-gradient(90deg,rgba(124,58,237,0.14),rgba(8,145,178,0.08));
  border-radius:14px; padding:14px 20px; margin-bottom:18px;
  border:1px solid var(--border); box-shadow:var(--z3);
}
.topbar-title {
  font-size:18px; font-weight:800;
  background:var(--accent-g);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}
.topbar-sub { font-size:12px; color:var(--txt-2); margin-top:2px; }
.topbar-ts  { font-family:'JetBrains Mono',monospace; font-size:12px; color:var(--txt-3); }

[data-testid="stSidebar"] { background:var(--surface) !important; border-right:1px solid var(--border) !important; }
.sidebar-section { background:linear-gradient(180deg,var(--panel),var(--panel-2)); border:1px solid var(--border); border-radius:10px; padding:12px; margin-bottom:12px; }

.kpi { background:linear-gradient(180deg,var(--panel),var(--panel-2)); border:1px solid var(--border); border-radius:10px; padding:12px; box-shadow:var(--z2); }

.stDataFrame th { color:var(--txt) !important; font-weight:700 !important; font-size:13px !important; }
.stDataFrame td { color:var(--txt) !important; font-family:'JetBrains Mono',monospace !important; font-size:13px !important; }

@media (prefers-reduced-motion:reduce) {
  *,*::before,*::after { transition-duration:0.01ms !important; animation-duration:0.01ms !important; }
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Macro table — premium HTML renderer
# ─────────────────────────────────────────────
def render_macro_table(df: pd.DataFrame) -> str:
    df_sorted = df.sort_values("Score", ascending=False).reset_index(drop=True)

    def score_cell(val, rank):
        try:
            v = float(val)
        except Exception:
            return f'<span style="color:#fff">{val}</span>'
        if v >= 65:
            bar_color = "linear-gradient(90deg,#10b981,#34d399)"
            pill_color = "#10b981"
            pill_bg = "rgba(16,185,129,0.15)"
            pill_border = "rgba(16,185,129,0.3)"
        elif v >= 40:
            bar_color = "linear-gradient(90deg,#f59e0b,#fcd34d)"
            pill_color = "#f59e0b"
            pill_bg = "rgba(245,158,11,0.15)"
            pill_border = "rgba(245,158,11,0.3)"
        else:
            bar_color = "linear-gradient(90deg,#f43f5e,#fb7185)"
            pill_color = "#f43f5e"
            pill_bg = "rgba(244,63,94,0.15)"
            pill_border = "rgba(244,63,94,0.3)"

        bar_w = max(4, min(100, int(v)))
        medal = ("🥇" if rank == 0 else "🥈" if rank == 1 else "🥉" if rank == 2 else "")

        return f'''
        <div style="display:flex;flex-direction:column;align-items:center;gap:5px;min-width:90px;">
          <div style="display:flex;align-items:center;gap:5px;">
            <span style="background:{pill_bg};border:1px solid {pill_border};color:{pill_color};
                         font-weight:800;font-size:13px;padding:3px 11px;border-radius:999px;
                         font-family:'JetBrains Mono',monospace;letter-spacing:0.02em;">{v:.0f}</span>
            {('<span style="font-size:14px;">' + medal + '</span>') if medal else ""}
          </div>
          <div style="width:76px;height:5px;background:rgba(255,255,255,0.06);border-radius:999px;overflow:hidden;">
            <div style="width:{bar_w}%;height:100%;background:{bar_color};border-radius:999px;"></div>
          </div>
        </div>'''

    def gdp_cell(val):
        try:
            v = float(val)
        except Exception:
            return f'<span style="color:#fff;font-family:JetBrains Mono">{val}</span>'
        color = "#10b981" if v > 0 else "#f43f5e" if v < 0 else "#94a3b8"
        arrow = "▲" if v > 0 else "▼" if v < 0 else "–"
        return f'<span style="color:{color};font-weight:700;font-family:JetBrains Mono,monospace">{arrow} {v:+.2f}%</span>'

    def numeric_cell(val, col):
        try:
            v = float(val)
        except Exception:
            return f'<span style="color:#fff;font-family:JetBrains Mono">{val}</span>'
        if col in ("Taux (%)", "10Y Yield (%)"):
            color = "#38bdf8" if v >= 3.0 else "#94a3b8"
            return f'<span style="color:{color};font-family:JetBrains Mono,monospace;font-weight:600">{v:.2f}%</span>'
        if col == "Inflation (%)":
            color = "#f59e0b" if v >= 3.5 else "#10b981" if v <= 2.5 else "#cbd5e1"
            return f'<span style="color:{color};font-family:JetBrains Mono,monospace">{v:.1f}%</span>'
        if col == "Chômage (%)":
            color = "#f43f5e" if v >= 6.0 else "#10b981" if v <= 4.0 else "#cbd5e1"
            return f'<span style="color:{color};font-family:JetBrains Mono,monospace">{v:.1f}%</span>'
        return f'<span style="color:#fff;font-family:JetBrains Mono,monospace">{val}</span>'

    cols = list(df_sorted.columns)
    th_style = (
        "padding:12px 16px;text-align:center;font-size:11px;font-weight:700;"
        "text-transform:uppercase;letter-spacing:0.1em;color:#94a3b8;white-space:nowrap;"
        "border-bottom:1px solid rgba(255,255,255,0.06);position:sticky;top:0;z-index:2;"
        "background:linear-gradient(180deg,#0f1e35,#0b1624);backdrop-filter:blur(8px);"
    )
    thead = "<tr>" + "".join(f'<th style="{th_style}">{c}</th>' for c in cols) + "</tr>"

    tbody_rows = []
    for rank, (_, row) in enumerate(df_sorted.iterrows()):
        row_bg = "rgba(255,255,255,0.012)" if rank % 2 == 0 else "transparent"
        cells = []
        for c in cols:
            val = row[c]
            td_style = "padding:12px 16px;text-align:center;vertical-align:middle;border-bottom:1px solid rgba(255,255,255,0.03);"
            if c == "Devise":
                flag = CCY_FLAGS.get(str(val), "🌐")
                cell_html = (
                    f'<div style="display:flex;align-items:center;gap:8px;justify-content:center;">'
                    f'<span style="font-size:18px;">{flag}</span>'
                    f'<span style="font-family:JetBrains Mono,monospace;font-weight:800;font-size:14px;color:#fff;">{val}</span>'
                    f'</div>'
                )
            elif c == "Score":
                cell_html = score_cell(val, rank)
            elif c == "PIB (%)":
                cell_html = gdp_cell(val)
            elif c in ("Taux (%)", "10Y Yield (%)", "Inflation (%)", "Chômage (%)"):
                cell_html = numeric_cell(val, c)
            elif c == "Banque Centrale":
                cell_html = f'<span style="color:#cbd5e1;font-size:13px;font-weight:500;">{val}</span>'
            else:
                cell_html = f'<span style="color:#fff;">{val}</span>'
            cells.append(f'<td style="{td_style}">{cell_html}</td>')

        hover_in  = f"this.style.background='rgba(124,58,237,0.07)'"
        hover_out = f"this.style.background='{row_bg}'"
        tbody_rows.append(
            f'<tr style="background:{row_bg};transition:background 150ms ease;" '
            f'onmouseover="{hover_in}" onmouseout="{hover_out}">'
            + "".join(cells) + "</tr>"
        )

    tbody = "\n".join(tbody_rows)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:transparent; font-family:'Inter',system-ui,sans-serif; -webkit-font-smoothing:antialiased; }}
  .wrapper {{ border-radius:14px; overflow:hidden; border:1px solid rgba(255,255,255,0.06); background:linear-gradient(180deg,#0b1624,#0f2233); box-shadow:0 8px 32px rgba(0,0,0,0.65); }}
  .tscroll {{ overflow-x:auto; overflow-y:auto; max-height:340px; }}
  table {{ width:100%; border-collapse:collapse; }}
  .legend {{ display:flex; gap:20px; padding:10px 16px; border-top:1px solid rgba(255,255,255,0.05); background:rgba(255,255,255,0.01); flex-wrap:wrap; }}
  .li {{ display:flex; align-items:center; gap:6px; font-size:11px; color:#94a3b8; font-family:'Inter',sans-serif; }}
  .dot {{ width:8px; height:8px; border-radius:50%; }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="tscroll">
    <table>
      <thead>{thead}</thead>
      <tbody>{tbody}</tbody>
    </table>
  </div>
  <div class="legend">
    <div class="li"><div class="dot" style="background:#10b981"></div> Score ≥ 65 (Hawkish)</div>
    <div class="li"><div class="dot" style="background:#f59e0b"></div> Score 40–64 (Neutre)</div>
    <div class="li"><div class="dot" style="background:#f43f5e"></div> Score &lt; 40 (Dovish)</div>
    <div class="li"><div class="dot" style="background:#38bdf8"></div> Taux / Yield ≥ 3%</div>
    <div class="li"><div class="dot" style="background:#f59e0b"></div> Inflation &gt; 3.5%</div>
    <div class="li"><div class="dot" style="background:#f43f5e"></div> Chômage ≥ 6%</div>
  </div>
</div>
</body>
</html>"""


# ─────────────────────────────────────────────
# Generic styled HTML table renderer
# ─────────────────────────────────────────────
def _styled_table_html(headers, rows, col_formats=None, height=320, legend_items=None):
    TH = (
        "padding:11px 14px;text-align:center;font-size:11px;font-weight:700;"
        "text-transform:uppercase;letter-spacing:0.1em;color:#94a3b8;white-space:nowrap;"
        "border-bottom:1px solid rgba(255,255,255,0.06);position:sticky;top:0;z-index:2;"
        "background:linear-gradient(180deg,#0f1e35,#0b1624);"
    )
    TD = "padding:11px 14px;text-align:center;vertical-align:middle;border-bottom:1px solid rgba(255,255,255,0.03);"
    thead = "<tr>" + "".join(f'<th style="{TH}">{h}</th>' for h in headers) + "</tr>"
    tbody_rows = []
    for ri, row in enumerate(rows):
        bg = "rgba(255,255,255,0.012)" if ri % 2 == 0 else "transparent"
        hi = "this.style.background='rgba(124,58,237,0.07)'"
        ho = f"this.style.background='{bg}'"
        cells = []
        for ci, val in enumerate(row):
            if col_formats and ci in col_formats:
                cell_html = col_formats[ci](val)
            else:
                cell_html = f'<span style="color:#fff;font-family:JetBrains Mono,monospace;">{val}</span>'
            cells.append(f'<td style="{TD}">{cell_html}</td>')
        tbody_rows.append(
            f'<tr style="background:{bg};transition:background 150ms ease;" onmouseover="{hi}" onmouseout="{ho}">'
            + "".join(cells) + "</tr>"
        )
    legend_html = ""
    if legend_items:
        items = "".join(
            f'<div style="display:flex;align-items:center;gap:6px;font-size:11px;color:#94a3b8;">'
            f'<div style="width:8px;height:8px;border-radius:50%;background:{li["dot"]};flex-shrink:0;"></div>'
            f'{li["label"]}</div>'
            for li in legend_items
        )
        legend_html = f'<div style="display:flex;gap:18px;flex-wrap:wrap;padding:10px 16px;border-top:1px solid rgba(255,255,255,0.05);background:rgba(255,255,255,0.01);">{items}</div>'
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{background:transparent;font-family:'Inter',system-ui,sans-serif;-webkit-font-smoothing:antialiased;}}
  .wrap{{border-radius:14px;overflow:hidden;border:1px solid rgba(255,255,255,0.06);background:linear-gradient(180deg,#0b1624,#0f2233);box-shadow:0 8px 32px rgba(0,0,0,.65);}}
  .scroll{{overflow-x:auto;overflow-y:auto;max-height:{height}px;}}
  table{{width:100%;border-collapse:collapse;}}
</style></head><body>
<div class="wrap">
  <div class="scroll"><table><thead>{thead}</thead><tbody>{"".join(tbody_rows)}</tbody></table></div>
  {legend_html}
</div>
</body></html>"""


def render_comparison_table(df):
    if df is None or df.empty:
        return ""
    headers = list(df.columns)
    col_formats = {}
    for ci, col in enumerate(headers):
        c = col.lower()
        if any(k in c for k in ("spread","diff","écart")):
            def fmt_spread(val):
                try:
                    v = float(str(val).replace("%","").replace("bp","").strip())
                    color = "#10b981" if v > 0 else "#f43f5e" if v < 0 else "#94a3b8"
                    arrow = "▲" if v > 0 else "▼" if v < 0 else "–"
                    return f'<span style="color:{color};font-weight:700;font-family:JetBrains Mono,monospace">{arrow} {v:+.2f}</span>'
                except Exception:
                    return f'<span style="color:#fff;font-family:JetBrains Mono,monospace">{val}</span>'
            col_formats[ci] = fmt_spread
        elif any(k in c for k in ("taux","rate","yield","rendement")):
            def fmt_rate(val):
                try:
                    v = float(str(val).replace("%","").strip())
                    color = "#38bdf8" if v >= 3.0 else "#94a3b8"
                    return f'<span style="color:{color};font-weight:600;font-family:JetBrains Mono,monospace">{v:.2f}%</span>'
                except Exception:
                    return f'<span style="color:#fff;font-family:JetBrains Mono,monospace">{val}</span>'
            col_formats[ci] = fmt_rate
        elif any(k in c for k in ("score","note","rang")):
            def fmt_score(val):
                try:
                    v = float(val)
                    color = "#10b981" if v >= 65 else "#f59e0b" if v >= 40 else "#f43f5e"
                    return (f'<span style="background:rgba(0,0,0,0.2);border:1px solid {color}55;color:{color};'
                            f'font-weight:800;padding:3px 10px;border-radius:999px;font-family:JetBrains Mono,monospace">{v:.0f}</span>')
                except Exception:
                    return f'<span style="color:#fff;font-family:JetBrains Mono,monospace">{val}</span>'
            col_formats[ci] = fmt_score
        elif any(k in c for k in ("pib","gdp","croissance","growth")):
            def fmt_gdp(val):
                try:
                    v = float(str(val).replace("%","").replace("+","").strip())
                    color = "#10b981" if v > 0 else "#f43f5e" if v < 0 else "#94a3b8"
                    arrow = "▲" if v > 0 else "▼" if v < 0 else "–"
                    return f'<span style="color:{color};font-weight:700;font-family:JetBrains Mono,monospace">{arrow} {v:+.2f}%</span>'
                except Exception:
                    return f'<span style="color:#fff;font-family:JetBrains Mono,monospace">{val}</span>'
            col_formats[ci] = fmt_gdp
        elif any(k in c for k in ("inflation","cpi","ipc")):
            def fmt_inf(val):
                try:
                    v = float(str(val).replace("%","").strip())
                    color = "#f59e0b" if v >= 3.5 else "#10b981" if v <= 2.5 else "#cbd5e1"
                    return f'<span style="color:{color};font-family:JetBrains Mono,monospace">{v:.1f}%</span>'
                except Exception:
                    return f'<span style="color:#fff;font-family:JetBrains Mono,monospace">{val}</span>'
            col_formats[ci] = fmt_inf
        elif any(k in c for k in ("chôm","unem","unemploy")):
            def fmt_unem(val):
                try:
                    v = float(str(val).replace("%","").strip())
                    color = "#f43f5e" if v >= 6.0 else "#10b981" if v <= 4.0 else "#cbd5e1"
                    return f'<span style="color:{color};font-family:JetBrains Mono,monospace">{v:.1f}%</span>'
                except Exception:
                    return f'<span style="color:#fff;font-family:JetBrains Mono,monospace">{val}</span>'
            col_formats[ci] = fmt_unem
        elif ci == 0:
            def fmt_label(val):
                flag = CCY_FLAGS.get(str(val).strip().upper()[:3], "")
                flag_html = f'<span style="font-size:15px;margin-right:5px;">{flag}</span>' if flag else ""
                return (f'<div style="display:flex;align-items:center;justify-content:center;">'
                        f'{flag_html}<span style="font-family:JetBrains Mono,monospace;font-weight:700;color:#fff;">{val}</span></div>')
            col_formats[ci] = fmt_label
    data_rows = [[str(df.iloc[i][col]) for col in headers] for i in range(len(df))]
    legend = [
        {"dot": "#10b981", "label": "Spread / PIB positif"},
        {"dot": "#f43f5e", "label": "Spread / PIB négatif"},
        {"dot": "#38bdf8", "label": "Taux ≥ 3%"},
        {"dot": "#f59e0b", "label": "Inflation > 3.5%"},
    ]
    return _styled_table_html(headers, data_rows, col_formats=col_formats, height=280, legend_items=legend)


def render_rateprob_table(rows):
    if not rows or not all(isinstance(r, list) for r in rows):
        return ""
    headers = rows[0]
    data_rows = rows[1:]
    col_formats = {}
    for ci, col in enumerate(headers):
        c = col.lower()
        if any(k in c for k in ("implied","outcome","décision","action","move")):
            def fmt_outcome(val):
                vl = str(val).lower()
                if any(k in vl for k in ("hike","raise","hausse","up","increase")):
                    return (f'<span style="background:rgba(16,185,129,0.12);border:1px solid rgba(16,185,129,0.3);'
                            f'color:#10b981;font-weight:700;padding:3px 10px;border-radius:999px;font-size:12px;">▲ {val}</span>')
                if any(k in vl for k in ("cut","lower","baisse","down","decrease","réduction")):
                    return (f'<span style="background:rgba(244,63,94,0.12);border:1px solid rgba(244,63,94,0.3);'
                            f'color:#f43f5e;font-weight:700;padding:3px 10px;border-radius:999px;font-size:12px;">▼ {val}</span>')
                return (f'<span style="background:rgba(148,163,184,0.08);border:1px solid rgba(148,163,184,0.2);'
                        f'color:#94a3b8;font-weight:600;padding:3px 10px;border-radius:999px;font-size:12px;">— {val}</span>')
            col_formats[ci] = fmt_outcome
        elif any(k in c for k in ("prob","probability","%","chance","likelihood")):
            def fmt_prob(val):
                try:
                    v = float(str(val).replace("%","").strip())
                    color = "#10b981" if v >= 70 else "#f59e0b" if v >= 40 else "#f43f5e"
                    bar_w = max(4, min(100, int(v)))
                    return (f'<div style="display:flex;flex-direction:column;align-items:center;gap:4px;min-width:80px;">'
                            f'<span style="color:{color};font-weight:700;font-family:JetBrains Mono,monospace">{v:.0f}%</span>'
                            f'<div style="width:64px;height:4px;background:rgba(255,255,255,0.06);border-radius:999px;overflow:hidden;">'
                            f'<div style="width:{bar_w}%;height:100%;background:{color};border-radius:999px;"></div>'
                            f'</div></div>')
                except Exception:
                    return f'<span style="color:#cbd5e1;font-family:JetBrains Mono,monospace">{val}</span>'
            col_formats[ci] = fmt_prob
        elif any(k in c for k in ("bank","banque","institution","central")):
            def fmt_bank(val):
                key = str(val).split("/")[0].strip().upper()[:3]
                flag = CCY_FLAGS.get(key, "🏦")
                return (f'<div style="display:flex;align-items:center;gap:7px;justify-content:center;">'
                        f'<span style="font-size:16px;">{flag}</span>'
                        f'<span style="color:#fff;font-weight:600;font-size:13px;">{val}</span></div>')
            col_formats[ci] = fmt_bank
        elif any(k in c for k in ("date","meeting","réunion","time","when")):
            def fmt_date(val):
                return f'<span style="color:#cbd5e1;font-family:JetBrains Mono,monospace;font-size:12px;">{val}</span>'
            col_formats[ci] = fmt_date
        elif any(k in c for k in ("rate","taux","current","actuel")):
            def fmt_rate_rp(val):
                try:
                    v = float(str(val).replace("%","").strip())
                    color = "#38bdf8" if v >= 3.0 else "#94a3b8"
                    return f'<span style="color:{color};font-weight:600;font-family:JetBrains Mono,monospace">{v:.2f}%</span>'
                except Exception:
                    return f'<span style="color:#cbd5e1;font-family:JetBrains Mono,monospace">{val}</span>'
            col_formats[ci] = fmt_rate_rp
    legend = [
        {"dot": "#10b981", "label": "Hike / Hausse"},
        {"dot": "#f43f5e", "label": "Cut / Baisse"},
        {"dot": "#94a3b8", "label": "Hold / Stable"},
        {"dot": "#f59e0b", "label": "Prob. 40–69%"},
    ]
    return _styled_table_html(headers, data_rows, col_formats=col_formats, height=300, legend_items=legend)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def sparkline(values, color="#10b981", height=44):
    def hex_to_rgb(h):
        h = h.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    rgb = hex_to_rgb(color) if isinstance(color, str) and color.startswith("#") else (16, 185, 129)
    fig = go.Figure(go.Scatter(
        y=values, mode="lines",
        line=dict(color=color, width=2),
        fill="tozeroy",
        fillcolor=f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0.08)",
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
    return f'<span style="color:{color};font-weight:700;">{arrow} {abs(chg):.2f}%</span>'

def regime_dot(sentiment):
    s = (sentiment or "").lower()
    if "bull" in s or "risk on" in s: return "🟢"
    if "bear" in s or "risk off" in s: return "🔴"
    return "⚪"


# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
utc_now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC · %Y-%m-%d")
auto_sentiment, sentiment_color = detect_market_sentiment()

# ── Risk sentiment computed once, used in Comparison + Insights ──
risk_sentiment = compute_risk_sentiment(MARKET_ASSETS)

st.markdown(f"""
<div class="topbar">
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;
                background:linear-gradient(135deg,#7c3aed,#0891b2);box-shadow:0 6px 18px rgba(124,58,237,.35);">📈</div>
    <div>
      <div class="topbar-title">FX INTERMARKET PRO</div>
      <div class="topbar-sub">Terminal fondamental · signaux intermarché · WTI ↔ CAD</div>
    </div>
  </div>
  <div style="text-align:right;">
    <div style="margin-bottom:6px;">
      <span style="padding:6px 14px;border-radius:999px;background:rgba(255,255,255,0.03);
                   border:1px solid rgba(255,255,255,0.07);font-weight:700;color:#cbd5e1;">
        {regime_dot(auto_sentiment)} Régime: {auto_sentiment}
      </span>
    </div>
    <div class="topbar-ts">{utc_now}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Paramètres")
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    auto_refresh = st.checkbox("Auto-refresh", value=True)
    interval = st.slider("Intervalle (sec)", min_value=60, max_value=900, value=120, step=30)
    kpi_count = st.selectbox("Paires KPI affichées", options=[3, 4, 6, 9], index=2)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Actions")
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    if st.button("⚡ Forcer mise à jour"):
        ok = refresh_and_persist()
        st.success("✓ Mise à jour terminée") if ok else st.error("✗ Échec — consulter les logs")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Export")
    st.markdown('<div class="sidebar-section"><div style="color:#cbd5e1;font-size:13px;">Configurez votre clé API pour publier vers des services externes.</div></div>', unsafe_allow_html=True)

if auto_refresh:
    try:
        start_background_updater(interval_seconds=interval)
    except Exception:
        pass

# ─────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────
tab_macro, tab_sentiment, tab_compare, tab_intermarket, tab_insights, tab_logs = st.tabs(
    ["🏛  Macro", "🎯  Sentiment", "🔄  Comparaison", "📊  Commodités", "🔎  Insights", "🗄  Logs"]
)

# ═══════════════════════════════════════════
# TAB — MACRO
# ═══════════════════════════════════════════
with tab_macro:
    st.markdown(
        '<div style="font-size:13px;font-weight:700;text-transform:uppercase;'
        'letter-spacing:0.1em;color:#94a3b8;margin-bottom:12px;">'
        '📊 Matrice Juridictionnelle Fondamentale</div>',
        unsafe_allow_html=True
    )

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

    try:
        html_table = render_macro_table(df_macro)
        components.html(html_table, height=430, scrolling=False)
    except Exception as e:
        st.warning(f"Rendu HTML indisponible ({e}) — affichage dataframe.")
        st.dataframe(df_macro, use_container_width=True, height=360)

    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:13px;font-weight:700;text-transform:uppercase;'
        'letter-spacing:0.1em;color:#94a3b8;margin-bottom:12px;">'
        '📈 Évolution des Taux Directeurs</div>',
        unsafe_allow_html=True
    )

    palette = ["#7c3aed", "#0891b2", "#10b981", "#f59e0b", "#f43f5e", "#60a5fa"]
    fig = go.Figure()
    for i, (ccy, rates) in enumerate(HIST_RATE.items()):
        fig.add_trace(go.Scatter(
            y=rates, x=list(range(len(rates))),
            mode="lines+markers", name=ccy,
            line=dict(color=palette[i % len(palette)], width=2.5),
            marker=dict(size=5),
        ))
    fig.update_layout(
        height=360,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", family="Inter"),
        xaxis=dict(title="Période", gridcolor="rgba(255,255,255,.04)", linecolor="rgba(255,255,255,.06)", tickfont=dict(size=11)),
        yaxis=dict(title="Taux (%)", gridcolor="rgba(255,255,255,.04)", linecolor="rgba(255,255,255,.06)", tickfont=dict(size=11)),
        legend=dict(bgcolor="rgba(13,20,36,.9)", bordercolor="rgba(255,255,255,.06)", borderwidth=1, font=dict(size=12)),
        hovermode="x unified",
        margin=dict(l=8, r=8, t=8, b=8),
    )
    st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════
# TAB — SENTIMENT / KPI
# ═══════════════════════════════════════════
with tab_sentiment:
    st.markdown('<div style="font-weight:700;color:#cbd5e1;margin-bottom:8px;">Core FX Indicators</div>', unsafe_allow_html=True)

    fx_items = list(FX_RATES.items())[:kpi_count]
    for row in [fx_items[i:i+3] for i in range(0, len(fx_items), 3)]:
        cols = st.columns(len(row))
        for col, (pair, info) in zip(cols, row):
            rate  = info.get("rate", 0) or 0
            chg   = info.get("chg",  0) or 0.0
            color = "#10b981" if chg >= 0 else "#f43f5e"
            hist  = [round(rate * (0.994 + i*0.0015 + (0.001 if i%3==0 else 0)), 6) for i in range(16)]
            with col:
                st.markdown(f"""
                <div class="kpi">
                  <div style="font-size:11px;color:#cbd5e1;font-weight:700;">{pair}</div>
                  <div style="font-family:'JetBrains Mono',monospace;font-size:20px;font-weight:800;color:#fff;margin-top:6px;">{rate:.4f}</div>
                  <div style="margin-top:6px;">{delta_html(chg)}</div>
                </div>
                """, unsafe_allow_html=True)
                st.plotly_chart(sparkline(hist, color=color), use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div style="height:18px;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-weight:700;color:#cbd5e1;margin-bottom:8px;">Market Assets Snapshot</div>', unsafe_allow_html=True)
    for col, (key, icon, label) in zip(
        st.columns(4),
        [("VIX","🌊","VIX"),("WTI_CRUDE","🛢","WTI Crude"),("US_500","📈","S&P 500"),("GOLD","✦","Gold Spot")]
    ):
        a = MARKET_ASSETS.get(key, {"price":"—","chg":0})
        with col:
            st.markdown(f"""
            <div class="kpi">
              <div style="font-size:12px;color:#cbd5e1;">{icon} {label}</div>
              <div style="font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:800;color:#fff;margin-top:6px;">{a.get('price') or '—'}</div>
              <div style="margin-top:6px;">{delta_html(a.get('chg',0) or 0)}</div>
            </div>
            """, unsafe_allow_html=True)

# ═══════════════════════════════════════════
# TAB — COMPARISON
# ═══════════════════════════════════════════
with tab_compare:
    st.markdown('<div style="font-weight:700;color:#cbd5e1;margin-bottom:12px;">Comparaison FX & Signal Prédictif</div>', unsafe_allow_html=True)

    # ── Risk sentiment panel (VIX + SP500) ──
    st.markdown(risk_sentiment_panel_html(risk_sentiment), unsafe_allow_html=True)

    ccy_list = list(MACRO.keys())
    c1, c2 = st.columns(2)
    with c1:
        base_ccy  = st.selectbox("Devise Long (Base)",          ccy_list, index=min(6,len(ccy_list)-1))
    with c2:
        quote_ccy = st.selectbox("Devise Short (Contrepartie)", ccy_list, index=0)

    if base_ccy == quote_ccy:
        st.markdown('<div style="background:#2b2f36;padding:10px;border-radius:8px;color:#f59e0b;">⚠ Sélectionnez deux devises distinctes.</div>', unsafe_allow_html=True)
    else:
        # Per-currency risk chips
        st.markdown(ccy_risk_chips_html(base_ccy, quote_ccy, risk_sentiment), unsafe_allow_html=True)

        b_data, q_data = MACRO.get(base_ccy,{}), MACRO.get(quote_ccy,{})
        spreads = compute_spreads(b_data, q_data)
        df_comp = build_comparison_table(base_ccy, quote_ccy, b_data, q_data, spreads)
        try:
            comp_html = render_comparison_table(df_comp)
            components.html(comp_html, height=340, scrolling=False)
        except Exception:
            st.dataframe(df_comp, use_container_width=True)

        # ── Signal prédictif — intègre le bonus risque ──
        regime_tuple = regime_weights("Automatique", auto_sentiment)
        wti_bull  = MARKET_ASSETS.get("WTI_CRUDE",{}).get("chg",0) > 0
        wti_bonus = wti_adjustment(base_ccy, quote_ccy, wti_bull)

        # Risk sentiment bonus: base bias minus quote bias
        rs_bonus = risk_sentiment["bonus"].get(base_ccy, 0) - risk_sentiment["bonus"].get(quote_ccy, 0)

        expected  = (
            spreads[2] * regime_tuple[1] +
            spreads[1] * regime_tuple[2] +
            spreads[0] * regime_tuple[3] +
            wti_bonus  +
            rs_bonus         # ← VIX/SP500 adjustment
        )
        score_pct   = normalize_score(expected)
        bull        = score_pct >= 50
        bar_w       = score_pct if bull else (100 - score_pct)
        bar_color   = "linear-gradient(90deg,#10b981,#34d399)" if bull else "linear-gradient(90deg,#f43f5e,#fb7185)"
        label       = f"BULLISH — {bar_w}%" if bull else f"BEARISH — {bar_w}%"
        color       = "#10b981" if bull else "#f43f5e"
        rs_regime   = risk_sentiment["regime"]
        rs_color    = risk_sentiment["color"]
        rs_icon     = risk_sentiment["icon"]
        rs_net      = rs_bonus
        rs_net_str  = f"{rs_net:+.1f}pts" if rs_net != 0 else "neutre"
        rs_net_col  = "#10b981" if rs_net > 0 else "#f43f5e" if rs_net < 0 else "#94a3b8"

        st.markdown(f"""
        <div style="background:linear-gradient(180deg,var(--panel),var(--panel-2));padding:18px;
                    border-radius:12px;border:1px solid var(--border);margin-top:14px;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;">
            <div>
              <div style="font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;">
                Signal Fondamental + Risque
              </div>
              <div style="font-size:22px;font-weight:800;color:{color};">{label}</div>
            </div>
            <div style="text-align:right;">
              <div style="font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;">
                Ajustement VIX/SP500
              </div>
              <div style="font-size:14px;font-weight:700;color:{rs_color};">{rs_icon} {rs_regime}</div>
              <div style="font-size:12px;color:{rs_net_col};font-weight:600;font-family:'JetBrains Mono',monospace;">
                {rs_net_str} sur ce trade
              </div>
            </div>
          </div>
          <div style="height:8px;background:rgba(255,255,255,0.04);border-radius:999px;margin-top:14px;overflow:hidden;">
            <div style="width:{bar_w}%;height:100%;background:{bar_color};border-radius:999px;transition:width 400ms ease;"></div>
          </div>
          <div style="display:flex;justify-content:space-between;margin-top:4px;">
            <span style="font-size:10px;color:#94a3b8;">0%</span>
            <span style="font-size:10px;color:#94a3b8;">Conviction: {bar_w}%</span>
            <span style="font-size:10px;color:#94a3b8;">100%</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

# ═══════════════════════════════════════════
# TAB — COMMODITIES / INTERMARKET
# ═══════════════════════════════════════════
RATEPROB_CACHE = os.path.join(os.path.dirname(__file__), "rateprob_cache.json")
RATEPROB_URL   = "https://rateprobability.com"

def _load_rateprob_cache():
    try:
        with open(RATEPROB_CACHE,"r",encoding="utf-8") as f: return json.load(f)
    except Exception: return {"ts":None,"data":[]}

def _save_rateprob_cache(data):
    try:
        with open(RATEPROB_CACHE,"w",encoding="utf-8") as f:
            json.dump({"ts":datetime.utcnow().isoformat()+"Z","data":data},f,indent=2,ensure_ascii=False)
    except Exception: pass

def fetch_rateprobability(force=False, ttl_seconds=600):
    cache = _load_rateprob_cache()
    if not force and cache.get("ts"):
        try:
            age = (datetime.utcnow()-datetime.fromisoformat(cache["ts"].replace("Z",""))).total_seconds()
            if age < ttl_seconds: return cache.get("data",[]), cache.get("ts")
        except Exception: pass
    if BeautifulSoup is None: return cache.get("data",[]), cache.get("ts")
    try:
        resp = requests.get(RATEPROB_URL, timeout=10, headers={"User-Agent":"fx-terminal/2.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text,"html.parser")
        table = None
        for h in soup.find_all(["h1","h2","h3","h4","h5"]):
            if "upcoming meeting" in h.get_text(strip=True).lower():
                table = h.find_next("table")
                if table: break
        rows = []
        if table:
            ths = table.find("tr")
            if ths: rows.append([t.get_text(strip=True) for t in ths.find_all(["th","td"])])
            for tr in table.find_all("tr")[1:]:
                cells=[td.get_text(strip=True) for td in tr.find_all(["td","th"])]
                if cells: rows.append(cells)
        if not rows:
            for tbl in soup.find_all("table"):
                hdr=" ".join(th.get_text(strip=True).lower() for th in tbl.find_all("th"))
                if any(k in hdr for k in ["bank","probability","meeting","rate","implied"]):
                    ths=tbl.find("tr")
                    if ths: rows.append([t.get_text(strip=True) for t in ths.find_all(["th","td"])])
                    for tr in tbl.find_all("tr")[1:]:
                        cells=[td.get_text(strip=True) for td in tr.find_all(["td","th"])]
                        if cells: rows.append(cells)
                    break
        if rows:
            _save_rateprob_cache(rows)
            return rows, datetime.utcnow().isoformat()+"Z"
        return cache.get("data",[]), cache.get("ts")
    except Exception: return cache.get("data",[]), cache.get("ts")

with tab_intermarket:
    st.markdown('<div style="font-weight:700;color:#cbd5e1;margin-bottom:8px;">Intermarket Analytics & Commodities</div>', unsafe_allow_html=True)
    for col,(key,icon,label) in zip(
        st.columns(3),
        [("GOLD","✦","Gold Spot"),("WTI_CRUDE","🛢","WTI Crude"),("US_500","📈","S&P 500")]
    ):
        a = MARKET_ASSETS.get(key,{"price":"—","chg":0})
        with col:
            st.markdown(f"<div class='kpi'><div style='font-size:12px;color:#cbd5e1;'>{icon} {label}</div><div style='font-weight:800;font-family:JetBrains Mono;font-size:18px;margin-top:6px;color:#fff;'>{a.get('price') or '—'}</div><div style='margin-top:6px;'>{delta_html(a.get('chg',0) or 0)}</div></div>", unsafe_allow_html=True)

    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-weight:700;color:#cbd5e1;margin-bottom:8px;">Market-implied Upcoming Meetings (RateProbability)</div>', unsafe_allow_html=True)
    rp_force = st.button("🔄 Forcer refresh RateProbability")
    rows, ts = fetch_rateprobability(force=rp_force)
    if not rows:
        st.info("Impossible de récupérer RateProbability — cache vide ou erreur réseau.")
    else:
        st.markdown(f'<div style="font-size:11px;color:#94a3b8;margin-bottom:6px;font-family:JetBrains Mono">Dernière récupération: {ts}</div>', unsafe_allow_html=True)
        if isinstance(rows,list) and rows and all(isinstance(r,list) for r in rows):
            try:
                rp_html = render_rateprob_table(rows)
                components.html(rp_html, height=370, scrolling=False)
            except Exception:
                try: df_rp = pd.DataFrame(rows[1:], columns=rows[0])
                except Exception: df_rp = pd.DataFrame(rows[1:])
                st.dataframe(df_rp, use_container_width=True)
        else:
            st.table(rows)

# ═══════════════════════════════════════════
# TAB — INSIGHTS
# ═══════════════════════════════════════════
with tab_insights:
    st.markdown('<div style="font-weight:700;color:#cbd5e1;margin-bottom:12px;">Insights & Recommandations</div>', unsafe_allow_html=True)

    # ── Risk sentiment panel ──
    st.markdown(risk_sentiment_panel_html(risk_sentiment), unsafe_allow_html=True)

    # ── Ranked pairs with risk-adjusted scores ──
    regime_tuple = regime_weights("Automatique", auto_sentiment)
    wti_bull     = MARKET_ASSETS.get("WTI_CRUDE",{}).get("chg",0) > 0
    ranked       = rank_all_pairs(regime_tuple, wti_bull)

    # Apply risk-sentiment bonus to each pair score
    rs_bonus_map = risk_sentiment["bonus"]
    rs_fx_map    = risk_sentiment["fx_impact"]
    rs_regime    = risk_sentiment["regime"]
    rs_intensity = abs(risk_sentiment["score"] - 50) / 50.0

    def apply_rs_bonus(item):
        pair = item.get("pair","")
        parts = pair.replace("/",":").split(":")
        base  = parts[0] if len(parts) >= 1 else ""
        quote = parts[1] if len(parts) >= 2 else ""
        net   = rs_bonus_map.get(base, 0) - rs_bonus_map.get(quote, 0)
        adjusted_raw = item.get("raw", 0) + net
        # Re-normalize: simple clamp to 0-100 range
        adjusted_pct = max(0, min(100, item.get("score_pct", 50) + int(net)))
        return {**item, "score_pct": adjusted_pct, "adjusted_raw": adjusted_raw, "rs_net": net}

    ranked_adj = [apply_rs_bonus(r) for r in ranked]
    top_bull   = sorted([r for r in ranked_adj if r["score_pct"] >= 50], key=lambda x: -x["score_pct"])[:4]
    top_bear   = sorted([r for r in ranked_adj if r["score_pct"] < 50],  key=lambda x:  x["score_pct"])[:4]

    # ── Column headers ──
    col_bull_hdr, col_bear_hdr = st.columns(2)
    with col_bull_hdr:
        st.markdown(
            '<div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;'
            'color:#94a3b8;margin-bottom:8px;">🔥 Top Bullish</div>',
            unsafe_allow_html=True
        )
    with col_bear_hdr:
        st.markdown(
            '<div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;'
            'color:#94a3b8;margin-bottom:8px;">❄️ Top Bearish</div>',
            unsafe_allow_html=True
        )

    col_bull, col_bear = st.columns(2)

    def pair_card(item, color, arrow):
        pct      = item.get("score_pct", 0)
        raw      = item.get("raw", 0)
        rs_net   = item.get("rs_net", 0)
        pair     = item.get("pair","—")

        # Parse base/quote for flag display
        parts    = pair.replace("/",":").split(":")
        base_c   = parts[0] if len(parts) >= 1 else ""
        quote_c  = parts[1] if len(parts) >= 2 else ""
        b_flag   = CCY_FLAGS.get(base_c,"")
        q_flag   = CCY_FLAGS.get(quote_c,"")
        b_impact = rs_fx_map.get(base_c,"NEUTRE")
        q_impact = rs_fx_map.get(quote_c,"NEUTRE")

        # Risk chip colors
        imp_colors = {"BULLISH":"#10b981","BEARISH":"#f43f5e","NEUTRE":"#94a3b8"}
        b_col = imp_colors.get(b_impact,"#94a3b8")
        q_col = imp_colors.get(q_impact,"#94a3b8")
        rs_net_col = "#10b981" if rs_net > 0 else "#f43f5e" if rs_net < 0 else "#94a3b8"
        rs_net_str = f"{rs_net:+.1f}" if rs_net != 0 else "±0"

        return f"""
        <div style="padding:14px;border-radius:10px;background:linear-gradient(180deg,var(--panel),var(--panel-2));
                    margin-bottom:8px;border:1px solid rgba(255,255,255,0.06);
                    transition:border-color 150ms ease;"
             onmouseover="this.style.borderColor='rgba(124,58,237,0.3)'"
             onmouseout="this.style.borderColor='rgba(255,255,255,0.06)'">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div>
              <div style="font-weight:800;font-family:'JetBrains Mono',monospace;color:#fff;font-size:15px;margin-bottom:4px;">
                {b_flag}{q_flag} {pair}
              </div>
              <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
                <span style="font-size:10px;color:{b_col};font-weight:700;background:rgba(255,255,255,0.04);
                             padding:2px 7px;border-radius:999px;">{base_c} {b_impact}</span>
                <span style="font-size:10px;color:#94a3b8;">vs</span>
                <span style="font-size:10px;color:{q_col};font-weight:700;background:rgba(255,255,255,0.04);
                             padding:2px 7px;border-radius:999px;">{quote_c} {q_impact}</span>
              </div>
              <div style="margin-top:5px;font-size:11px;color:#94a3b8;">
                Macro: {raw:.2f} · Risque VIX/SP500:
                <span style="color:{rs_net_col};font-weight:700;">{rs_net_str}pts</span>
              </div>
            </div>
            <div style="text-align:right;flex-shrink:0;margin-left:12px;">
              <div style="color:{color};font-weight:800;font-size:18px;">{arrow} {pct}%</div>
            </div>
          </div>
          <div style="height:4px;background:rgba(255,255,255,0.05);border-radius:999px;margin-top:10px;overflow:hidden;">
            <div style="width:{pct}%;height:100%;background:{color};border-radius:999px;opacity:0.75;"></div>
          </div>
        </div>"""

    with col_bull:
        if not top_bull:
            st.info("Aucune paire bullish détectée.")
        for item in top_bull:
            st.markdown(pair_card(item,"#10b981","▲"), unsafe_allow_html=True)

    with col_bear:
        if not top_bear:
            st.info("Aucune paire bearish détectée.")
        for item in top_bear:
            st.markdown(pair_card(item,"#f43f5e","▼"), unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div style="font-weight:700;color:#cbd5e1;margin-bottom:8px;">📅 Catalyseurs à venir</div>', unsafe_allow_html=True)
    for c in [
        {"time":"2026-05-20 · 13:30 UTC","event":"US Nonfarm Payrolls (NFP)","impact":"High","pairs":["USD/*"]},
        {"time":"2026-05-21 · 08:00 UTC","event":"ECB Rate Decision","impact":"High","pairs":["EUR/*"]},
        {"time":"2026-05-22 · 02:00 UTC","event":"BoC Rate Statement","impact":"Medium","pairs":["CAD/*"]},
    ]:
        accent = "#f43f5e" if c["impact"]=="High" else "#f59e0b"
        st.markdown(f"""
        <div style="padding:12px 14px;border-radius:10px;background:linear-gradient(180deg,var(--panel),var(--panel-2));
                    margin-bottom:8px;border:1px solid rgba(255,255,255,0.05);border-left:3px solid {accent};">
          <div style="font-weight:700;color:#fff;">{c['event']}
            <span style="font-size:11px;padding:2px 8px;border-radius:999px;
                         background:rgba(255,255,255,0.05);color:{accent};margin-left:8px;">{c['impact']}</span>
          </div>
          <div style="color:#94a3b8;font-family:'JetBrains Mono',monospace;font-size:12px;margin-top:4px;">{c['time']} · {', '.join(c['pairs'])}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div style="font-weight:700;color:#cbd5e1;margin-bottom:8px;">📰 News & Flux</div>', unsafe_allow_html=True)
    articles = fetch_news(limit=6)
    if articles:
        st.markdown('<div style="background:linear-gradient(180deg,var(--panel),var(--panel-2));border-radius:10px;border:1px solid rgba(255,255,255,0.05);padding:4px 14px;">', unsafe_allow_html=True)
        for i, a in enumerate(articles, 1):
            title = a.get("title") or "Untitled"
            src   = a.get("source") or ""
            ts    = (a.get("publishedAt") or "")[:19].replace("T"," ")
            url   = a.get("url") or "#"
            st.markdown(f"""
            <div style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.04);display:flex;gap:10px;">
              <div style="color:#94a3b8;font-family:'JetBrains Mono',monospace;font-size:11px;width:24px;flex-shrink:0;padding-top:2px;">#{i:02d}</div>
              <div>
                <div><a href="{url}" target="_blank" rel="noopener" style="color:#38bdf8;font-weight:600;text-decoration:none;">{title}</a></div>
                <div style="color:#94a3b8;font-family:'JetBrains Mono',monospace;font-size:11px;margin-top:3px;">{src} · {ts}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Aucune news disponible — vérifiez NEWS_API_KEY ou le cache local.")

# ═══════════════════════════════════════════
# TAB — LOGS
# ═══════════════════════════════════════════
with tab_logs:
    st.markdown('<div style="font-weight:700;color:#cbd5e1;margin-bottom:8px;">System Logs</div>', unsafe_allow_html=True)
    try: logs = load_update_log()
    except Exception: logs = []
    if logs:
        st.markdown('<div style="background:linear-gradient(180deg,var(--panel),var(--panel-2));border-radius:10px;border:1px solid rgba(255,255,255,0.05);overflow:hidden;">', unsafe_allow_html=True)
        for entry in logs:
            ok = str(entry.get("status","")).lower() in ("ok","success","200")
            sc = "#10b981" if ok else "#f43f5e"
            st.markdown(f"""
            <div style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#cbd5e1;
                        padding:10px 14px;border-bottom:1px solid rgba(255,255,255,0.03);display:flex;gap:16px;">
              <span style="color:#94a3b8;width:160px;flex-shrink:0;">{entry.get('ts','—')}</span>
              <span>{entry.get('session','—')} · {entry.get('trigger','—')}</span>
              <span style="color:{sc};">{entry.get('status','—')}</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Aucun log disponible.")

# ─────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"<div style='display:flex;justify-content:space-between;color:#94a3b8;font-size:12px;padding-bottom:8px;'>"
    f"<div>Sources: Yahoo Finance (yfinance) · indicateurs fondamentaux pondérés · rateprobability.com</div>"
    f"<div style='font-family:JetBrains Mono,monospace;'>{utc_now}</div>"
    f"</div>",
    unsafe_allow_html=True,
)
