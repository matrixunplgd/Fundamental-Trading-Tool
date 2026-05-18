def wti_adjustment(base_ccy, quote_ccy, wti_is_bullish):
    """Ajuste le score en fonction du WTI et du CAD."""
    bonus = 0.0
    if wti_is_bullish:
        if base_ccy == "CAD": bonus += 0.85
        if quote_ccy == "CAD": bonus -= 0.85
    else:
        if base_ccy == "CAD": bonus -= 0.50
    return bonus

