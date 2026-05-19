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
