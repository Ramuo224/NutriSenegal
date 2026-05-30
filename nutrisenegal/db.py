import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

# Utiliser un chemin absolu pour la base de données (compatible Render)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nutrisenegal.db")

def init_db():
    """Initialiser la base de données SQLite avec les 4 tables principales."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table enfants (NutriScan)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS enfants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prenom TEXT NOT NULL,
        age_mois INTEGER NOT NULL,
        region TEXT NOT NULL,
        poids_kg REAL NOT NULL,
        taille_cm REAL NOT NULL,
        perimetre_brachial REAL,
        score_risque TEXT CHECK(score_risque IN ('VERT', 'ORANGE', 'ROUGE')),
        date_saisie TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        agent_id INTEGER,
        agent_nom TEXT,
        agent_zone TEXT
    )
    ''')
    
    # Table alertes (NutriScan → MaliMap)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS alertes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enfant_id INTEGER NOT NULL,
        region TEXT NOT NULL,
        score TEXT CHECK(score IN ('VERT', 'ORANGE', 'ROUGE')),
        date_alerte TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        centre_notifie BOOLEAN DEFAULT 0,
        sms_envoye BOOLEAN DEFAULT 0,
        FOREIGN KEY(enfant_id) REFERENCES enfants(id)
    )
    ''')
    
    # Table abonnees (MamaMenu)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS abonnees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telephone TEXT UNIQUE NOT NULL,
        prenom TEXT,
        age_enfant_mois INTEGER NOT NULL,
        region TEXT NOT NULL,
        langue TEXT DEFAULT 'fr' CHECK(langue IN ('fr', 'wo')),
        intensifie BOOLEAN DEFAULT 0,
        date_inscription TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Table recettes (MamaMenu)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS recettes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        age_min_mois INTEGER NOT NULL,
        age_max_mois INTEGER NOT NULL,
        kcal INTEGER NOT NULL,
        proteines_g REAL NOT NULL,
        fer_mg REAL NOT NULL,
        vitamine_a_ug REAL,
        ingredients TEXT NOT NULL,
        instructions TEXT NOT NULL,
        langue TEXT DEFAULT 'fr',
        prix_fcfa REAL
    )
    ''')
    
    # Table historique envois SMS (MamaMenu)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS envois_sms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        abonnee_id INTEGER NOT NULL,
        recette_id INTEGER,
        message TEXT,
        type_message TEXT,
        date_envoi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        statut TEXT DEFAULT 'envoye',
        FOREIGN KEY(abonnee_id) REFERENCES abonnees(id),
        FOREIGN KEY(recette_id) REFERENCES recettes(id)
    )
    ''')
    
    # Table données régionales (MaliMap)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS donnees_regions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        region TEXT UNIQUE NOT NULL,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        pluie_deficit REAL DEFAULT 0,
        prix_alimentaires_hausse REAL DEFAULT 0,
        cas_nutriscan_30j INTEGER DEFAULT 0,
        densite_medicale REAL DEFAULT 0,
        acces_eau_potable REAL DEFAULT 0,
        score_risque REAL DEFAULT 0,
        date_maj TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Table agents de santé
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        zone TEXT NOT NULL,
        telephone TEXT UNIQUE,
        region TEXT NOT NULL,
        actif BOOLEAN DEFAULT 1,
        date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    print(f"✅ Base de données initialisée: {DB_PATH}")

def get_connection():
    """Obtenir une connexion à la BDD."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Accès par nom de colonne
    return conn

