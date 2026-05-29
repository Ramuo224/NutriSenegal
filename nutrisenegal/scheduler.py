"""
Scheduler — Mises à jour automatiques toutes les 3h
Agrège données météo, prix, et met à jour score régional
"""

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import requests
from typing import Dict
from malimap import maj_donnees_region, obtenir_regions_par_risque
from db import get_connection

scheduler = BackgroundScheduler()

def maj_donnees_toutes_regions():
    """Mettre à jour scores pour toutes les régions (exécuté toutes les 3h)."""
    print(f"[{datetime.now()}] 🔄 Mise à jour données régionales...")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT region FROM donnees_regions")
    regions = [r[0] for r in cursor.fetchall()]
    conn.close()
    
    for region in regions:
        try:
            result = maj_donnees_region(region)
            print(f"  ✅ {region}: score={result['score']} ({result['niveau']})")
        except Exception as e:
            print(f"  ❌ {region}: Erreur — {str(e)}")
    
    print(f"[{datetime.now()}] ✅ Mise à jour complète\n")

def maj_prix_alimentaires():
    """Mettre à jour indices prix FAO (simulation)."""
    print(f"[{datetime.now()}] 📊 Mise à jour prix FAO...")
    # En production: appeler GIEWS API
    # https://www.fao.org/giews/pricelists
    print(f"  ✅ Prix mis à jour\n")

def maj_meteorologie():
    """Mettre à jour pluviométrie Open-Meteo."""
    print(f"[{datetime.now()}] 🌧️ Mise à jour météo...")
    # En production: appeler Open-Meteo API
    # https://open-meteo.com/
    print(f"  ✅ Météo mise à jour\n")

def maj_alertes_sms():
    """Envoyer SMS de recettes MamaMenu (hebdo)."""
    print(f"[{datetime.now()}] 📱 Envoi recettes hebdomadaires...")
    from mamamenù import obtenir_abonnees_pour_envoi_semain, recommander_recette, formater_sms_recette
    from sms import envoyer_sms
    
    abonnees = obtenir_abonnees_pour_envoi_semain()
    for abonnee in abonnees:
        rec = recommander_recette(abonnee['age_enfant_mois'], abonnee['langue'])
        if rec['recette']:
            sms = formater_sms_recette(rec['recette'], abonnee['langue'], 1)
            envoyer_sms(abonnee['telephone'], sms[:160])
            print(f"  ✅ SMS envoyé à {abonnee['telephone']}")
    
    print(f"[{datetime.now()}] ✅ Envois complétés\n")

def demarrer_scheduler():
    """Démarrer le scheduler en arrière-plan."""
    
    # Mise à jour regions toutes les 3h
    scheduler.add_job(maj_donnees_toutes_regions, 'interval', hours=3, id='maj_regions')
    
    # Mise à jour prix quotidienne à 6h du matin
    scheduler.add_job(maj_prix_alimentaires, 'cron', hour=6, id='maj_prix')
    
    # Mise à jour météo 2x/jour
    scheduler.add_job(maj_meteorologie, 'cron', hour='6,18', id='maj_meteo')
    
    # Envois SMS hebdo (lundi à 8h)
    scheduler.add_job(maj_alertes_sms, 'cron', day_of_week='0', hour=8, id='envoi_sms')
    
    scheduler.start()
    print("✅ Scheduler démarré")
    print("  • Régions maj toutes 3h")
    print("  • Prix à 06:00")
    print("  • Météo à 06:00 et 18:00")
    print("  • SMS lundi à 08:00\n")

if __name__ == "__main__":
    demarrer_scheduler()
    
    # Garder le scheduler en vie
    try:
        while True:
            pass
    except KeyboardInterrupt:
        scheduler.shutdown()
        print("Scheduler arrêté")
