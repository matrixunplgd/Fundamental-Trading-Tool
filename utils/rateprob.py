# utils/rateprob.py
import cloudscraper
from bs4 import BeautifulSoup
import re

def get_rate_probabilities():
    print("🕵️‍♂️ Récupération des données sur centralbank.watch...")
    
    # Slugs des banques centrales sur le site
    ccy_slugs = {
        "USD": "federal-reserve",
        "EUR": "european-central-bank",
        "GBP": "bank-of-england",
        "AUD": "reserve-bank-of-australia",
        "JPY": "bank-of-japan",
        "CAD": "bank-of-canada"
    }
    
    # Matrice de secours (Fallback macro réaliste G10)
    probs = {
        "USD": {"meetings": ["Juin 2026", "Juil 2026", "Sept 2026"], "prob_hike": [0.0, 0.0, 0.0], "prob_cut": [15.0, 65.0, 90.0], "prob_hold": [85.0, 35.0, 10.0], "status": "Cut"},
        "EUR": {"meetings": ["Juin 2026", "Juil 2026", "Sept 2026"], "prob_hike": [0.0, 0.0, 0.0], "prob_cut": [10.0, 55.0, 85.0], "prob_hold": [90.0, 45.0, 15.0], "status": "Cut"},
        "GBP": {"meetings": ["Juin 2026", "Août 2026", "Sept 2026"], "prob_hike": [0.0, 0.0, 0.0], "prob_cut": [5.0, 40.0, 60.0], "prob_hold": [95.0, 60.0, 40.0], "status": "Hold"},
        "AUD": {"meetings": ["Juin 2026", "Août 2026", "Sept 2026"], "prob_hike": [25.0, 45.0, 60.0], "prob_cut": [0.0, 0.0, 0.0], "prob_hold": [75.0, 55.0, 40.0], "status": "Hike"},
        "JPY": {"meetings": ["Juin 2026", "Juil 2026", "Sept 2026"], "prob_hike": [40.0, 70.0, 95.0], "prob_cut": [0.0, 0.0, 0.0], "prob_hold": [60.0, 30.0, 5.0], "status": "Hike"},
        "CAD": {"meetings": ["Juin 2026", "Juil 2026", "Sept 2026"], "prob_hike": [0.0, 0.0, 0.0], "prob_cut": [20.0, 60.0, 80.0], "prob_hold": [80.0, 40.0, 20.0], "status": "Cut"},
        "NZD": {"meetings": ["Août 2026", "Oct 2026", "Nov 2026"], "prob_hike": [15.0, 35.0, 55.0], "prob_cut": [0.0, 0.0, 0.0], "prob_hold": [85.0, 65.0, 45.0], "status": "Hold/Hike"},
        "CHF": {"meetings": ["Sept 2026", "Déc 2026", "Mars 2027"], "prob_hike": [0.0, 0.0, 0.0], "prob_cut": [70.0, 85.0, 95.0], "prob_hold": [30.0, 15.0, 5.0], "status": "Cut"}
    }
    
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    for ccy, slug in ccy_slugs.items():
        try:
            url = f"https://centralbank.watch/{slug}/"
            response = scraper.get(url, timeout=8)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                target_table = None
                
                for table in soup.find_all('table'):
                    headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]
                    if any('meeting' in h for h in headers) and (any('cut' in h for h in headers) or any('hike' in h for h in headers)):
                        target_table = table
                        break
                
                if target_table:
                    headers = [th.get_text(strip=True).lower() for th in target_table.find_all('th')]
                    cut_idx, hold_idx, hike_idx = 1, 2, 3
                    
                    for idx, h in enumerate(headers):
                        if 'cut' in h: cut_idx = idx
                        elif 'change' in h or 'hold' in h: hold_idx = idx
                        elif 'hike' in h: hike_idx = idx
                    
                    meetings, hikes, cuts, holds = [], [], [], []
                    rows = target_table.find_all('tr')[1:]
                    
                    for row in rows:
                        cols = [td.get_text(strip=True) for td in row.find_all('td')]
                        if len(cols) >= max(cut_idx, hold_idx, hike_idx) + 1:
                            meeting_date = cols[0].split(',')[0] # Garde juste "Month DD"
                            meetings.append(meeting_date)
                            
                            def clean_pct(val_str):
                                match = re.search(r'(\d+\.?\d*)', val_str)
                                return float(match.group(1)) if match else 0.0
                            
                            cuts.append(clean_pct(cols[cut_idx]))
                            holds.append(clean_pct(cols[hold_idx]))
                            hikes.append(clean_pct(cols[hike_idx]))
                    
                    if meetings:
                        probs[ccy] = {
                            "meetings": meetings[:4],
                            "prob_hike": hikes[:4],
                            "prob_cut": cuts[:4],
                            "prob_hold": holds[:4],
                            "status": "Hike" if sum(hikes[:2]) > sum(cuts[:2]) else ("Cut" if sum(cuts[:2]) > sum(hikes[:2]) else "Hold")
                        }
        except Exception as e:
            print(f"⚠️ Mode fallback pour {ccy}")
            
    return probs
