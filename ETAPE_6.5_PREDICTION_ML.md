# 🤖 Prédiction ML Automatique - Étape 6.5

## 📋 Vue d'ensemble

L'étape 6.5 applique automatiquement le modèle de machine learning sur les vols **immédiatement après leur insertion** dans PostgreSQL.

## 🎯 Avantages

✅ **Prédiction ciblée** : Seuls les vols nouvellement insérés sont traités  
✅ **Performance optimale** : Utilise les IDs retournés par l'insertion  
✅ **Pas de duplication** : Pas de réexécution sur les vols déjà traités  
✅ **Temps réel** : Les prédictions sont disponibles immédiatement  
✅ **Activable/désactivable** : Via `enable_ml_prediction` dans la config

## 🏗️ Architecture

### Workflow complet (8 étapes)

```
1. Collecte vols temps réel → MongoDB
2. Collecte météo (METAR/TAF) → MongoDB
3. Collecte vols passés → MongoDB
4. Association vols-METAR → MongoDB
5. Association vols-TAF → MongoDB
6. Insertion PostgreSQL → Table flight (retourne les IDs insérés)
   ↓
7. 🆕 Prédiction ML → Mise à jour delay_prob + delay_risk_level
   ↓
8. Mise à jour vols passés → PostgreSQL
```

## 🔧 Modifications apportées

### 1. PostgreSQLManager

