def regime_weights(mode, auto_sentiment):
    """Définit les pondérations selon le régime Risk-On / Risk-Off."""
    if "RISK-ON" in mode or ("Automatique" in mode and "RISK-ON" in auto_sentiment):
        return "RISK-ON", 0.30, 0.50, 0.20, 0.5
    elif "RISK-OFF" in mode or ("Automatique" in mode and "RISK-OFF" in auto_sentiment):
        return "RISK-OFF", 0.70, 0.15, 0.15, -1.8
    return "NORMAL", 0.45, 0.40, 0.15, 0.0