def ajouter_enfant(prenom: str, age_mois: int, region: str, poids_kg: float, 
                   taille_cm: float, perimetre_brachial: Optional[float] = None,
                   agent_id: Optional[int] = None, agent_nom: Optional[str] = None,
                   agent_zone: Optional[str] = None) -> int:
    """Ajouter un enfant à la BDD (NutriScan)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Calcul du score
    imc = poids_kg / ((taille_cm / 100) ** 2)
    if imc < 11.5:
        score_risque = "ROUGE"
    elif imc < 13.0:
        score_risque = "ORANGE"
    else:
        score_risque = "VERT"
    
    cursor.execute('''
    INSERT INTO enfants (prenom, age_mois, region, poids_kg, taille_cm, 
                        perimetre_brachial, score_risque, agent_id, agent_nom, agent_zone)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (prenom, age_mois, region, poids_kg, taille_cm, perimetre_brachial, 
          score_risque, agent_id, agent_nom, agent_zone))
    
    enfant_id = cursor.lastrowid
    
    # Créer alerte si score ORANGE ou ROUGE
    if score_risque in ["ORANGE", "ROUGE"]:
        cursor.execute('''
        INSERT INTO alertes (enfant_id, region, score)
        VALUES (?, ?, ?)
        ''', (enfant_id, region, score_risque))
    
    conn.commit()
    conn.close()
    return enfant_id

def ajouter_abonnee(telephone: str, age_enfant_mois: int, region: str, 
                    langue: str = 'fr', prenom: Optional[str] = None) -> int:
    """Inscrire une mère à MamaMenu."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO abonnees (telephone, prenom, age_enfant_mois, region, langue)
    VALUES (?, ?, ?, ?, ?)
    ''', (telephone, prenom, age_enfant_mois, region, langue))
    
    abonnee_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return abonnee_id

def get_recettes_pour_age(age_mois: int, langue: str = 'fr') -> List[Dict[str, Any]]:
    """Obtenir recettes adaptées à l'âge."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT * FROM recettes 
    WHERE age_min_mois <= ? AND age_max_mois >= ? AND langue = ?
    ORDER BY RANDOM()
    LIMIT 1
    ''', (age_mois, age_mois, langue))
    
    result = cursor.fetchall()
    conn.close()
    return [dict(r) for r in result]

def charger_recettes_depuis_json(recettes_json):
    """Charger les recettes depuis JSON dans la BDD."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Vider table existante
    cursor.execute('DELETE FROM recettes')
    
    for recette in recettes_json:
        cursor.execute('''
        INSERT INTO recettes (nom, age_min_mois, age_max_mois, kcal, proteines_g, 
                             fer_mg, vitamine_a_ug, ingredients, instructions, langue, prix_fcfa)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (recette['nom'], recette['age_min_mois'], recette['age_max_mois'],
              recette['kcal'], recette['proteines_g'], recette['fer_mg'],
              recette.get('vitamine_a_ug', 0), recette['ingredients'],
              recette['instructions'], recette.get('langue', 'fr'), 
              recette.get('prix_fcfa', 500)))
    
    conn.commit()
    conn.close()
    print(f"✅ {len(recettes_json)} recettes chargées dans la BDD")

def charger_regions_depuis_json(regions_json):
    """Charger les régions depuis JSON dans la BDD."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Vider table existante
    cursor.execute('DELETE FROM donnees_regions')
    
    for region in regions_json:
        cursor.execute('''
        INSERT INTO donnees_regions (region, lat, lon, densite_medicale, acces_eau_potable)
        VALUES (?, ?, ?, ?, ?)
        ''', (region['nom'], region['lat'], region['lon'], 
              region.get('densite_medicale', 0.5), region.get('acces_eau_potable', 60)))
    
    conn.commit()
    conn.close()
    print(f"✅ {len(regions_json)} régions chargées dans la BDD")

def get_alertes_recentes(jours: int = 30) -> List[Dict[str, Any]]:
    """Obtenir alertes des 30 derniers jours pour MaliMap."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT a.*, e.prenom, e.poids_kg, e.taille_cm 
    FROM alertes a
    JOIN enfants e ON a.enfant_id = e.id
    WHERE datetime(a.date_alerte) >= datetime('now', ? || ' days')
    ''', (f'-{jours}',))
    
    result = cursor.fetchall()
    conn.close()
    return [dict(r) for r in result]

def get_abonnees_pour_envoi() -> List[Dict[str, Any]]:
    """Obtenir abonnées pour envoi hebdo."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT * FROM abonnees WHERE 1=1
    ''')
    
    result = cursor.fetchall()
    conn.close()
    return [dict(r) for r in result]

if __name__ == "__main__":
    init_db()
