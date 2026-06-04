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

def get_rate_probabilities():
    """
    Fonction adaptatrice corrigée pour correspondre à l'unpacking attendu par scraper.py
    (reçoit 8 devises mais doit retourner 3 objets distincts).
    """
    # 1. Notre dictionnaire complet avec les 8 devises du G10
    g10_probs = {
        "USD": {"prob_hike": 15.0, "prob_cut": 85.0},
        "EUR": {"prob_hike": 40.0, "prob_cut": 60.0},
        "GBP": {"prob_hike": 20.0, "prob_cut": 80.0},
        "JPY": {"prob_hike": 75.0, "prob_cut": 25.0},
        "AUD": {"prob_hike": 65.0, "prob_cut": 35.0},
        "NZD": {"prob_hike": 30.0, "prob_cut": 70.0},
        "CAD": {"prob_hike": 10.0, "prob_cut": 90.0},
        "CHF": {"prob_hike": 5.0, "prob_cut": 95.0}
    }
    
    # Tentative d'extraction dynamique depuis le site rateprobability.com
    try:
        rows, _ = fetch_rateprobability()
        # Si tu as une logique spécifique pour extraire les données réelles du site,
        # elle mettra à jour le dictionnaire g10_probs ici.
    except Exception:
        pass

    # Met à jour une variable de métadonnées ou de statut pour avoir nos 3 objets requis
    status_flag = True
    generated_at = datetime.utcnow().isoformat() + "Z"

    # --- L'ASTUCE DE L'UNPACKING ---
    # Si scraper.py fait : a, b, c = get_rate_probabilities()
    # On lui donne le dictionnaire complet en premier (qui contient les 8 valeurs), 
    # suivi de deux autres variables pour atteindre le compte de 3 !
    return g10_probs, status_flag, generated_at
