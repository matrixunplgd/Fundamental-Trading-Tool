# utils/news.py
import os
import requests
import json
from datetime import datetime, timedelta
CACHE_FILE = "news_cache.json"

def _load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                ts = datetime.fromisoformat(data.get("ts"))
                if datetime.utcnow() - ts < timedelta(minutes=30):
                    return data.get("articles", [])
        except Exception:
            pass
    return []

def _save_cache(articles):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"ts": datetime.utcnow().isoformat(), "articles": articles}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def fetch_news(query="forex OR fx OR currency", limit=6):
    """Récupère les dernières news via NewsAPI si clé fournie, sinon fallback cache."""
    api_key = os.getenv("NEWS_API_KEY", "")
    cached = _load_cache()
    if api_key:
        url = "https://newsapi.org/v2/everything"
        params = {"q": query, "language": "en", "pageSize": limit, "sortBy": "publishedAt", "apiKey": api_key}
        try:
            r = requests.get(url, params=params, timeout=8)
            if r.status_code == 200:
                items = r.json().get("articles", [])[:limit]
                articles = [{"title": a.get("title"), "source": a.get("source", {}).get("name"), "url": a.get("url"), "publishedAt": a.get("publishedAt")} for a in items]
                _save_cache(articles)
                return articles
        except Exception:
            pass
    # fallback
    return cached
