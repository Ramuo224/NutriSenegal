# 🏥 NutriSénégal — Plateforme de Lutte Contre la Malnutrition Infantile

Une plateforme numérique intégrée conçue pour lutter contre la malnutrition infantile au Sénégal, réunissant trois outils complémentaires en un système cohérent.

## 📋 Vue d'ensemble

**NutriSénégal** articule trois modules interdépendants:

### 🔍 **NutriScan** — Dépistage communautaire
Outil de terrain utilisé par agents de santé communautaires. Photographie + mesures simples (poids, taille, âge, périmètre brachial) → calcul de score OMS → alerte SMS automatique si enfant à risque.

### 🍽️ **MamaMenu** — Prévention nutritionnelle
Les mères s'inscrivent par SMS avec l'âge de leur enfant → reçoivent chaque semaine une recette adaptée à l'âge + budget (aliments locaux <500 FCFA), en français ET wolof.

### 🗺️ **MaliMap** — Cartographie temps réel
Agrège données NutriScan + données contextuelles publiques (météo, prix FAO, pauvreté) → score de risque régional → alerte aux décideurs (ONG, Ministère) AVANT que les crises n'éclatent.

---

## 🚀 Démarrage rapide

### Prérequis
- **Python 3.8+**
- **pip** ou **conda**

### Installation

1. **Cloner/Naviguer vers le projet**
```bash
cd c:\Users\bmd tech\OneDrive\Desktop\Nutriage\nutrisenegal
```

2. **Créer un environnement virtuel** (optionnel mais recommandé)
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Lancer le serveur**
```bash
python main.py
```

Le serveur démarre sur **http://localhost:8000**

### Accès aux modules

| Module | URL |
|--------|-----|
| 🏠 Accueil | http://localhost:8000/ |
| 🔍 NutriScan | http://localhost:8000/api/nutriscan/formulaire |
| 🍽️ MamaMenu | http://localhost:8000/api/mamamenù/formulaire |
| 🗺️ MaliMap | http://localhost:8000/malimap |
| 📊 Dashboard | http://localhost:8000/dashboard |

---

## 📁 Structure du projet

```
nutrisenegal/
├── main.py                 # FastAPI — point d'entrée unique
├── db.py                   # SQLite — gestion BDD
├── nutriscan.py            # Module dépistage
├── mamamenù.py             # Module recettes SMS
├── malimap.py              # Module cartographie
├── sms.py                  # Gestion SMS (Twilio mock)
├── scheduler.py            # Scheduler APScheduler
├── requirements.txt        # Dépendances Python
├── data/
│   ├── recettes.json       # 50+ recettes (6-60 mois)
│   ├── regions.json        # 12 régions sénégalaises
│   └── prix.json           # Prix aliments simulés
├── templates/
│   ├── index.html          # Accueil
│   ├── nutriscan.html      # Formulaire dépistage
│   ├── mamamenù.html       # Inscription MamaMenu
│   ├── malimap.html        # Carte interactive
│   └── dashboard.html      # Admin dashboard
└── nutrisenegal.db         # BDD SQLite (généré)
```

---

## 🔧 API Endpoints

### NutriScan
```
POST   /api/nutriscan/enregistrer        # Enregistrer enfant
GET    /api/nutriscan/formulaire         # Formulaire HTML
```

### MamaMenu
```
POST   /api/mamamenù/inscrire            # Inscrire mère
POST   /api/mamamenù/sms-entrant         # Webhook SMS entrant
GET    /api/mamamenù/recette/{age_mois}  # Recette selon âge
GET    /api/mamamenù/formulaire          # Formulaire HTML
```

### MaliMap
```
GET    /api/malimap/regions              # Toutes régions + scores
GET    /api/malimap/region/{nom}         # Maj région spécifique
GET    /api/malimap/geojson              # Format GeoJSON (Folium)
GET    /malimap                          # Carte interactive
```

### Admin
```
GET    /api/admin/stats                  # Statistiques globales
GET    /api/admin/sms-log                # Historique SMS
GET    /health                           # Vérification santé
```

---

## 📊 Base de données

