"""
NutriScan — Dépistage communautaire assisté par IA
Module pour l'analyse nutritionnelle des enfants par agents de santé
"""

from typing import Tuple, Dict, Optional
from db import get_connection, ajouter_enfant

def score_risque(poids_kg: float, taille_cm: float, age_mois: int, 
                perimetre_brachial: Optional[float] = None) -> Tuple[str, str, Dict]:
    """
    Calculer le score de risque nutritionnel basé sur standards OMS.
    PRIORITÉ: MUAC > IMC (fallback)
    
    MUAC (Périmètre brachial) seuils enfants 6-59m:
    - < 11.5 cm: Malnutrition sévère aiguë (MAG)
    - 11.5-12.5 cm: Malnutrition modérée aiguë (MMA)
    - > 12.5 cm: Normal
    
    Retourne: (score, message, details_dict)
    """
    imc = poids_kg / ((taille_cm / 100) ** 2)
    details = {"imc": imc, "muac": perimetre_brachial}
    
    # ============================================
    # PRIORITÉ 1: MUAC (Périmètre brachial)
    # ============================================
    if perimetre_brachial is not None:
        if perimetre_brachial < 11.5:
            score = "ROUGE"
            message = f"🔴 MALNUTRITION SÉVÈRE AIGUË (MUAC {perimetre_brachial}cm < 11.5) — RÉFÉRER IMMÉDIATEMENT"
            details["mesure_primaire"] = "MUAC"
        elif perimetre_brachial < 12.5:
            score = "ORANGE"
            message = f"🟠 MALNUTRITION MODÉRÉE AIGUË (MUAC {perimetre_brachial}cm: 11.5-12.5) — Suivi renforcé"
            details["mesure_primaire"] = "MUAC"
        else:
            score = "VERT"
            message = f"✅ Normal (MUAC {perimetre_brachial}cm > 12.5)"
            details["mesure_primaire"] = "MUAC"
        
        # DOUBLE-CHECK: Si IMC aussi critique + MUAC critique → alerte renforcée
        if score in ["ROUGE", "ORANGE"]:
            if imc < 11.5:
                message += " ⚠️⚠️ [IMC aussi critique! Double malnutrition]"
                details["double_alerte"] = True
    
    # ============================================
    # FALLBACK: IMC (si MUAC manquant)
    # ============================================
    else:
        if imc < 11.5:
            score = "ROUGE"
            message = f"🔴 MALNUTRITION SÉVÈRE (IMC {imc:.2f} < 11.5) — RÉFÉRER IMMÉDIATEMENT"
            details["mesure_primaire"] = "IMC"
        elif imc < 13.0:
            score = "ORANGE"
            message = f"🟠 MALNUTRITION MODÉRÉE (IMC {imc:.2f}: 11.5-13.0) — Suivi renforcé"
            details["mesure_primaire"] = "IMC"
        else:
            score = "VERT"
            message = f"✅ Normal (IMC {imc:.2f} ≥ 13.0)"
            details["mesure_primaire"] = "IMC"
    
    return score, message, details

def valider_mesures(poids_kg: float, taille_cm: float, age_mois: int) -> Tuple[bool, str]:
    """Valider que les mesures sont plausibles."""
    if not (1 < poids_kg < 50):
        return False, "❌ Poids doit être entre 1 et 50 kg"
    if not (30 < taille_cm < 120):
        return False, "❌ Taille doit être entre 30 et 120 cm"
    if not (0 < age_mois < 60):
        return False, "❌ Âge doit être entre 0 et 60 mois"
    return True, "✅ Mesures valides"

def enregistrer_enfant(prenom: str, age_mois: int, region: str, poids_kg: float,
                       taille_cm: float, perimetre_brachial: Optional[float] = None,
                       agent_id: Optional[int] = None, agent_nom: Optional[str] = None,
                       agent_zone: Optional[str] = None) -> Dict:
    """Enregistrer un enfant et retourner score + alerte."""
    
    # Valider mesures
    valide, msg_validation = valider_mesures(poids_kg, taille_cm, age_mois)
    if not valide:
        return {"succes": False, "erreur": msg_validation}
    
    # Calculer score (MUAC prioritaire, IMC fallback)
    score, message, details = score_risque(poids_kg, taille_cm, age_mois, perimetre_brachial)
    
    # Enregistrer en BDD
    enfant_id = ajouter_enfant(
        prenom=prenom,
        age_mois=age_mois,
        region=region,
        poids_kg=poids_kg,
        taille_cm=taille_cm,
        perimetre_brachial=perimetre_brachial,
        agent_id=agent_id,
        agent_nom=agent_nom,
        agent_zone=agent_zone
    )
    
    return {
        "succes": True,
        "enfant_id": enfant_id,
        "score": score,
        "message": message,
        "imc": round(details["imc"], 2),
        "muac": perimetre_brachial,
        "mesure_primaire": details.get("mesure_primaire"),
        "double_alerte": details.get("double_alerte", False),
        "alerte": score in ["ORANGE", "ROUGE"],
        "details": {
            "prenom": prenom,
            "age_mois": age_mois,
            "region": region,
            "poids_kg": poids_kg,
            "taille_cm": taille_cm,
            "perimetre_brachial": perimetre_brachial
        }
    }

def generer_sms_alerte(enfant: Dict, score: str, centre_sante_tel: str) -> str:
    """Générer le message SMS pour alerte au centre de santé."""
    muac_info = f"MUAC {enfant.get('perimetre_brachial')}cm" if enfant.get('perimetre_brachial') else f"IMC {enfant.get('imc')}"
    
    if score == "ROUGE":
        emoji = "🔴"
        urgence = "CRITIQUE — RÉFÉRER IMMÉDIATEMENT"
    else:
        emoji = "🟠"
        urgence = "MODÉRÉE — Suivi renforcé"
    
    return (
        f"{emoji} NUTRISCAN ALERTE {score}\n"
        f"Enfant: {enfant['prenom']} ({enfant['age_mois']}m)\n"
        f"Mesure: {muac_info}\n"
        f"Zone: {enfant.get('agent_zone', '?')}\n"
        f"Agent: {enfant.get('agent_nom', '?')}\n"
        f"Statut: {urgence}\n"
        f"ID: {enfant.get('enfant_id', '?')}"
    )

if __name__ == "__main__":
    # Test
    result = enregistrer_enfant(
        prenom="Marie",
        age_mois=18,
        region="Dakar",
        poids_kg=9.5,
        taille_cm=76,
        agent_nom="Aram Fall",
        agent_zone="Pikine"
    )
    print(result)
