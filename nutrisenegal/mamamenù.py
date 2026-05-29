"""
MamaMenu — Prévention nutritionnelle par SMS
Module pour envoi de recettes adaptées aux mères de famille
"""

import json
from typing import Dict, Optional, List
from datetime import datetime
from db import (get_connection, ajouter_abonnee, get_recettes_pour_age, 
                get_abonnees_pour_envoi, charger_recettes_depuis_json)

def inscrire_mere(telephone: str, age_enfant_mois: int, region: str, 
                  langue: str = 'fr', prenom: Optional[str] = None) -> Dict:
    """Inscrire une mère à MamaMenu."""
    try:
        abonnee_id = ajouter_abonnee(
            telephone=telephone,
            age_enfant_mois=age_enfant_mois,
            region=region,
            langue=langue,
            prenom=prenom
        )
        return {
            "succes": True,
            "abonnee_id": abonnee_id,
            "message": "✅ Inscription réussie! Vous recevrez des recettes chaque semaine."
        }
    except Exception as e:
        return {
            "succes": False,
            "erreur": f"Erreur inscription: {str(e)}"
        }

def recommander_recette(age_enfant_mois: int, langue: str = 'fr') -> Dict:
    """Sélectionner une recette adaptée à l'âge."""
    recettes = get_recettes_pour_age(age_enfant_mois, langue)
    
    if not recettes:
        return {
            "recette": None,
            "message": "Pas de recette trouvée pour cet âge"
        }
    
    recette = recettes[0]
    return {
        "recette": recette,
        "message": f"✅ Recette trouvée: {recette['nom']}"
    }

def formater_sms_recette(recette: Dict, langue: str = 'fr', semaine: int = 1) -> str:
    """Formater une recette en message SMS (max 160 car SMS)."""
    
    if langue == 'wo':
        # Wolof
        msg = (
            f"🍽️ MAMAMENÙ SEMAINE {semaine} (Wolof):\n"
            f"{recette['nom']}\n"
            f"Valeur: {recette['kcal']}kcal, {recette['proteines_g']}g protéines\n"
            f"Prix: ~{recette.get('prix_fcfa', 500)}FCFA\n"
            f"—Tapez 'AIDE' pour détails"
        )
    else:
        # Français
        msg = (
            f"🍽️ MAMAMENÙ SEMAINE {semaine}:\n"
            f"{recette['nom']}\n"
            f"Valeur: {recette['kcal']}kcal, {recette['proteines_g']}g protéines\n"
            f"Prix: ~{recette.get('prix_fcfa', 500)}FCFA\n"
            f"—Tapez 'AIDE' pour détails"
        )
    
    return msg

def formater_sms_alerte_orange(age_enfant_mois: int, langue: str = 'fr') -> str:
    """Envoyer alerte intensifiée si enfant détecté en ORANGE."""
    
    if langue == 'wo':
        return (
            "⚠️ ALERTE MAMAMENÙ (Wolof):\n"
            "Yoon xaj yu ne ba diiwax "
            "malnutrition di. Jeer ba nu recettes "
            "bu njëkk. Safara xamile ci dispensaire.\n"
            "—MAMAMENÙ"
        )
    else:
        return (
            "⚠️ ALERTE MAMAMENÙ:\n"
            "Votre enfant a besoin d'une meilleure nutrition.\n"
            "Nous envoyons recettes quotidiennes cette semaine.\n"
            "Consultez votre centre de santé.\n"
            "—MAMAMENÙ"
        )

def enregistrer_envoi(abonnee_id: int, recette_id: int, message: str, 
                     type_message: str = 'recette_semaine') -> bool:
    """Enregistrer un envoi SMS dans la BDD."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO envois_sms (abonnee_id, recette_id, message, type_message, statut)
    VALUES (?, ?, ?, ?, 'envoye')
    ''', (abonnee_id, recette_id, message, type_message))
    
    conn.commit()
    conn.close()
    return True

def obtenir_abonnees_pour_envoi_semain() -> List[Dict]:
    """Récupérer la liste des abonnées pour envoi hebdomadaire."""
    return get_abonnees_pour_envoi()

if __name__ == "__main__":
    # Test
    result = inscrire_mere(
        telephone="+221771234567",
        age_enfant_mois=12,
        region="Dakar",
        langue="fr",
        prenom="Mame"
    )
    print(result)
    
    # Recommander une recette
    rec = recommander_recette(12, 'fr')
    if rec['recette']:
        sms = formater_sms_recette(rec['recette'], 'fr', 1)
        print("\nSMS formé:")
        print(sms)
