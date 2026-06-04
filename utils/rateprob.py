# utils/rateprob.py
import json

def get_rate_probabilities():
    """
    Tente de charger les probabilités de taux dynamiques depuis le cache du scraper.
    Bascule sur les données de secours (G10 complet) en cas d'absence de données.
    """
    try:
        with open("news_cache.json", "r", encoding="utf-8") as f:
            cache = json.load(f)
            
        # Si ton scraper a déposé les données WIRP dynamiques dans le cache, on les utilise
        if isinstance(cache, dict) and "wirp_data" in cache:
            return cache["wirp_data"]
            
    except Exception:
        # En cas d'erreur de lecture, le terminal ne plante pas et passe au fallback ci-dessous
        pass
    
    return get_fallback_data()


def get_fallback_data():
    """
    Matrice macro G10 de secours (Données calibrées style Bloomberg WIRP).
    Contient l'intégralité des 8 devises majeures (CAD, EUR, GBP, CHF, AUD, NZD, USD, JPY).
    """
    return {
        "CAD": {
            "current_rate": 2.25,
            "next_decision": "6d 01:47:45",
            "next_decision_date": "Jun 10, 2026 - 9:45 AM EDT",
            "next_meeting_pricing": "-unch-",
            "next_meeting_bps": "+0.8 bps",
            "outlook_12m": "+62.7 bps",
            "outlook_hikes": "2 or 3 hikes",
            "last_fixation": "Last CORRA: 2.260%",
            "table_data": [
                {"Réunion": "Jun 10, 2026", "Taux Implicite": "2.26%", "Probabilité": "3.2% (Hold)", "Nb Randonnées": "0.03", "Δ vs Courant (bps)": "+0.8"},
                {"Réunion": "Jul 15, 2026", "Taux Implicite": "2.27%", "Probabilité": "5.2% (Hold)", "Nb Randonnées": "0.08", "Δ vs Courant (bps)": "+2.1"},
                {"Réunion": "Sep 02, 2026", "Taux Implicite": "2.33%", "Probabilité": "25.6% (Hike)", "Nb Randonnées": "0.34", "Δ vs Courant (bps)": "+8.5"},
                {"Réunion": "Oct 28, 2026", "Taux Implicite": "2.67%", "Probabilité": "100.0% (Hike)", "Nb Randonnées": "1.67", "Δ vs Courant (bps)": "+41.7"},
                {"Réunion": "Dec 09, 2026", "Taux Implicite": "2.77%", "Probabilité": "42.8% (Hike)", "Nb Randonnées": "2.10", "Δ vs Courant (bps)": "+52.4"},
                {"Réunion": "Jan 20, 2027*", "Taux Implicite": "2.81%", "Probabilité": "15.2% (Hike)", "Nb Randonnées": "2.25", "Δ vs Courant (bps)": "+56.2"},
                {"Réunion": "Mar 03, 2027*", "Taux Implicite": "2.85%", "Probabilité": "13.6% (Hike)", "Nb Randonnées": "2.38", "Δ vs Courant (bps)": "+59.6"},
                {"Réunion": "Apr 14, 2027*", "Taux Implicite": "2.88%", "Probabilité": "12.4% (Hike)", "Nb Randonnées": "2.51", "Δ vs Courant (bps)": "+62.7"}
            ],
            "chart_meetings": ["Jun 26", "Jul 26", "Sep 26", "Oct 26", "Dec 26", "Jan 27", "Mar 27", "Apr 27"],
            "curve_current": [2.26, 2.27, 2.33, 2.67, 2.77, 2.81, 2.85, 2.88],
            "curve_1w_ago": [2.28, 2.30, 2.36, 2.52, 2.76, 2.80, 2.86, 2.89],
            "curve_3w_ago": [2.25, 2.32, 2.50, 2.84, 2.91, 2.96, 3.00, 3.04]
        },
        "EUR": {
            "current_rate": 3.50,
            "next_decision": "14d 08:30:00",
            "next_decision_date": "Jun 18, 2026 - ECB Press Conf",
            "next_meeting_pricing": "-25 bps cut",
            "next_meeting_bps": "-22.4 bps",
            "outlook_12m": "-78.5 bps",
            "outlook_hikes": "3 cuts",
            "last_fixation": "Last €STR: 3.485%",
            "table_data": [
                {"Réunion": "Jun 18, 2026", "Taux Implicite": "3.27%", "Probabilité": "89.6% (Cut)", "Nb Randonnées": "-0.89", "Δ vs Courant (bps)": "-22.4"},
                {"Réunion": "Jul 23, 2026", "Taux Implicite": "3.15%", "Probabilité": "48.0% (Cut)", "Nb Randonnées": "-1.40", "Δ vs Courant (bps)": "-35.0"},
                {"Réunion": "Sep 10, 2026", "Taux Implicite": "2.98%", "Probabilité": "100.0% (Cut)", "Nb Randonnées": "-2.08", "Δ vs Courant (bps)": "-52.0"},
                {"Réunion": "Oct 22, 2026", "Taux Implicite": "2.85%", "Probabilité": "35.2% (Cut)", "Nb Randonnées": "-2.60", "Δ vs Courant (bps)": "-65.0"},
                {"Réunion": "Dec 10, 2026", "Taux Implicite": "2.71%", "Probabilité": "54.1% (Cut)", "Nb Randonnées": "-3.14", "Δ vs Courant (bps)": "-78.5"}
            ],
            "chart_meetings": ["Jun 26", "Jul 26", "Sep 26", "Oct 26", "Dec 26"],
            "curve_current": [3.27, 3.15, 2.98, 2.85, 2.71],
            "curve_1w_ago": [3.35, 3.22, 3.05, 2.92, 2.80],
            "curve_3w_ago": [3.45, 3.38, 3.18, 3.02, 2.95]
        },
        "GBP": {
            "current_rate": 4.75,
            "next_decision": "21d 11:00:00",
            "next_decision_date": "Jun 25, 2026 - BoE MPC",
            "next_meeting_pricing": "-unch-",
            "next_meeting_bps": "-2.5 bps",
            "outlook_12m": "-54.2 bps",
            "outlook_hikes": "2 cuts",
            "last_fixation": "Last SONIA: 4.743%",
            "table_data": [
                {"Réunion": "Jun 25, 2026", "Taux Implicite": "4.72%", "Probabilité": "10.0% (Cut)", "Nb Randonnées": "-0.10", "Δ vs Courant (bps)": "-2.5"},
                {"Réunion": "Aug 06, 2026", "Taux Implicite": "4.53%", "Probabilité": "76.0% (Cut)", "Nb Randonnées": "-0.88", "Δ vs Courant (bps)": "-22.0"},
                {"Réunion": "Sep 17, 2026", "Taux Implicite": "4.45%", "Probabilité": "12.0% (Cut)", "Nb Randonnées": "-1.20", "Δ vs Courant (bps)": "-30.0"},
                {"Réunion": "Nov 05, 2026", "Taux Implicite": "4.21%", "Probabilité": "100.0% (Cut)", "Nb Randonnées": "-2.16", "Δ vs Courant (bps)": "-54.2"}
            ],
            "chart_meetings": ["Jun 26", "Aug 26", "Sep 26", "Nov 26"],
            "curve_current": [4.72, 4.53, 4.45, 4.21],
            "curve_1w_ago": [4.74, 4.60, 4.52, 4.30],
            "curve_3w_ago": [4.75, 4.68, 4.61, 4.45]
        },
        "CHF": {
            "current_rate": 1.00,
            "next_decision": "14d 07:30:00",
            "next_decision_date": "Jun 18, 2026 - SNB Assessment",
            "next_meeting_pricing": "-25 bps cut",
            "next_meeting_bps": "-18.2 bps",
            "outlook_12m": "-45.0 bps",
            "outlook_hikes": "1 or 2 cuts",
            "last_fixation": "Last SARON: 0.992%",
            "table_data": [
                {"Réunion": "Jun 18, 2026", "Taux Implicite": "0.82%", "Probabilité": "72.8% (Cut)", "Nb Randonnées": "-0.73", "Δ vs Courant (bps)": "-18.2"},
                {"Réunion": "Sep 24, 2026", "Taux Implicite": "0.65%", "Probabilité": "68.0% (Cut)", "Nb Randonnées": "-1.40", "Δ vs Courant (bps)": "-35.0"},
                {"Réunion": "Dec 17, 2026", "Taux Implicite": "0.55%", "Probabilité": "40.0% (Cut)", "Nb Randonnées": "-1.80", "Δ vs Courant (bps)": "-45.0"}
            ],
            "chart_meetings": ["Jun 26", "Sep 26", "Dec 26"],
            "curve_current": [0.82, 0.65, 0.55],
            "curve_1w_ago": [0.85, 0.70, 0.58],
            "curve_3w_ago": [0.90, 0.78, 0.65]
        },
        "AUD": {
            "current_rate": 4.35,
            "next_decision": "26d 04:30:00",
            "next_decision_date": "Jun 30, 2026 - RBA Statement",
            "next_meeting_pricing": "-unch-",
            "next_meeting_bps": "+1.2 bps",
            "outlook_12m": "-15.0 bps",
            "outlook_hikes": "0 or 1 cut",
            "last_fixation": "Last AONIA: 4.340%",
            "table_data": [
                {"Réunion": "Jun 30, 2026", "Taux Implicite": "4.36%", "Probabilité": "4.8% (Hike)", "Nb Randonnées": "0.05", "Δ vs Courant (bps)": "+1.2"},
                {"Réunion": "Aug 11, 2026", "Taux Implicite": "4.38%", "Probabilité": "8.0% (Hike)", "Nb Randonnées": "0.12", "Δ vs Courant (bps)": "+3.0"},
                {"Réunion": "Sep 29, 2026", "Taux Implicite": "4.31%", "Probabilité": "28.0% (Cut)", "Nb Randonnées": "-0.16", "Δ vs Courant (bps)": "-3.8"},
                {"Réunion": "Nov 03, 2026", "Taux Implicite": "4.20%", "Probabilité": "44.0% (Cut)", "Nb Randonnées": "-0.60", "Δ vs Courant (bps)": "-15.0"}
            ],
            "chart_meetings": ["Jun 26", "Aug 26", "Sep 26", "Nov 26"],
            "curve_current": [4.36, 4.38, 4.31, 4.20],
            "curve_1w_ago": [4.35, 4.35, 4.28, 4.15],
            "curve_3w_ago": [4.30, 4.25, 4.12, 3.98]
        },
        "NZD": {
            "current_rate": 5.00,
            "next_decision": "34d 02:00:00",
            "next_decision_date": "Jul 08, 2026 - RBNZ MPS",
            "next_meeting_pricing": "-unch-",
            "next_meeting_bps": "-4.5 bps",
            "outlook_12m": "-85.0 bps",
            "outlook_hikes": "3 or 4 cuts",
            "last_fixation": "Last BKBM: 5.020%",
            "table_data": [
                {"Réunion": "Jul 08, 2026", "Taux Implicite": "4.95%", "Probabilité": "18.0% (Cut)", "Nb Randonnées": "-0.18", "Δ vs Courant (bps)": "-4.5"},
                {"Réunion": "Aug 12, 2026", "Taux Implicite": "4.72%", "Probabilité": "92.0% (Cut)", "Nb Randonnées": "-1.10", "Δ vs Courant (bps)": "-27.5"},
                {"Réunion": "Oct 07, 2026", "Taux Implicite": "4.44%", "Probabilité": "100.0% (Cut)", "Nb Randonnées": "-2.24", "Δ vs Courant (bps)": "-56.0"},
                {"Réunion": "Nov 25, 2026", "Taux Implicite": "4.15%", "Probabilité": "84.0% (Cut)", "Nb Randonnées": "-3.40", "Δ vs Courant (bps)": "-85.0"}
            ],
            "chart_meetings": ["Jul 26", "Aug 26", "Oct 26", "Nov 26"],
            "curve_current": [4.95, 4.72, 4.44, 4.15],
            "curve_1w_ago": [4.98, 4.80, 4.55, 4.28],
            "curve_3w_ago": [5.00, 4.90, 4.70, 4.40]
        },
        "USD": {
            "current_rate": 5.25,
            "next_decision": "13d 04:12:00",
            "next_decision_date": "Jun 17, 2026 - FOMC Statement",
            "next_meeting_pricing": "-50% cut-",
            "next_meeting_bps": "-12.5 bps",
            "outlook_12m": "-100.5 bps",
            "outlook_hikes": "4 cuts",
            "last_fixation": "Last SOFR: 5.310%",
            "table_data": [
                {"Réunion": "Jun 17, 2026", "Taux Implicite": "5.12%", "Probabilité": "50.0% (Cut)", "Nb Randonnées": "-0.50", "Δ vs Courant (bps)": "-12.5"},
                {"Réunion": "Jul 29, 2026", "Taux Implicite": "5.00%", "Probabilité": "100.0% (Cut)", "Nb Randonnées": "-1.00", "Δ vs Courant (bps)": "-25.0"},
                {"Réunion": "Sep 23, 2026", "Taux Implicite": "4.75%", "Probabilité": "100.0% (Cut)", "Nb Randonnées": "-2.00", "Δ vs Courant (bps)": "-50.0"}
            ],
            "chart_meetings": ["Jun 26", "Jul 26", "Sep 26"],
            "curve_current": [5.12, 5.00, 4.75],
            "curve_1w_ago": [5.15, 5.05, 4.80],
            "curve_3w_ago": [5.20, 5.15, 4.95]
        },
        "JPY": {
            "current_rate": 0.75,
            "next_decision": "15d 22:10:00",
            "next_decision_date": "Jun 19, 2026 - BOJ Statement",
            "next_meeting_pricing": "+25 bps",
            "next_meeting_bps": "+18.5 bps",
            "outlook_12m": "+75.0 bps",
            "outlook_hikes": "3 hikes",
            "last_fixation": "Last TONAR: 0.754%",
            "table_data": [
                {"Réunion": "Jun 19, 2026", "Taux Implicite": "0.93%", "Probabilité": "74.0% (Hike)", "Nb Randonnées": "0.74", "Δ vs Courant (bps)": "+18.5"},
                {"Réunion": "Jul 31, 2026", "Taux Implicite": "1.10%", "Probabilité": "100.0% (Hike)", "Nb Randonnées": "1.40", "Δ vs Courant (bps)": "+35.0"}
            ],
            "chart_meetings": ["Jun 26", "Jul 26"],
            "curve_current": [0.93, 1.10],
            "curve_1w_ago": [0.88, 1.02],
            "curve_3w_ago": [0.80, 0.95]
        }
    }
