def regime_weights(mode, auto_sentiment):
    """Définit les pondérations selon le régime Risk-On / Risk-Off."""
    if "RISK-ON" in mode or ("Automatique" in mode and "RISK-ON" in auto_sentiment):
        return "RISK-ON", 0.30, 0.50, 0.20, 0.5
    elif "RISK-OFF" in mode or ("Automatique" in mode and "RISK-OFF" in auto_sentiment):
        return "RISK-OFF", 0.70, 0.15, 0.15, -1.8
    return "NORMAL", 0.45, 0.40, 0.15, 0.0

# À rajouter tout à la fin de utils/sentiment_engine.py

def analyze_market_sentiment():
    """
    Fonction adaptatrice pour le scraper de la LNE Watch Tower.
    Elle appelle ta logique existante et retourne les scores de sentiment 
    requis pour la matrice de confluence macro G10.
    """
    # 1. Si tu as déjà une fonction existante dans ce fichier, appelle-la ici.
    # Exemple : données_brutes = ma_fonction_de_sentiment_existante()
    
    # 2. Structure de secours (Fallback) pour que ton Algorithmic Score 
    # fonctionne pour chaque devise du G10, même si ton scraping de news coupe.
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
    
    # Tu pourras ensuite lier tes résultats scrapés dynamiquement à ce dictionnaire.
    return sentiment_data
