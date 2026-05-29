"""
MaliMap — Carte de risque nutritionnel en temps réel
Module pour agrégation données et scoring régional (Version Spéciale Démo Hackathon - Sénégal)
"""

from typing import Dict, List, Optional
from datetime import datetime
from db import get_connection

def calculer_score_risque(region: str, data: Dict) -> float:
    """
    Calculer score composite (0-100) pour une région.
    Version Hackathon rééquilibrée pour rendre l'impact visuel immédiat.
    """
    score = 0
    
    # Facteurs de risque (les coefficients ont été augmentés pour la démo en direct)
    score += min(data.get('pluie_deficit', 0) * 1.5, 30)  
    score += min(data.get('prix_alimentaires_hausse', 0) * 1.5, 20)  
    
    # Un seul cas NutriScan récent fait maintenant bondir le score de 50 points d'un coup !
    score += min(data.get('cas_nutriscan_30j', 0) * 50.0, 60)  
    
    # Facteurs de protection
    score -= min(data.get('densite_medicale', 0) * 10, 10)  
    score -= min(data.get('acces_eau_potable', 0) / 10, 10)  
    
    return round(max(0, min(100, score)), 1)

def maj_donnees_region(region: str) -> Dict:
    """Mettre à jour les données d'une région avec simulation réaliste par zone."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Compter cas ORANGE/ROUGE des 30 derniers jours
    try:
        cursor.execute('''
        SELECT COUNT(*) as nb_cas FROM alertes
        WHERE region = ? AND datetime(date_alerte) >= datetime('now', '-30 days')
        ''', (region,))
        cas_30j = cursor.fetchone()[0]
    except Exception:
        cas_30j = 0
    
    # --- TA CONFIGURATION DE DONNÉES JSON INTÉGRÉE ---
    config_brute = {
        "Dakar": {"densite": 2.5, "eau": 95, "critique": False},
        "Thiès": {"densite": 0.8, "eau": 75, "critique": False},
        "Thies": {"densite": 0.8, "eau": 75, "critique": False},  # Sécurité doublon accent
        "Kaolack": {"densite": 0.5, "eau": 65, "critique": False},
        "Tambacounda": {"densite": 0.4, "eau": 55, "critique": True},
        "Kolda": {"densite": 0.3, "eau": 50, "critique": False},
        "Diourbel": {"densite": 0.4, "eau": 60, "critique": True},
        "Matam": {"densite": 0.3, "eau": 45, "critique": True},
        "Saint-Louis": {"densite": 0.6, "eau": 70, "critique": False},
        "Louga": {"densite": 0.35, "eau": 58, "critique": False},
        "Fatick": {"densite": 0.4, "eau": 62, "critique": False},
        "Ziguinchor": {"densite": 0.5, "eau": 68, "critique": False},
        "Kedougou": {"densite": 0.25, "eau": 48, "critique": False}
    }
    
    reg_config = config_brute.get(region, {"densite": 0.4, "eau": 60, "critique": False})
    
    # Si la région est marquée critique=True dans ton JSON, on simule des risques initiaux.
    # Sinon, le risque de base reste à 0 pour laisser la région au vert.
    if reg_config["critique"]:
        pluie_def = 75.0
        prix_hausse = 80.0
    else:
        pluie_def = 0.0
        prix_hausse = 0.0
        
    data = {
        'pluie_deficit': pluie_def, 
        'prix_alimentaires_hausse': prix_hausse,
        'cas_nutriscan_30j': cas_30j,
        'densite_medicale': reg_config["densite"],
        'acces_eau_potable': reg_config["eau"]
    }
    
    score = calculer_score_risque(region, data)
    
    # Mettre à jour BDD si la table existe
    try:
        cursor.execute('''
        UPDATE donnees_regions
        SET score_risque = ?, pluie_deficit = ?, prix_alimentaires_hausse = ?,
            cas_nutriscan_30j = ?, acces_eau_potable = ?, date_maj = CURRENT_TIMESTAMP
        WHERE region = ?
        ''', (score, data['pluie_deficit'], data['prix_alimentaires_hausse'],
              data['cas_nutriscan_30j'], data['acces_eau_potable'], region))
        conn.commit()
    except Exception:
        pass
        
    conn.close()
    
    return {
        "region": region,
        "score": score,
        "data": data,
        "niveau": "CRITIQUE" if score > 70 else "ÉLEVÉ" if score > 50 else "MODÉRÉ" if score > 30 else "BAS"
    }

def obtenir_regions_par_risque() -> List[Dict]:
    """Obtenir toutes les régions configurées avec leurs données dynamiques."""
    liste_regions = ["Dakar", "Thiès", "Kaolack", "Tambacounda", "Kolda", "Diourbel", 
                     "Matam", "Saint-Louis", "Louga", "Fatick", "Ziguinchor", "Kedougou"]
    
    # Coordonnées géographiques précises issues de ton JSON
    coords = {
        "Dakar": [14.6928, -17.0469], 
        "Thiès": [14.7919, -16.9397], 
        "Thies": [14.7919, -16.9397],
        "Kaolack": [13.9644, -15.9281], 
        "Tambacounda": [13.7721, -13.7743], 
        "Kolda": [13.0581, -14.9425], 
        "Diourbel": [14.6405, -15.5535], 
        "Matam": [14.6496, -13.2407], 
        "Saint-Louis": [16.0255, -16.4915], 
        "Louga": [15.6196, -15.6108], 
        "Fatick": [13.5522, -15.8661], 
        "Ziguinchor": [13.3703, -15.5577], 
        "Kedougou": [12.5549, -12.1808]
    }
    
    regions = []
    for nom_reg in liste_regions:
        res = maj_donnees_region(nom_reg)
        loc = coords.get(nom_reg, [14.0, -14.0])
        
        regions.append({
            "nom": nom_reg,
            "lat": loc[0],
            "lon": loc[1],
            "score": res["score"],
            "niveau": res["niveau"],
            "cas_30j": res["data"]["cas_nutriscan_30j"],
            "densite_medicale": res["data"]["densite_medicale"]
        })
        
    return sorted(regions, key=lambda x: x['score'], reverse=True)

def generer_alerte_decision(region: str, score: float) -> Dict:
    """Générer alerte pour décideurs (ONG, Ministère)."""
    if score > 70:
        niveau = "🔴 CRITIQUE"
        action = "INTERVENTION IMMÉDIATE"
        details = "Malnutrition générale probable. Dépêcher équipe nutrition."
    elif score > 50:
        niveau = "🟠 ÉLEVÉ"
        action = "INTERVENTION À 7 JOURS"
        details = "Signaux faibles. Intensifier suivi + recettes MamaMenu."
    elif score > 30:
        niveau = "🟡 MODÉRÉ"
        action = "SURVEILLANCE RENFORCÉE"
        details = "Situation stable. Maintenir monitoring."
    else:
        niveau = "🟢 BAS"
        action = "SUIVI STANDARD"
        details = "Pas d'inquiétude immédiate."
    
    return {
        "region": region,
        "score": score,
        "niveau": niveau,
        "action": action,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }

def generer_geojson_carte(regions: List[Dict]) -> Dict:
    """Générer GeoJSON pour rendu complet sur l'interface graphique."""
    features = []
    for region in regions:
        color_map = {
            "CRITIQUE": "#d62728",  # Rouge
            "ÉLEVÉ": "#ff7f0e",     # Orange
            "MODÉRÉ": "#ffdd57",    # Jaune
            "BAS": "#2ca02c"        # Vert
        }
        
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [region['lon'], region['lat']]
            },
            "properties": {
                "nom": region['nom'],
                "score": region['score'],
                "niveau": region['niveau'],
                "cas_30j": region['cas_30j'],
                "color": color_map.get(region['niveau'], "#2ca02c")
            }
        })
    
    return {
        "type": "FeatureCollection",
        "features": features
    }
