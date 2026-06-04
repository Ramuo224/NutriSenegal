"""
NutriSénégal — Backend FastAPI Principal
Point d'entrée unique pour tous les modules
"""

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json
import os

# Importer tous les modules
from db import (
    init_db,
    charger_recettes_depuis_json,
    charger_regions_depuis_json,
    get_alertes_actives,
    get_alertes_historique,
    resoudre_alerte
)
from nutriscan import enregistrer_enfant, score_risque
from mamamenù import inscrire_mere, recommander_recette, formater_sms_recette
from malimap import obtenir_regions_par_risque, maj_donnees_region, generer_geojson_carte
# sms : importation de envoyer_sms, etc., et de la liste SMS_LOG pour le compteur
from sms import envoyer_sms, envoyer_alerte_nutriscan, parser_sms_entrant, obtenir_historique_sms, SMS_LOG
from scheduler import demarrer_scheduler

# Initialiser FastAPI
app = FastAPI(
    title="NutriSénégal",
    description="Plateforme numérique contre la malnutrition infantile au Sénégal",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# INITIALISATION
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialiser la BDD et charger données au démarrage."""
    print("🚀 NutriSénégal démarrage...")
    
    # Créer/initialiser BDD
    init_db()
    
    # Charger données (chemins compatibles avec Render)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    recettes_path = os.path.join(base_dir, "data", "recettes.json")
    with open(recettes_path, "r", encoding="utf-8") as f:
        recettes = json.load(f)
        charger_recettes_depuis_json(recettes)
    
    regions_path = os.path.join(base_dir, "data", "regions.json")
    with open(regions_path, "r", encoding="utf-8") as f:
        regions = json.load(f)
        charger_regions_depuis_json(regions)
    
    # Démarrer scheduler
    demarrer_scheduler()
    
    print("✅ NutriSénégal prêt!\n")

# ============================================================================
# MODÈLES PYDANTIC
# ============================================================================

class EnfantSaisie(BaseModel):
    prenom: str
    age_mois: int
    region: str
    poids_kg: float
    taille_cm: float
    perimetre_brachial: Optional[float] = None
    agent_nom: Optional[str] = None
    agent_zone: Optional[str] = None

class InscriptionMere(BaseModel):
    telephone: str
    age_enfant_mois: int
    region: str
    langue: str = "fr"
    prenom: Optional[str] = None

# ============================================================================
# ROUTES PRINCIPALES
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def page_accueil():
    """Page d'accueil NutriSénégal."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(base_dir, "templates", "index.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/health")
async def health_check():
    """Vérifier que l'API fonctionne."""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "application": "NutriSénégal",
        "version": "1.0.0"
    }

@app.get("/favicon.ico")
async def favicon():
    """Répondre proprement au navigateur lorsque le favicon est demandé."""
    return Response(status_code=204, media_type="image/x-icon")

# ============================================================================
# NUTRISCAN — Dépistage
# ============================================================================

@app.post("/api/nutriscan/enregistrer")
async def api_nutriscan_enregistrer(enfant: EnfantSaisie):
    """Enregistrer un enfant et calculer son score de risque."""
    result = enregistrer_enfant(
        prenom=enfant.prenom,
        age_mois=enfant.age_mois,
        region=enfant.region,
        poids_kg=enfant.poids_kg,
        taille_cm=enfant.taille_cm,
        perimetre_brachial=enfant.perimetre_brachial,
        agent_nom=enfant.agent_nom,
        agent_zone=enfant.agent_zone
    )
    
    # Si ROUGE ou ORANGE, envoyer alerte SMS
    if result.get('alerte') and result.get('score') in ["ROUGE", "ORANGE"]:
        sms_result = envoyer_sms(
            numero_destination="+221771234567",  # Centre de santé (mock)
            message=f"🚨 NUTRISCAN ALERTE {result['score']}: {enfant.prenom} ({enfant.age_mois}m) - {enfant.region}",
            type_sms="alerte_nutriscan"
        )
        result['sms_envoye'] = sms_result.get('succes', False)
    
    return result

