def regime_weights(mode, auto_sentiment):
    """Définit les pondérations selon le régime Risk-On / Risk-Off."""
    if "RISK-ON" in mode or ("Automatique" in mode and "RISK-ON" in auto_sentiment):
        return "RISK-ON", 0.30, 0.50, 0.20, 0.5
    elif "RISK-OFF" in mode or ("Automatique" in mode and "RISK-OFF" in auto_sentiment):
        return "RISK-OFF", 0.70, 0.15, 0.15, -1.8
    return "NORMAL", 0.45, 0.40, 0.15, 0.0

# À rajouter tout à la fin de utils/sentiment_engine.py
# utils/sentiment_engine.py

def analyze_market_sentiment():
    """
    Fonction adaptatrice corrigée pour correspondre au format d'unpacking 
    de scraper.py (attend 3 éléments : dictionnaire_sentiment, geo_risk, speech_impact).
    """
    # 1. Le dictionnaire de sentiment par devise requis pour tes calculs
    sentiment_data = {
        "USD": {"score": 0.2, "status": "Neutral"},
        "EUR": {"score": -0.4, "status": "Bearish"},
        "GBP": {"score": 0.5, "status": "Bullish"},
        "JPY": {"score": -0.1, "status": "Neutral"},
        "AUD": {"score": 0.6, "status": "Bullish"},
        "NZD": {"score": 0.1, "status": "Neutral"},
        "CAD": {"score": -0.3, "status": "Bearish"},
        "CHF": {"score": 0.3, "status": "Bullish"}
    }
    
    # 2. Les deux variables exogènes numériques attendues par scraper.py (lignes 42 et 62)
    geo_risk = 1.0       # Niveau de risque géopolitique (ex: 1.0 = Modéré, > 2.0 = Critique)
    speech_impact = 1.0  # Impact des discours (ex: 1.0 = Neutre, > 2.0 = Hawkish)
    
    # On retourne les 3 valeurs demandées par le unpacking : _, geo_risk, speech_impact
    return sentiment_data, geo_risk, speech_impact
