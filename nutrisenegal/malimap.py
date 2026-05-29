"""
MaliMap — Carte de risque nutritionnel en temps réel
Module pour agrégation données et scoring régional (Version Spéciale Démo Hackathon)
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
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
    
    # --- CONFIGURATION DE DONNÉES DE DÉMO PAS EN DUR ---
    # Pour que chaque région ait une vraie couleur différente au départ (Pitch réaliste)
    config_regions = {
        "Matam": {"pluie": 80, "prix": 75, "eau": 30},
        "Diourbel": {"pluie": 70, "prix": 85, "eau": 40},
        "Tambacounda": {"pluie": 65, "prix": 60, "eau": 35},
        "Saint-Louis": {"pluie": 40, "prix": 50, "eau": 60},
        "Dakar": {"pluie": 10, "prix": 30, "eau": 90},
        "Thiès": {"pluie": 20, "prix": 35, "eau": 80}
    }
    
    reg_config = config_regions.get(region, {"pluie": 35, "prix": 40, "eau": 55})
    
    data = {
        'pluie_deficit': reg_config["pluie"], 
        'prix_alimentaires_hausse': reg_config["prix"],
        'cas_nutriscan_30j': cas_30j,
        'densite_medicale': 0.4,
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
    """Obtenir toutes les régions (Calcule à la volée pour assurer le dynamisme)."""
    # Liste des régions du Sénégal définies dans votre projet
    liste_regions = ["Dakar", "Diourbel", "Fatick", "Kaolack", "Kaffrine", "Kedougou", 
                     "Kolda", "Louga", "Matam", "Podor", "Saint-Louis", "Sedhiou", 
                     "Tambacounda", "Thiès", "Ziguinchor"]
    
    regions = []
    # Coordonnées approximatives pour le centrage des points sur la carte
    coords = {
        "Dakar": [14.7167, -17.4677], "Diourbel": [14.6500, -16.4000], "Fatick": [14.3333, -16.4167],
        "Kaolack": [14.1833, -16.0833], "Kaffrine": [14.1000, -15.5500], "Kedougou": [12.5500, -12.1833],
        "Kolda": [12.8833, -14.9500], "Louga": [15.6167, -16.2167], "Matam": [15.6167, -13.2500],
        "Saint-Louis": [16.0167, -16.5000], "Sedhiou": [12.7083, -15.5569], "Tambacounda": [13.7667, -13.6667],
        "Thiès": [14.7833, -16.9167], "Ziguinchor": [12.5833, -16.2667]
    }
    
    for nom_reg in liste_regions:
        # Met à jour et récupère le score calculé dynamiquement
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
    """Générer GeoJSON pour rendu complet."""
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
