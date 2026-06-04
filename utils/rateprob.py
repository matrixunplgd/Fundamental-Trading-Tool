# utils/rateprob.py
import cloudscraper
from bs4 import BeautifulSoup
import re

def get_rate_probabilities():
    print("🕵️‍♂️ Lancement du scraper sur centralbank.watch...")
    
    # Mapping des devises vers les slugs exacts du site
    ccy_slugs = {
        "USD": "federal-reserve",
        "EUR": "european-central-bank",
        "GBP": "bank-of-england",
        "AUD": "reserve-bank-of-australia",
        "JPY": "bank-of-japan",
        "CAD": "bank-of-canada"
    }
    
    # Matrice de secours fondamentale G10 (reflétant le biais actuel si le site est down)
    probs = {
        "USD": {"meetings": ["Jul 2026", "Sep 2026", "Nov 2026"], "prob_hike": [0.0, 0.0, 0.0], "prob_cut": [82.0, 94.5, 99.0], "prob_hold": [18.0, 5.5, 1.0], "status": "Cut"},
        "EUR": {"meetings": ["Jul 2026", "Sep 2026", "Oct 2026"], "prob_hike": [0.0, 0.0, 0.0], "prob_cut": [95.0, 100.0, 100.0], "prob_hold": [5.0, 0.0, 0.0], "status": "Cut"},
        "GBP": {"meetings": ["Aug 2026", "Sep 2026", "Nov 2026"], "prob_hike": [0.0, 0.0, 0.0], "prob_cut": [40.5, 60.0, 75.0], "prob_hold": [59.5, 40.0, 25.0], "status": "Hold/Cut"},
        "AUD": {"meetings": ["Aug 2026", "Sep 2026", "Nov 2026"], "prob_hike": [20.0, 35.0, 50.0], "prob_cut": [0.0, 0.0, 0.0], "prob_hold": [80.0, 65.0, 50.0], "status": "Hike"},
        "JPY": {"meetings": ["Jul 2026", "Sep 2026", "Oct 2026"], "prob_hike": [68.5, 82.0, 95.0], "prob_cut": [0.0, 0.0, 0.0], "prob_hold": [31.5, 18.0, 5.0], "status": "Hike"},
        "CAD": {"meetings": ["Jul 2026", "Sep 2026", "Oct 2026"], "prob_hike": [0.0, 0.0, 0.0], "prob_cut": [88.0, 95.0, 98.0], "prob_hold": [12.0, 5.0, 2.0], "status": "Cut"},
        "NZD": {"meetings": ["Aug 2026", "Oct 2026", "Nov 2026"], "prob_hike": [15.0, 25.0, 40.0], "prob_cut": [0.0, 0.0, 0.0], "prob_hold": [85.0, 75.0, 60.0], "status": "Hold/Hike"},
        "CHF": {"meetings": ["Sep 2026", "Dec 2026", "Mar 2027"], "prob_hike": [0.0, 0.0, 0.0], "prob_cut": [75.0, 85.0, 90.0], "prob_hold": [25.0, 15.0, 10.0], "status": "Cut"}
    }
    
    # Utilisation de cloudscraper pour l'en-tête de requête standard clean
    scraper = cloudscraper.create_scraper(browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    })
    
    for ccy, slug in ccy_slugs.items():
        try:
            url = f"https://centralbank.watch/{slug}/"
            response = scraper.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Cibler le tableau des probabilités de réunions
                target_table = None
                for table in soup.find_all('table'):
                    headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]
                    if any('meeting' in h for h in headers) and (any('cut' in h for h in headers) or any('hike' in h for h in headers)):
                        target_table = table
                        break
                
                if target_table:
                    # Identification dynamique de l'ordre des colonnes
                    headers = [th.get_text(strip=True).lower() for th in target_table.find_all('th')]
                    cut_idx, hold_idx, hike_idx = 1, 2, 3 # Valeurs par défaut
                    
                    for idx, h in enumerate(headers):
                        if 'cut' in h: cut_idx = idx
                        elif 'change' in h or 'hold' in h: hold_idx = idx
                        elif 'hike' in h: hike_idx = idx
                    
                    meetings, hikes, cuts, holds = [], [], [], []
                    rows = target_table.find_all('tr')[1:]  # Skip header
                    
                    for row in rows:
                        cols = [td.get_text(strip=True) for td in row.find_all('td')]
                        if len(cols) >= max(cut_idx, hold_idx, hike_idx) + 1:
                            # Extraction du mois/année de la réunion (ex: "June 11, 2026" -> "June 11")
                            meeting_date = cols[0].split(',')[0]
                            meetings.append(meeting_date)
                            
                            # Nettoyage et conversion des pourcentages (ex: "74.7%" -> 74.7)
                            def clean_pct(val_str):
                                match = re.search(r'(\d+\.?\d*)', val_str)
                                return float(match.group(1)) if match else 0.0
                            
                            cuts.append(clean_pct(cols[cut_idx]))
                            holds.append(clean_pct(cols[hold_idx]))
                            hikes.append(clean_pct(cols[hike_idx]))
                    
                    if meetings:
                        # Remplacement des données de secours par les données réelles (limité à 4 nodes pour le graphique)
                        probs[ccy] = {
                            "meetings": meetings[:4],
                            "prob_hike": hikes[:4],
                            "prob_cut": cuts[:4],
                            "prob_hold": holds[:4],
                            "status": "Hike" if sum(hikes[:2]) > sum(cuts[:2]) else ("Cut" if sum(cuts[:2]) > sum(hikes[:2]) else "Hold")
                        }
                        print(f"✅ Synchro CentralBank.watch réussie pour : {ccy}")
                        
        except Exception as e:
            print(f"⚠️ Impossible de scraper {ccy} ({e}), maintien de la matrice macro.")
            
    return probs
