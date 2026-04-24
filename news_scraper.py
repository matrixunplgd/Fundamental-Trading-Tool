# news_scraper.py
import requests
import os
from datetime import datetime, timezone

GNEWS_API_KEY = "a2530359ee05f25e94ec6ebc10eff403"  # Remplace par ta clé

def fetch_financial_juice():
    """
    Récupère les dernières actualités sur Trump + banques centrales via GNews API.
    """
    if not GNEWS_API_KEY or GNEWS_API_KEY == "TA_CLE_API_ICI":
        print("⚠️  Clé API GNews manquante. Ajoute-la dans news_scraper.py")
        return []

    url = "https://gnews.io/api/v4/search"
    params = {
        "q": "(Trump OR Fed OR Powell OR BoJ OR Ueda OR BoE OR Bailey OR ECB OR Lagarde OR RBA OR RBNZ OR BoC OR SNB) AND (taux OR inflation OR pétrole OR guerre)",
        "lang": "en",
        "country": "us",
        "max": 15,
        "apikey": GNEWS_API_KEY,
        "sortby": "publishedDesc",
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        articles = data.get("articles", [])
        result = []

        for art in articles:
            # Format attendu par le dashboard
            ts = art.get("publishedAt", "")
            # Convertir ISO 8601 en "24 Apr 20:11"
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                ts = dt.strftime("%d %b %H:%M")
            except:
                ts = datetime.now(timezone.utc).strftime("%d %b %H:%M")

            title = art.get("title", "")
            body = art.get("description", "")[:500]

            # Déterminer les devises concernées
            text = (title + " " + body).lower()
            ccys = []
            if "trump" in text or "fed" in text or "powell" in text:
                ccys.append("USD")
            if "boj" in text or "ueda" in text:
                ccys.append("JPY")
            if "boe" in text or "bailey" in text:
                ccys.append("GBP")
            if "ecb" in text or "lagarde" in text:
                ccys.append("EUR")
            if "rba" in text:
                ccys.append("AUD")
            if "rbnz" in text:
                ccys.append("NZD")
            if "boc" in text:
                ccys.append("CAD")
            if "snb" in text:
                ccys.append("CHF")
            if not ccys:
                ccys = ["USD"]

            # Sentiment basé sur mots-clés (approximatif)
            if any(k in text for k in ["hike", "hawkish", "raise", "surge", "positive"]):
                sentiment = "positive"
            elif any(k in text for k in ["cut", "dovish", "lower", "collapse", "negative"]):
                sentiment = "negative"
            else:
                sentiment = "mixed"

            cat = "Central Bank" if any(cb in text for cb in ["fed", "boj", "boe", "ecb", "rba", "rbnz", "boc", "snb"]) else "Geopolitics"

            result.append({
                "ts": ts,
                "title": title[:120],
                "body": body[:500],
                "cat": cat,
                "ccys": list(set(ccys)),
                "dir": sentiment,
            })

        return result[:15]
    except Exception as e:
        print(f"Erreur GNews: {e}")
        return []

# Test rapide
if __name__ == "__main__":
    news = fetch_financial_juice()
    print(f"{len(news)} articles trouvés")
    for n in news[:3]:
        print(f"{n['ts']} | {n['cat']} | {n['title'][:60]}")