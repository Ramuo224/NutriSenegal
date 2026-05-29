"""
Module SMS — Gestion Twilio (corrigé pour insertion BDD en mode démo)
Gère envoi/réception SMS pour NutriScan alertes et MamaMenu
"""

import os
from typing import Optional, Dict
from datetime import datetime

# Importer la connexion depuis votre db.py
from db import get_connection

# En production, dégainer Twilio. Pour démo: mock
TWILIO_ENABLED = os.getenv("TWILIO_ENABLED", "false").lower() == "true"
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE = os.getenv("TWILIO_PHONE", "+221123456789")

if TWILIO_ENABLED:
    from twilio.rest import Client
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
else:
    twilio_client = None

# Historique SMS pour démo (mémoire)
SMS_LOG = []

def envoyer_sms(numero_destination: str, message: str, type_sms: str = "alerte") -> Dict:
    """
    Envoyer un SMS.
    Pour démo sans Twilio: simule l'envoi, log en console ET insère en BDD.
    """
    global SMS_LOG
    
    sms_record = {
        "timestamp": datetime.now().isoformat(),
        "from": TWILIO_PHONE,
        "to": numero_destination,
        "message": message,
        "type": type_sms,
        "statut": "envoye_sim"
    }
    SMS_LOG.append(sms_record)
    
    # --- BLOC CORRECTEUR ROBUSTE POUR LE DASHBOARD ---
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # On vérifie si le numéro correspond à une maman abonnée
        cursor.execute("SELECT id FROM abonnees WHERE telephone = ?", (numero_destination,))
        row = cursor.fetchone()
        
        if row:
            # Si c'est une maman, on associe l'abonnee_id normalement
            cursor.execute('''
                INSERT INTO envois_sms (abonnee_id, message, type_message, statut, date_envoi)
                VALUES (?, ?, ?, ?, ?)
            ''', (row['id'], message, type_sms, "envoye_sim", datetime.now().isoformat()))
        else:
            # Si c'est une alerte de centre de santé (NutriScan), on omet l'abonnee_id
            # pour éviter de violer la contrainte FOREIGN KEY (Clé étrangère)
            cursor.execute('''
                INSERT INTO envois_sms (message, type_message, statut, date_envoi)
                VALUES (?, ?, ?, ?)
            ''', (message, type_sms, "envoye_sim", datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        print("💾 Succès : SMS enregistré dans la base de données (envois_sms) !")
    except Exception as db_err:
        print(f"⚠️ Erreur critique d'écriture du SMS en BDD : {db_err}")
    # --------------------------------------------------

    if TWILIO_ENABLED and twilio_client:
        try:
            msg = twilio_client.messages.create(
                body=message[:160],
                from_=TWILIO_PHONE,
                to=numero_destination
            )
            sms_record["statut"] = "envoye_twilio"
            sms_record["sid"] = msg.sid
            return {"succes": True, "sid": msg.sid}
        except Exception as e:
            sms_record["statut"] = "erreur"
            sms_record["erreur"] = str(e)
            return {"succes": False, "erreur": str(e)}
    else:
        # Simulation pour development/hackathon
        print(f"📱 SMS SIMULÉ à {numero_destination}:")
        print(f"   {message}\n")
        return {"succes": True, "statut": "simule"}

def envoyer_alerte_nutriscan(centre_sante_tel: str, enfant_prenom: str, 
                             enfant_age: int, region: str, score: str,
                             agent_nom: str, agent_zone: str) -> Dict:
    """Envoyer alerte NutriScan au centre de santé."""
    
    message = (
        f"🚨 NUTRISCAN ALERTE {score}\n"
        f"Enfant: {enfant_prenom} ({enfant_age}m)\n"
        f"Région: {region}\n"
        f"Agent: {agent_nom} — Zone: {agent_zone}\n"
        f"⚠️ Action requise immédiatement"
    )
    
    return envoyer_sms(centre_sante_tel, message, type_sms="alerte_nutriscan")

def envoyer_recette_mamamenù(numero_mere: str, recette_nom: str, 
                             ingredients: str, instructions: str, 
                             kcal: int, proteines: float, langue: str = "fr") -> Dict:
    """Envoyer recette à une mère (MamaMenu)."""
    
    if langue == "wo":
        message = f"🍽️ MAMAMENÙ (Wolof):\n{recette_nom}\n{ingredients}\n{kcal}kcal, {proteines}g protéines"
    else:
        message = f"🍽️ MAMAMENÙ:\n{recette_nom}\n{ingredients[:80]}...\n{kcal}kcal, {proteines}g protéines"
    
    return envoyer_sms(numero_mere, message[:160], type_sms="recette_mamamenù")

def obtenir_historique_sms(limite: int = 50) -> list:
    """Récupérer historique SMS simulés."""
    return SMS_LOG[-limite:]

def parser_sms_entrant(numero: str, message: str) -> Dict:
    """
    Parser SMS entrant pour inscription MamaMenu.
    Format attendu: "age enfant" ou "AIDE"
    """
    
    msg_lower = message.lower().strip()
    
    if msg_lower == "aide":
        return {
            "type": "aide",
            "message": "Tapez l'âge de votre enfant en mois (ex: 12)"
        }
    
    try:
        age_mois = int(msg_lower)
        if 0 < age_mois < 60:
            return {
                "type": "inscription",
                "age_mois": age_mois,
                "telephone": numero,
                "message": f"✅ Inscrite! Enfant {age_mois}m. Recette cette semaine."
            }
        else:
            return {
                "type": "erreur",
                "message": "Âge invalide. Doit être entre 1-59 mois."
            }
    except:
        return {
            "type": "erreur",
            "message": "Format invalide. Tapez l'âge en chiffres."
        }

if __name__ == "__main__":
    # Test
    result = envoyer_alerte_nutriscan(
        centre_sante_tel="+221771234567",
        enfant_prenom="Marie",
        enfant_age=18,
        region="Dakar",
        score="ROUGE",
        agent_nom="Aram Fall",
        agent_zone="Pikine"
    )
    print(result)
    
    # Parser SMS
    parsed = parser_sms_entrant("+221771234567", "12")
    print(parsed)