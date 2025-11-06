# 🧪 Test du Modèle ML en Production

## 📋 Vue d'ensemble

Script simplifié pour tester le modèle de prédiction de retards en production.

## 🏗️ Architecture

### Fichiers principaux

1. **`test_production.py`** - Script d'orchestration principal (150 lignes)
2. **`flight_delay_predictor.py`** - Classe ML principale
3. **`config/collection_config.py`** - Configuration centralisée
4. **`utils/postgresql_manager.py`** - Gestionnaire PostgreSQL avec méthodes ML

### Configuration

Tous les paramètres sont centralisés dans `config/collection_config.py` :

```python
@dataclass
class CollectionConfig:
    # PostgreSQL
    postgresql_uri: str = "postgresql://postgres:password@localhost:5433/dst_ml"
    
    # Machine Learning
    ml_model_dir: str = "machine_learning/model"
    ml_model_config_path: str = None  # None = modèle le plus récent
    ml_test_n_flights: int = 1000  # Nombre de vols à tester
```

## 🚀 Utilisation

### Lancer le test

```bash
cd "machine_learning"
python test_production.py
```

### Ce que fait le script

1. **Charge le modèle** - Utilise le modèle le plus récent ou celui spécifié
2. **Récupère les données** - Lit les N derniers vols depuis PostgreSQL (view "all")
3. **Génère les prédictions** - Applique le modèle ML
4. **Sauvegarde les résultats** - Met à jour les colonnes `delay_prob` et `delay_risk_level`

### Sortie

```
🧪 TEST DU MODÈLE ML EN PRODUCTION
==================================================================
📂 Utilisation du modèle le plus récent: model/production_config_20251104_084632.json
🤖 Chargement du modèle ML...

📊 INFORMATIONS DU MODÈLE
==================================================================
Type de modèle: XGBClassifier
Seuil de retard: 15 minutes
Seuil optimal: 0.752
Seuils de risque: Faible < 0.345 < Modéré < 0.752 < Élevé

📈 MÉTRIQUES D'ENTRAÎNEMENT:
  ROC-AUC: 0.856
  PR-AUC: 0.673
  F1-Score: 0.598
  Précision: 0.792
  Rappel: 0.481
==================================================================

🔌 Connexion à PostgreSQL...
📊 Récupération des 1000 derniers vols...
✅ 1000 vols récupérés
🔮 Application du modèle de prédiction...
✅ 1000 prédictions générées
   Retards prédits: 127
   Probabilité moyenne: 23.45%

📊 Distribution des niveaux de risque:
   Faible: 653 (65.3%)
   Modéré: 220 (22.0%)
   Élevé: 127 (12.7%)

💾 Sauvegarde des prédictions dans PostgreSQL...
✅ 1000 lignes mises à jour (delay_prob + delay_risk_level)

==================================================================
✅ TEST TERMINÉ AVEC SUCCÈS
==================================================================
Vols récupérés: 1000
Prédictions générées: 1000
Mises à jour PostgreSQL: 1000
Durée totale: 12.3s
==================================================================
```

## 🔧 API PostgreSQLManager

### Nouvelles méthodes ML

```python
# Récupérer les N derniers vols
df = pg.fetch_last_n_flights(n=1000)

# Mettre à jour les prédictions
updated_count = pg.update_flight_predictions(predictions_df)
```

## 📊 Résultats dans PostgreSQL

Le script met à jour la table `flight` :

| Colonne | Type | Description |
|---------|------|-------------|
| `delay_prob` | NUMERIC | Probabilité de retard (0.0 à 1.0) |
| `delay_risk_level` | VARCHAR | Niveau de risque ("Faible", "Modéré", "Élevé") |

## 🎯 Avantages du refactoring

- ✅ **-349 lignes de code** (509 supprimées, 160 ajoutées)
- ✅ **Configuration centralisée** (principe DRY)
- ✅ **Responsabilités claires** (principe SRP)
- ✅ **Pas de wrappers inutiles** (principe YAGNI)
- ✅ **Code maintenable** (principe KISS)

## 📁 Fichiers supprimés

- ❌ `production_predictor.py` (225 lignes) - Wrapper inutile
- ❌ `test_model_production.py` (272 lignes) - Remplacé par `test_production.py`
- ❌ `config_test.py` (12 lignes) - Config centralisée

## 🔄 Comparaison avant/après

### Avant (complexe)
```python
# config_test.py
POSTGRESQL_URI = "postgresql://..."
MODEL_CONFIG_PATH = None
N_FLIGHTS_TO_TEST = 1000

# test_model_production.py
from production_predictor import FlightDelayProductionPredictor

tester = ModelProductionTester(POSTGRESQL_URI, MODEL_CONFIG_PATH)
tester.run_test(N_FLIGHTS_TO_TEST)
```

### Après (simple)
```python
# config/collection_config.py (configuration globale)
config = get_default_config()

# test_production.py (orchestration simple)
pg = PostgreSQLManager(config.postgresql_uri)
predictor = FlightDelayPredictor.load_model(config.ml_model_config_path)
df = pg.fetch_last_n_flights(config.ml_test_n_flights)
predictions = predictor.predict_from_csv(...)
pg.update_flight_predictions(predictions)
```

## 🎓 Principes appliqués

- **DRY** (Don't Repeat Yourself) : Configuration centralisée
- **KISS** (Keep It Simple, Stupid) : Script linéaire sans abstractions inutiles
- **YAGNI** (You Aren't Gonna Need It) : Suppression des wrappers
- **SRP** (Single Responsibility Principle) : Chaque classe a une responsabilité claire