**Méthode modifiée** : `insert_flights_batch()`
- **Avant** : `return int` (nombre d'insérés)
- **Après** : `return tuple` (nombre_insérés, liste_ids_insérés)

```python
# Utilise RETURNING id pour récupérer les IDs
INSERT INTO flight (...) VALUES (...) RETURNING id
```

**Nouvelle méthode** : `fetch_flights_by_ids(flight_ids: List[int])`
- Récupère les vols depuis la vue `"all"` par leurs IDs
- Retourne un DataFrame pandas prêt pour la prédiction

```python
SELECT * FROM public."all" WHERE f_id = ANY(%s)
```

### 2. FlightOrchestrator

**Méthode modifiée** : `insert_weather_and_flight_data_to_postgres()`
- Stocke les IDs insérés dans `results.details['inserted_flight_ids']`

**Nouvelle méthode** : `predict_flights_ml(flight_ids: List[int])`
- Récupère les vols par IDs
- Crée un fichier CSV temporaire
- Charge le modèle ML
- Génère les prédictions
- Met à jour PostgreSQL
- Nettoie le fichier temporaire

### 3. ExecutionManager

**Nouvelle étape 6.5** ajoutée entre insertion (6) et mise à jour (7)

```python
# ÉTAPE 6.5: Prédiction ML sur les vols nouvellement insérés
if self.config.enable_ml_prediction and results_postgres.success:
    inserted_ids = results_postgres.details['inserted_flight_ids']
    results_ml = orchestrator.predict_flights_ml(inserted_ids)
```

### 4. CollectionConfig

**Nouveau paramètre** :
```python
enable_ml_prediction: bool = True  # Active la prédiction ML automatique
```

## 🚀 Utilisation

### Configuration

**Fichier** : `config/collection_config.py`

```python
@dataclass
class CollectionConfig:
    # Machine Learning
    ml_model_dir: str = "machine_learning/model"
    ml_model_config_path: str = None  # None = modèle le plus récent
    enable_ml_prediction: bool = True  # ⬅️ Active l'étape 6.5
```

### Exécution

```bash
cd orchestration
python main.py
```

### Sortie attendue

```
[10:30:45] Session ID global: 20251106_103045_123
[10:30:45] → ÉTAPE 6: Insertion données météo et vols dans PostgreSQL...
[10:30:47]   ✓ Étape 6 réussie

[10:30:49] → ÉTAPE 6.5: Prédiction ML sur vols insérés...
[10:30:49] === ÉTAPE 6.5: PRÉDICTION ML ===
[10:30:49] 127 vols à prédire
[10:30:50] 📊 Récupération des 127 vols depuis la vue 'all'...
[10:30:50] ✅ 127 vols récupérés
[10:30:51] 🤖 Chargement du modèle: machine learning/model/production_config_20251104_084632.json
[10:30:52] 🔮 Génération des prédictions...
[10:30:53] ✅ 127 prédictions générées
[10:30:53]    Probabilité moyenne: 23.45%
[10:30:53]    Distribution risque: {'Faible': 85, 'Modéré': 28, 'Élevé': 14}
[10:30:53] 💾 Mise à jour des prédictions dans PostgreSQL...
[10:30:54] ✅ 127 lignes mises à jour (delay_prob + delay_risk_level)
[10:30:54]   ✓ Étape 6.5 réussie

[10:30:56] → ÉTAPE 7: Mise à jour vols PostgreSQL avec données passées...
```

## 📊 Résultats dans PostgreSQL

Après l'étape 6.5, la table `flight` contient :

| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| `id` | INTEGER | ID du vol | 12345 |
| `flight_number` | VARCHAR | Numéro de vol | AF1234 |
| `from_airport` | VARCHAR | Aéroport de départ | CDG |
| `to_airport` | VARCHAR | Aéroport d'arrivée | JFK |
| `delay_prob` | NUMERIC | **🆕 Probabilité de retard** | 0.234 (23.4%) |
| `delay_risk_level` | VARCHAR | **🆕 Niveau de risque** | "Faible" |

### Requête de vérification

```sql
-- Vérifier les prédictions des derniers vols insérés
SELECT 
    flight_number,
    from_airport,
    to_airport,
    departure_scheduled_utc,
    delay_prob,
    delay_risk_level,
    created_at
FROM flight
WHERE delay_prob IS NOT NULL
ORDER BY created_at DESC
LIMIT 20;
```

## 🎯 Comparaison avec test_production.py

| Aspect | test_production.py | Étape 6.5 automatique |
|--------|-------------------|----------------------|
| **Déclenchement** | Manuel | Automatique |
| **Cible** | N derniers vols (paramétrable) | Vols nouvellement insérés |
| **Timing** | À la demande | Immédiatement après insertion |
| **Use case** | Test, analyse, rétrofit | Production temps réel |
| **Configuration** | Script standalone | Intégré au workflow |

**Complémentarité** :
- **Étape 6.5** : Pour les nouveaux vols en temps réel
- **test_production.py** : Pour réappliquer le modèle sur l'historique

## 🔍 Détection automatique du modèle

Si `ml_model_config_path = None`, le système cherche le modèle le plus récent :

```python
model_dir = Path("machine_learning/model")
config_files = list(model_dir.glob("production_config_*.json"))
model_config = max(config_files, key=lambda p: p.stat().st_mtime)  # Le plus récent
```

## ⚙️ Désactivation

Pour désactiver l'étape 6.5 :

```python
# config/collection_config.py
enable_ml_prediction: bool = False  # ⬅️ Désactive l'étape 6.5
```

Le workflow devient alors :
```
1-6: Collecte + associations + insertion
7: Mise à jour vols passés
(pas d'étape ML)
```

## 🧹 Gestion des fichiers temporaires

```python
# Création sécurisée
with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
    df_flights.to_csv(tmp.name, index=False)
    temp_csv = tmp.name

# Nettoyage garanti (bloc finally)
finally:
    if temp_csv and os.path.exists(temp_csv):
        os.unlink(temp_csv)
```

## 📈 Métriques de performance

L'étape 6.5 affiche :
- Nombre de vols traités
- Probabilité moyenne de retard
- Distribution des niveaux de risque (Faible/Modéré/Élevé)
- Nombre de lignes PostgreSQL mises à jour
- Durée d'exécution

## 🎓 Principes respectés

✅ **DRY** : Réutilise `fetch_flights_by_ids()` et `update_flight_predictions()`  
✅ **KISS** : Workflow linéaire clair  
✅ **SRP** : Chaque méthode a une responsabilité unique  
✅ **Performance** : Seulement les nouveaux vols, pas de requête globale  
✅ **Robustesse** : Gestion d'erreurs, nettoyage garanti, déconnexion PostgreSQL

## 🚀 Prochaines évolutions possibles

- [ ] Parallélisation des prédictions par batch
- [ ] Cache du modèle ML entre exécutions
- [ ] Métriques de performance dans CollectionResults
- [ ] Webhook pour notifier les prédictions à risque élevé
- [ ] Dashboard temps réel des prédictions