@app.get("/api/nutriscan/formulaire", response_class=HTMLResponse)
async def formulaire_nutriscan():
    """Formulaire HTML pour saisir enfant."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(base_dir, "templates", "nutriscan.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

# ============================================================================
# MAMAMENÙ — Prévention
# ============================================================================

@app.post("/api/mamamenù/inscrire")
async def api_mamamenù_inscrire(inscription: InscriptionMere):
    """Inscrire une mère à MamaMenu."""
    result = inscrire_mere(
        telephone=inscription.telephone,
        age_enfant_mois=inscription.age_enfant_mois,
        region=inscription.region,
        langue=inscription.langue,
        prenom=inscription.prenom
    )
    
    # Envoyer recette bienvenue
    if result.get('succes'):
        rec = recommander_recette(inscription.age_enfant_mois, inscription.langue)
        if rec['recette']:
            sms = formater_sms_recette(rec['recette'], inscription.langue, 1)
            envoyer_sms(inscription.telephone, sms[:160], "recette_mamamenù")
    
    return result

@app.post("/api/mamamenù/sms-entrant")
async def api_mamamenù_sms_entrant(telephone: str, message: str):
    """Webhook pour SMS entrant (inscription MamaMenu)."""
    parsed = parser_sms_entrant(telephone, message)
    
    if parsed['type'] == 'inscription':
        # Auto-inscrire
        result = inscrire_mere(
            telephone=telephone,
            age_enfant_mois=parsed['age_mois'],
            region="Non spécifiée",
            langue="fr"
        )
        return {
            "statut": "inscrite",
            "message": parsed['message']
        }
    else:
        return {
            "statut": "erreur",
            "message": parsed['message']
        }

@app.get("/api/mamamenù/recette/{age_mois}")
async def api_mamamenù_recette(age_mois: int, langue: str = "fr"):
    """Obtenir recette adaptée à l'âge."""
    result = recommander_recette(age_mois, langue)
    return result

@app.get("/api/mamamenù/formulaire", response_class=HTMLResponse)
async def formulaire_mamamenù():
    """Formulaire HTML pour inscription MamaMenu."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(base_dir, "templates", "mamamenù.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

# ============================================================================
# MALIMAP — Cartographie
# ============================================================================

@app.get("/api/malimap/regions")
async def api_malimap_regions():
    """Obtenir toutes les régions avec scores de risque."""
    return obtenir_regions_par_risque()

@app.get("/api/malimap/geojson")
async def api_malimap_geojson():
    """Obtenir GeoJSON pour carte interactive."""
    regions = obtenir_regions_par_risque()
    return generer_geojson_carte(regions)

@app.get("/api/malimap/region/{nom_region}")
async def api_malimap_region(nom_region: str):
    """Mettre à jour et obtenir données d'une région."""
    result = maj_donnees_region(nom_region)
    return result

@app.get("/api/alertes/actives")
async def api_alertes_actives():
    """Obtenir alertes actives non résolues."""
    return get_alertes_actives()

@app.get("/api/alertes/historique")
async def api_alertes_historique(limite: int = 50):
    """Obtenir l'historique des alertes récentes."""
    return get_alertes_historique(limite)

@app.post("/api/alertes/{alerte_id}/resoudre")
async def api_resoudre_alerte(alerte_id: int):
    """Marquer une alerte comme résolue."""
    succes = resoudre_alerte(alerte_id)
    if not succes:
        raise HTTPException(status_code=404, detail="Alerte introuvable ou déjà résolue")
    return {"succes": True, "alerte_id": alerte_id}

@app.get("/malimap", response_class=HTMLResponse)
async def page_malimap():
    """Page interactive MaliMap."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(base_dir, "templates", "malimap.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

# ============================================================================
# ADMIN — Historique et Monitoring
# ============================================================================

@app.get("/api/admin/sms-log")
async def api_admin_sms_log(limite: int = 50):
    """Obtenir historique SMS."""
    return obtenir_historique_sms(limite)

@app.get("/api/admin/stats")
async def api_admin_stats():
    """Obtenir statistiques globales (Corrigé avec SMS_LOG pour la démo)."""
    from db import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Enfants dépistés
    cursor.execute("SELECT COUNT(*) FROM enfants")
    nb_enfants = cursor.fetchone()[0]
    
    # Alertes actives non résolues
    cursor.execute("SELECT COUNT(*) FROM alertes WHERE score IN ('ORANGE', 'ROUGE') AND resolue = 0")
    nb_alertes = cursor.fetchone()[0]
    
    # Abonnées
    cursor.execute("SELECT COUNT(*) FROM abonnees")
    nb_abonnees = cursor.fetchone()[0]
    
    conn.close()
    
    # --- MODIFICATION DE SÉCURITÉ POUR LE HACKATHON ---
    # Au lieu d'interroger la table SQLite qui pose problème,
    # on récupère la taille exacte de la liste SMS_LOG (mémoire) qui alimente les logs du bas.
    nb_sms = len(SMS_LOG)
    # --------------------------------------------------
    
    return {
        "enfants_depistes": nb_enfants,
        "alertes_actives": nb_alertes,
        "abonnees_mamamenù": nb_abonnees,
        "sms_envoyes": nb_sms,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/dashboard", response_class=HTMLResponse)
async def page_dashboard():
    """Dashboard admin."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(base_dir, "templates", "dashboard.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

# ============================================================================
# ERREURS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "erreur": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )

# ============================================================================
# LANCER L'APP
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )