import pandas as pd

def compute_spreads(base_data, quote_data):
    """Calcule les spreads fondamentaux entre deux devises."""
    interest_spread = base_data.get("rate", 0.0) - quote_data.get("rate", 0.0)
    yield_spread = base_data.get("yield_10y", 0.0) - quote_data.get("yield_10y", 0.0)
    score_diff = base_data.get("score", 0) - quote_data.get("score", 0)
    return interest_spread, yield_spread, score_diff

def normalize_score(value, v_min=-4.0, v_max=4.0):
    """Normalise un score entre 1 et 100%."""
    clamped = max(v_min, min(v_max, value))
    score_pct = int(((clamped - v_min) / (v_max - v_min)) * 100)
    return max(1, min(100, score_pct))

def build_comparison_table(base_ccy, quote_ccy, base_data, quote_data, spreads):
    """Construit un tableau comparatif des fondamentaux."""
    interest_spread, yield_spread, score_diff = spreads
    rows = [
        {"Indicateur": "Banque Centrale", base_ccy: base_data.get("cb"), quote_ccy: quote_data.get("cb"), "Spread": "—"},
        {"Indicateur": "Taux Directeur", base_ccy: f"{base_data.get('rate',0):.2f}%", quote_ccy: f"{quote_data.get('rate',0):.2f}%", "Spread": f"{interest_spread:+.2f}%"},
        {"Indicateur": "Rendement 10Y", base_ccy: f"{base_data.get('yield_10y',0):.2f}%", quote_ccy: f"{quote_data.get('yield_10y',0):.2f}%", "Spread": f"{yield_spread:+.2f}%"},
        {"Indicateur": "Score Fondamental", base_ccy: str(base_data.get("score",0)), quote_ccy: str(quote_data.get("score",0)), "Spread": f"{score_diff:+d}"}
    ]
    return pd.DataFrame(rows)
