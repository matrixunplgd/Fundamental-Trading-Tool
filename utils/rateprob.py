# utils/rateprob.py
import requests, json, os, time
from bs4 import BeautifulSoup
from datetime import datetime

CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "rateprob_cache.json")
RATEPROB_URL = "https://rateprobability.com"

def _load_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"ts": None, "data": []}

def _save_cache(data):
    try:
        payload = {"ts": datetime.utcnow().isoformat()+"Z", "data": data}
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def fetch_rateprobability(force=False):
    cache = _load_cache()
    # TTL 10 minutes
    if not force and cache.get("ts"):
        age = (datetime.utcnow() - datetime.fromisoformat(cache["ts"].replace("Z",""))).total_seconds()
        if age < 600:
            return cache["data"], cache["ts"]
    try:
        r = requests.get(RATEPROB_URL, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # heuristique: trouver la table "Upcoming meetings" par texte
        table = None
        for h in soup.find_all(["h2","h3","h4"]):
            if "Upcoming meetings" in h.get_text():
                # cherche table suivante
                table = h.find_next("table")
                break
        rows = []
        if table:
            for tr in table.find_all("tr")[1:]:
                cols = [td.get_text(strip=True) for td in tr.find_all(["td","th"])]
                if not cols: continue
                # adapter selon colonnes trouvées
                rows.append(cols)
        _save_cache(rows)
        return rows, datetime.utcnow().isoformat()+"Z"
    except Exception as e:
        return cache.get("data", []), cache.get("ts")


# ─── FONCTION D'ADAPTATION POUR LE SCRAPER DE LA WATCH TOWER ───
# utils/rateprob.py (Remplacer la fonction à la fin du fichier)

# utils/rateprob.py (Remplace la fonction tout à la fin)

# utils/rateprob.py

def get_rate_probabilities():
    """
    Extrait et structure dynamiquement les probabilités de taux OIS depuis RateProbability.com
    """
    rows, _ = fetch_rateprobability()
    
    # Base par défaut (au cas où le site est inaccessible)
    g10_probs = {
        "USD": {"prob_hike": 0.0, "prob_cut": 0.0, "status": "Hold"},
        "EUR": {"prob_hike": 0.0, "prob_cut": 0.0, "status": "Hold"},
        "GBP": {"prob_hike": 0.0, "prob_cut": 0.0, "status": "Hold"},
        "JPY": {"prob_hike": 0.0, "prob_cut": 0.0, "status": "Hold"},
        "AUD": {"prob_hike": 0.0, "prob_cut": 0.0, "status": "Hold"},
        "NZD": {"prob_hike": 0.0, "prob_cut": 0.0, "status": "Hold"},
        "CAD": {"prob_hike": 0.0, "prob_cut": 0.0, "status": "Hold"},
        "CHF": {"prob_hike": 0.0, "prob_cut": 0.0, "status": "Hold"}
    }
    
    mapping = {
        "FED": "USD", "ECB": "EUR", "BOE": "GBP", 
        "BOJ": "JPY", "RBA": "AUD", "RBNZ": "NZD", 
        "BOC": "CAD", "SNB": "CHF"
    }
    
    if rows:
        try:
            for row in rows:
                if len(row) >= 3:
                    cell_text = row[0].upper()
                    for cb_keyword, ccy in mapping.items():
                        if cb_keyword in cell_text:
                            # Exemple d'extraction : on cherche des chaînes comme 'Hike: 65%' ou 'Cut: 35%' dans les colonnes
                            # Si ton scraping extrait des chaînes propres, on nettoie les symboles '%'
                            try:
                                # Logique de parsing générique selon la structure textuelle observée sur le site
                                if "HIKE" in row[2].upper():
                                    val = float(''.join(filter(str.isdigit, row[2])))
                                    g10_probs[ccy]["prob_hike"] = val
                                    g10_probs[ccy]["prob_cut"] = 100.0 - val
                                elif "CUT" in row[2].upper():
                                    val = float(''.join(filter(str.isdigit, row[2])))
                                    g10_probs[ccy]["prob_cut"] = val
                                    g10_probs[ccy]["prob_hike"] = 100.0 - val
                            except:
                                pass
        except Exception:
            pass # Sécurité anti-plantage si le HTML change
            
    return g10_probs
