# utils/recommendations.py
from .fx_calculations import compute_spreads, normalize_score
from data import MACRO
from .commodities_logic import wti_adjustment

def score_pair(base_ccy, quote_ccy, regime_weights_tuple, wti_is_bullish):
    b = MACRO.get(base_ccy, {})
    q = MACRO.get(quote_ccy, {})
    interest_spread, yield_spread, score_diff = compute_spreads(b, q)
    _, w_score, w_yield, w_rate, _ = regime_weights_tuple
    wti_bonus = wti_adjustment(base_ccy, quote_ccy, wti_is_bullish)
    expected_move = (score_diff * w_score) + (yield_spread * w_yield) + (interest_spread * w_rate) + wti_bonus
    pct = normalize_score(expected_move)
    return pct, expected_move

def rank_unique_pairs(regime_weights_tuple, wti_is_bullish):
    """
    Retourne une liste triée d'entrées uniques par paire non ordonnée.
    Pour chaque combinaison {A,B} on calcule A/B et B/A, on garde la direction la plus forte.
    Résultat: [{'pair':'USD/CHF','dominant':'USD','score_pct':89,'raw':3.16}, ...]
    """
    ccy_list = list(MACRO.keys())
    seen = set()
    results = []

    for i, a in enumerate(ccy_list):
        for b in ccy_list[i+1:]:
            if a == b:
                continue
            # calcule A/B
            pct_ab, raw_ab = score_pair(a, b, regime_weights_tuple, wti_is_bullish)
            # calcule B/A
            pct_ba, raw_ba = score_pair(b, a, regime_weights_tuple, wti_is_bullish)

            # Choisir la direction la plus forte (score le plus élevé)
            if pct_ab >= pct_ba:
                dominant = a
                pair_str = f"{a}/{b}"
                score_pct = pct_ab
                raw = raw_ab
            else:
                dominant = b
                pair_str = f"{b}/{a}"
                score_pct = pct_ba
                raw = raw_ba

            # Normaliser l'affichage: on garde une seule entrée par combinaison
            key = tuple(sorted([a, b]))
            if key in seen:
                continue
            seen.add(key)
            results.append({
                "pair": pair_str,
                "dominant": dominant,
                "score_pct": score_pct,
                "raw": raw,
                "base": pair_str.split("/")[0],
                "quote": pair_str.split("/")[1]
            })

    # Trier par score descendant (les paires où la devise dominante est la plus forte)
    results_sorted = sorted(results, key=lambda x: x["score_pct"], reverse=True)
    return results_sorted