SQLite automatiquement créée au démarrage avec tables:
- **enfants** — Enfants dépistés (NutriScan)
- **alertes** — Alertes ORANGE/ROUGE
- **abonnees** — Mères inscrites (MamaMenu)
- **recettes** — 50+ recettes par âge
- **envois_sms** — Historique envois
- **donnees_regions** — Scores régionaux (MaliMap)
- **agents** — Agents de santé

---

## ⏰ Scheduler automatisé

| Tâche | Fréquence |
|-------|-----------|
| Maj régions (scores) | Toutes 3h |
| Mise à jour prix FAO | 06:00 quotidien |
| Mise à jour météo | 06:00 + 18:00 |
| Envoi recettes MamaMenu | Lundi 08:00 |

---

## 📱 SMS (Mock pour hackathon)

Par défaut, SMS sont **simulés** (affichage console). Pour utiliser **Twilio réel**:

1. Créer un fichier `.env`:
```
TWILIO_ENABLED=true
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE=+221771234567
```

2. Charger variables env:
```python
from dotenv import load_dotenv
load_dotenv()
```

---

## 🧪 Tester le flux complet

### 1. Ajouter un enfant (NutriScan)
```bash
curl -X POST http://localhost:8000/api/nutriscan/enregistrer \
  -H "Content-Type: application/json" \
  -d '{
    "prenom": "Marie",
    "age_mois": 18,
    "region": "Dakar",
    "poids_kg": 9.5,
    "taille_cm": 76,
    "agent_nom": "Aram Fall"
  }'
```

Réponse:
```json
{
  "succes": true,
  "enfant_id": 1,
  "score": "ORANGE",
  "message": "⚠️ MALNUTRITION MODÉRÉE — Suivi renforcé recommandé",
  "imc": 16.42,
  "alerte": true,
  "sms_envoye": true
}
```

### 2. Inscrire une mère (MamaMenu)
```bash
curl -X POST http://localhost:8000/api/mamamenù/inscrire \
  -H "Content-Type: application/json" \
  -d '{
    "telephone": "+221771234567",
    "age_enfant_mois": 12,
    "region": "Dakar",
    "langue": "fr",
    "prenom": "Fatou"
  }'
```

### 3. Récupérer statistiques
```bash
curl http://localhost:8000/api/admin/stats
```

### 4. Voir régions par risque
```bash
curl http://localhost:8000/api/malimap/regions
```

---

## 🎯 Fonctionnalités clés

✅ **Hors ligne partielle** — Synchronisation dès connexion dispo  
✅ **Multilingue** — Français + Wolof  
✅ **Déploiement léger** — Raspberry Pi, VPS 5$/mois  
✅ **2G compatible** — Taille messages minimale  
✅ **Standards OMS** — IMC, scores Z-score  
✅ **Webhook SMS** — Intégration Twilio (mock)  
✅ **Real-time mapping** — Folium + Leaflet  
✅ **Scheduler intégré** — APScheduler  

---

## 📈 Scalabilité future

- [ ] Connexion BD PostgreSQL en production
- [ ] Authentification JWT agents/ONG
- [ ] Export PDF rapports régionaux
- [ ] Intégration Open-Meteo (vraie météo)
- [ ] Intégration FAO GIEWS (vrais prix)
- [ ] Mobile app native (React Native)
- [ ] Sync cloud (AWS S3)

---

## 📚 Ressources

- **OMS Nutrition**: https://www.who.int/teams/nutrition-physical-activity
- **EDS Sénégal 2023**: https://www.ansd.sn/
- **Twilio SMS**: https://www.twilio.com/
- **Open-Meteo**: https://open-meteo.com/
- **FAO GIEWS**: https://www.fao.org/giews/pricelists/

---

## 👥 Équipe

**Hackathon 48h — Nutrition Sénégal 2026**

Modules:
- 🔍 **NutriScan** — Agent A
- 🍽️ **MamaMenu** — Agent B
- 🗺️ **MaliMap** — Agent C
- 🔌 **Socle commun** — Tous ensemble

---

## 📄 Licence

Projet à usage social/humanitaire. Libre de modification pour contexte sénégalais/africain.

---

## ✉️ Support

Pour questions/bugs: [Créer une issue]

---

**Dernière mise à jour**: Mai 2026  
**Version**: 1.0.0  
**Status**: ✅ Prêt pour hackathon
