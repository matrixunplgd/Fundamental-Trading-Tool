# FX Fundamental Dashboard

Dashboard Streamlit d'analyse fondamentale des 8 devises majeures.

## Lancement local
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Déploiement Streamlit Cloud
1. Push ce repo sur GitHub
2. Va sur share.streamlit.io → New app → sélectionne app.py
3. Deploy

## Auto-update (GitHub Actions)
GitHub Actions met à jour data.py automatiquement :
- 17:05 UTC — London close (lundi-vendredi)
- 22:05 UTC — NY close (lundi-vendredi)

### Secrets GitHub à configurer
Settings → Secrets → Actions :
- `GH_TOKEN` — Personal Access Token (Contents: Read & Write)
- `FRED_API_KEY` — Clé gratuite sur fred.stlouisfed.org
- `ALPHAVANTAGE_KEY` — Clé gratuite sur alphavantage.co (optionnel)

## Fichiers
- `app.py` — Application Streamlit (8 pages)
- `data.py` — Données macro, FX, taux, calendrier
- `scraper.py` — Scraper automatique
- `.github/workflows/scraper.yml` — GitHub Actions scheduler

## Sources de données
- FX Rates : Frankfurter (ECB), aucune clé
- Macro : World Bank, aucune clé
- Yields : FRED St Louis Fed, clé gratuite
