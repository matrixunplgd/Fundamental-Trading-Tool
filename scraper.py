# scraper.py
import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
import yfinance as yf

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

utils_folder = "utilitaires" if (ROOT_DIR / "utilitaires").exists() else "utils"
try:
    if utils_folder == "utilitaires":
        from utilitaires.rateprob import get_rate_probabilities
        from utilitaires.sentiment_engine import analyze_market_sentiment
        from utilitaires.news import fetch_news
    else:
        from utils.rateprob import get_rate_probabilities
        from utils.sentiment_engine import analyze_market_sentiment
        from utils.news import fetch_news
except ModuleNotFoundError:
    from rateprob import get_rate_probabilities
    from sentiment_engine import analyze_market_sentiment
    from news import fetch_news

def get_bond_yield(ticker):
    """Récupère dynamiquement le rendement obligataire actuel à 10 ans via Yahoo Finance"""
    try:
        bond = yf.Ticker(ticker)
        # On prend le dernier cours de clôture disponible
        hist = bond.history(period="1d")
        if not hist.empty:
            return round(hist['Close'].iloc[-1], 2)
    except:
        pass
    return 0.0

def run_global_scraper():
    print("Démarrage du scraping global haute précision pour le complexe G10...")
    
    # 1. Extraction des sous-modules
    probs = get_rate_probabilities()
    sentiment_data, geo_risk, speech_impact = analyze_market_sentiment()
    articles_presse = fetch_news(limit=6)
    
    # 2. Récupération des rendements obligataires à 10 ans (Moteurs réels des devises)
    # US10Y (^TNX), EU10Y/Bund (DE10Y.F), etc.
    yields = {
        "USD": get_bond_yield("^TNX"),
        "EUR": get_bond_yield("DE10Y.F"),
        "GBP": get_bond_yield("GJGB10.F"),
        "JPY": get_bond_yield("GJGBC10.F"),
        "AUD": get_bond_yield("GAYGB10.F"),
        "CAD": get_bond_yield("GCAN10Y.F"),
        "CHF": get_bond_yield("GCHBK10.F"),
        "NZD": 4.25 # Fallback constant si ticker obscur
    }

    # 3. Structure Macro-Économique Exhaustive (Données enrichies pour l'Accuracy)
    macro_structure = {
        "USD": {"cb": "FED", "rate": 5.25, "bias": "Neutral", "gdp": 2.5, "cpi": 2.9, "unem": 4.1, "pmi": 51.2, "retail_sales": 0.4},
        "EUR": {"cb": "ECB", "rate": 2.15, "bias": "Hawkish", "gdp": 1.2, "cpi": 2.3, "unem": 6.5, "pmi": 48.9, "retail_sales": -0.2},
        "GBP": {"cb": "BOE", "rate": 3.75, "bias": "Holding Restrictive", "gdp": 0.9, "cpi": 3.0, "unem": 4.7, "pmi": 50.5, "retail_sales": 0.1},
        "JPY": {"cb": "BOJ", "rate": 0.75, "bias": "Tightening", "gdp": 0.8, "cpi": 2.5, "unem": 2.4, "pmi": 49.6, "retail_sales": 0.8},
        "AUD": {"cb": "RBA", "rate": 4.35, "bias": "Hawkish", "gdp": 1.8, "cpi": 3.2, "unem": 4.1, "pmi": 52.1, "retail_sales": 0.5},
        "NZD": {"cb": "RBNZ", "rate": 5.50, "bias": "Neutral", "gdp": 1.1, "cpi": 3.0, "unem": 5.0, "pmi": 47.8, "retail_sales": -0.4},
        "CAD": {"cb": "BOC", "rate": 4.75, "bias": "Dovish", "gdp": 1.3, "cpi": 2.2, "unem": 6.3, "pmi": 49.3, "retail_sales": 0.0},
        "CHF": {"cb": "SNB", "rate": 1.25, "bias": "Uncertain", "gdp": 1.3, "cpi": 1.1, "unem": 2.5, "pmi": 45.2, "retail_sales": -0.1}
    }
    
    # 4. Modèle de Scoring Algorithmique Multi-Confluences
    scores = {}
    for ccy, info in macro_structure.items():
        score = 0
        
        # Axe A : Inflation vs Target (2.0%)
        if info["cpi"] > 2.5: score += 1.5
        if info["cpi"] < 1.8: score -= 1.5
        
        # Axe B : Croissance & Santé Économique (PMI de rupture à 50)
        if info["pmi"] > 50.0: score += 1.0
        else: score -= 1.0
        
        if info["retail_sales"] > 0.2: score += 0.5
        
        # Axe C : Marché de l'emploi
        if info["unem"] < 4.2: score += 1.0
        
        # Axe D : Dynamique des OIS (Taux Implicites)
        ccy_prob = probs.get(ccy, {"prob_hike": 0, "prob_cut": 0})
        if ccy_prob.get("prob_hike", 0) > 60: score += 2.5
        if ccy_prob.get("prob_cut", 0) > 60: score -= 2.5
        
        # Axe E : Sentiment Fondamental Individuel Extrait
        ccy_sent = sentiment_data.get(ccy, {"score": 0})
        if ccy_sent.get("score", 0) > 0.3: score += 1.0
        elif ccy_sent.get("score", 0) < -0.3: score -= 1.0
        
        # Axe F : Flux de Capitaux & Risques Globaux (Géopolitique)
        if geo_risk > 2:
            if ccy in ["USD", "JPY", "CHF"]: score += 2.0  # Safe Havens achetés
            if ccy in ["AUD", "NZD", "CAD"]: score -= 2.0  # Cycliques / Matières premières pénalisées
            
        scores[ccy] = round(score, 2)

    # 5. Injection des données obligataires collectées pour affichage dans l'app
    for ccy in macro_structure:
        macro_structure[ccy]["yield_10y"] = yields.get(ccy, 0.0)

    # 6. Écriture finale dans le cache
    output = {
        "metadata": {
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "geo_risk_level": "CRITIQUE" if geo_risk > 2 else "MODÉRÉ",
            "speech_tone": "HAWKISH" if speech_impact > 2 else "NEUTRAL"
        },
        "macro_data": macro_structure,
        "probs": probs,
        "scores": scores,
        "news_feed": articles_presse
    }
    
    with open("news_cache.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
    print("news_cache.json synchronisé avec succès.")
