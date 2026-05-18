# utils/recommendations.py
from .fx_calculations import compute_spreads, normalize_score
from data import MACRO, MARKET_ASSETS
from .commodities_logic import wti_adjustment

def score_pair(base_ccy, quote_ccy, regime_weights_tuple, wti_is_bullish):
    b = MACRO.get(base_ccy, {})
    q = MACRO.get(quote_ccy, {})
    interest_spread, yield_spread, score_diff = compute_spreads(b, q)
    _, w_score, w_yield, w_rate, beta = regime_weights_tuple
    wti_bonus = wti_adjustment(base_ccy, quote_ccy, wti_is_bullish)
    expected_move = (score_diff * w_score) + (yield_spread * w_yield) + (interest_spread * w_rate) + wti_bonus
    pct = normalize_score(expected_move)
    return pct, expected_move

def rank_all_pairs(regime_weights_tuple, wti_is_bullish):
    """Retourne une liste triée de tuples (pair, score_pct, raw_value)."""
    ccy_list = list(MACRO.keys())
    results = []
    for base in ccy_list:
        for quote in ccy_list:
            if base == quote: continue
            pair = f"{base}/{quote}"
            pct, raw = score_pair(base, quote, regime_weights_tuple, wti_is_bullish)
            results.append({"pair": pair, "base": base, "quote": quote, "score_pct": pct, "raw": raw})
    # trier par score_pct descendant
    results_sorted = sorted(results, key=lambda x: x["score_pct"], reverse=True)
    return results_sorted
