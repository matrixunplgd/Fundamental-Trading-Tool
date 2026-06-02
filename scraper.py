# scraper.py
import os
import sys
import json
from datetime import datetime, timezone
import yfinance as yf

# ─── SÉCURITÉ TRAJECTOIRE POUR STREAMLIT CLOUD & GITHUB ACTIONS ───
# On configure le chemin absolu de la racine AVANT de faire le moindre import local
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Maintenant que les chemins sont verrouillés, les imports ne planteront plus
try:
    from utilitaires.rateprob import get_rate_probabilities
    from utilitaires.sentiment_engine import analyze_market_sentiment
    from utilitaires.news import fetch_news
except ModuleNotFoundError:
    # Fallback au cas où l'environnement exécute depuis le sous-dossier directement
    from rateprob import get_rate_probabilities
    from sentiment_engine import analyze_market_sentiment
    from news import fetch_news


def run_global_scraper():
    print("Démarrage du scraping global pour le complexe G10...")
    
    # 1. Récupération des probabilités, sentiments et news via tes utilitaires
    probs = get_rate_probabilities()
    _, geo_risk, speech_impact = analyze_market_sentiment()
    
    # Intégration de NewsAPI (récupère les 6 derniers articles financiers mondiaux)
    articles_presse = fetch_news(limit=6)
    
    # 2. Structure exhaustive avec TOUTES tes devises (G10 Matrix)
    macro_structure = {
        "USD": {"cb": "FED", "rate": 5.25, "bias": "Neutral", "gdp": 2.5, "cpi": 2.9, "unem": 4.1},
        "EUR": {"cb": "ECB", "rate": 2.15, "bias": "Hawkish", "gdp": 1.2, "cpi": 2.3, "unem": 6.5},
        "GBP": {"cb": "BOE", "rate": 3.75, "bias": "Holding Restrictive", "gdp": 0.9, "cpi": 3.0, "unem": 4.7},
        "JPY": {"cb": "BOJ", "rate": 0.75, "bias": "Tightening", "gdp": 0.8, "cpi": 2.5, "unem": 2.4},
        "AUD": {"cb": "RBA", "rate": 4.35, "bias": "Hawkish", "gdp": 1.8, "cpi": 3.2, "unem": 4.1},
        "NZD": {"cb": "RBNZ", "rate": 5.50, "bias": "Neutral", "gdp": 1.1, "cpi": 3.0, "unem": 5.0},
        "CAD": {"cb": "BOC", "rate": 4.75, "bias": "Dovish", "gdp": 1.3, "cpi": 2.2, "unem": 6.3},
        "CHF": {"cb": "SNB", "rate": 1.25, "bias": "Uncertain", "gdp": 1.3, "cpi": 1.1, "unem": 2.5}
    }
    
    # 3. Calculs algorithmiques des scores fondamentaux
    scores = {}
    for ccy, info in macro_structure.items():
        score = 0
        if info["cpi"] > 2.5: score += 1
        if info["unem"] < 4.5: score += 1
        
        # Intégration des probabilités de rateprob.py
        ccy_prob = probs.get(ccy, {"prob_hike": 50, "prob_cut": 50})
        if ccy_prob.get("prob_hike", 0) > 60: score += 2
        if ccy_prob.get("prob_cut", 0) > 70: score -= 2
        
        # Gestion du sentiment exogène macro (Financial Juice / Géopolitique)
        if geo_risk > 2:
            if ccy in ["USD", "JPY", "CHF"]: score += 2  # Flux vers les Safe Havens
            if ccy in ["AUD", "NZD", "CAD"]: score -= 2  # Choc sur les Commodity Currencies
            
        scores[ccy] = score

    # 4. Packaging unifié de toutes les briques de données
    output = {
        "metadata": {
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "geo_risk_level": "CRITIQUE" if geo_risk > 2 else "MODÉRÉ",
            "speech_tone": "HAWKISH" if speech_impact > 2 else "NEUTRAL"
        },
        "macro_data": macro_structure,
        "probs": probs,
        "scores": scores,
        "news_feed": articles_presse  # Tes articles NewsAPI prêts à l'emploi
    }
    
    # Écriture propre et sécurisée à la racine pour l'application Streamlit
    with open("news_cache.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
    print("news_cache.json synchronisé avec succès.")

if __name__ == "__main__":
    run_global_scraper()
