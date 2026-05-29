🚀 **DÉMARRAGE RAPIDE — NutriSénégal**
================================

**La plateforme est DÉJÀ EN LIGNE sur votre système!**

## ⚡ Accès immédiat

| URL | Fonction |
|-----|----------|
| **http://localhost:8000** | 🏠 Accueil |
| **http://localhost:8000/api/nutriscan/formulaire** | 🔍 NutriScan (dépistage) |
| **http://localhost:8000/api/mamamenù/formulaire** | 🍽️ MamaMenu (recettes SMS) |
| **http://localhost:8000/malimap** | 🗺️ MaliMap (carte risque) |
| **http://localhost:8000/dashboard** | 📊 Dashboard admin |

---

## 📋 Vérifier que le serveur tourne

Le terminal affichant le serveur FastAPI doit montrer:
```
✅ Base de données initialisée: nutrisenegal.db
✅ 10 recettes chargées dans la BDD
✅ 12 régions chargées dans la BDD
✅ Scheduler démarré
✅ NutriSénégal prêt!
INFO: Uvicorn running on http://0.0.0.0:8000
```

Si le serveur s'est arrêté, redémarrer:
```bash
cd c:\Users\bmd tech\OneDrive\Desktop\Nutriage\nutrisenegal
python main.py
```

---

## 🧪 Tests rapides

### 1️⃣ Ajouter un enfant (NutriScan)

Via navigateur: **http://localhost:8000/api/nutriscan/formulaire**

Ou en Python:
```python
import requests

data = {
    'prenom': 'Aïssatou',
    'age_mois': 15,
    'region': 'Diourbel',
    'poids_kg': 7.2,
    'taille_cm': 70,
    'agent_nom': 'Aminata Sow'
}

response = requests.post('http://localhost:8000/api/nutriscan/enregistrer', json=data)
print(response.json())
```

**Résultat attendu:**
```json
{
  "succes": true,
  "score": "ROUGE",  // ou ORANGE, ou VERT
  "message": "⚠️ MALNUTRITION SÉVÈRE — Référer immédiatement",
  "enfant_id": 2,
  "sms_envoye": true
}
```

---

### 2️⃣ Inscrire une mère (MamaMenu)

Via navigateur: **http://localhost:8000/api/mamamenù/formulaire**

Ou en Python:
```python
data = {
    'telephone': '+221781234567',
    'age_enfant_mois': 10,
    'region': 'Saint-Louis',
    'langue': 'wo',  # ou 'fr'
    'prenom': 'Mame'
}

response = requests.post('http://localhost:8000/api/mamamenù/inscrire', json=data)
print(response.json())
```

**Résultat:** Recette SMS envoyée automatiquement ✓

---

### 3️⃣ Voir la carte (MaliMap)

Via navigateur: **http://localhost:8000/malimap**

- Carte interactive Senegal avec 12 régions
- Sidebar avec scores de risque
- Légende de couleurs

---

### 4️⃣ Dashboard Admin

Via navigateur: **http://localhost:8000/dashboard**

Affiche:
- Statistiques globales (enfants, alertes, SMS)
- Régions par risque
- Historique SMS

---

## 🔧 Configuration optionnelle

### Activer Twilio (vraiment envoyer des SMS)

1. Créer fichier `.env`:
```
TWILIO_ENABLED=true
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE=+221771234567
```

2. Redémarrer le serveur

---

## 📱 Webhook SMS entrant

Pour intégrer Twilio **webhook entrant** (mères qui s'inscrivent par SMS):

1. Aller sur Twilio console
2. Configurer webhook POST vers:
   ```
   https://your-domain.com/api/mamamenù/sms-entrant?telephone=+221XXXXXXX&message=12
   ```

3. Les SMS reçus inscriront automatiquement les mères

---

## 🐛 Troubleshooting

### Erreur: "Address already in use"
Le port 8000 est occupé. Tuer le processus Python:
```bash
Get-Process python | Stop-Process
python main.py
```

### Base de données verrouillée
Supprimer `nutrisenegal.db` et relancer:
```bash
rm c:\Users\bmd tech\OneDrive\Desktop\Nutriage\nutrisenegal\nutrisenegal.db
python main.py
```

### Templates HTML manquants
Vérifier que le dossier `templates/` existe avec tous les fichiers `.html`

---

## 📊 Données de démo

**3 enfants pré-dépistés (pour tester):**

1. Marie, 18m, Dakar — Score VERT (IMC 16.45)
2. Aïssatou, 20m, Diourbel — Score ORANGE (IMC 12.8)
3. Fatou, 14m, Tambacounda — Score ROUGE (IMC 10.2)

**1 mère inscrite:**
- Fatou, +221771234567, enfant 12m, Dakar

---

## 🎯 Prochaines étapes pour hackathon

1. ✅ Backend complet
2. ⏳ Tests intensifs (ajouter 50-100 cas de test)
3. ⏳ Optimisations 2G (réduire taille messages)
4. ⏳ Carte GeoJSON avancée (Folium)
5. ⏳ Export PDF rapports régionaux

---

## 📞 Support API

Documentation complète: [README.md](README.md)

API REST:
- `GET /health` — Vérifier santé serveur
- `POST /api/nutriscan/enregistrer` — Ajouter enfant
- `POST /api/mamamenù/inscrire` — Inscrire mère
- `GET /api/malimap/regions` — Toutes régions + scores
- `GET /api/admin/stats` — Stats globales

---

**Merci d'avoir utilisé NutriSénégal! 🙏**

*Ensemble contre la malnutrition infantile au Sénégal.*
