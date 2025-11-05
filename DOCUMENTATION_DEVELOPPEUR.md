# 📋 Documentation Développeur - Projet Airlines Data Collector

## 🎯 Objectif du Projet

Ce projet collecte des données de vols en temps réel et des données météorologiques pour permettre la prédiction des retards de vols. Il constitue un pipeline de données complet avec collecte, traitement, association et stockage dans MongoDB et PostgreSQL.

## 📁 Structure du Projet

```
projet-avril25_cde_airlines/
├── 📁 config/               # Configuration et logging
│   ├── collection_config.py # Configuration centralisée
│   └── simple_logger.py     # Système de logging
├── 📁 data/                 # Collecteurs de données
│   ├── flight_data_scrapper.py    # Collecte vols (airportinfo.live)
│   ├── metar_collector.py     # Collecte METAR (aviationweather.gov)
│   └── taf_collector.py       # Collecte TAF (aviationweather.gov)
├── 📁 orchestration/        # Orchestration du workflow
│   ├── execution_manager.py       # Gestionnaire d'exécution
│   └── flight_orchestrator.py     # Orchestrateur principal
├── 📁 utils/                # Utilitaires et gestionnaires
│   ├── mongodb_manager.py          # Gestionnaire MongoDB
│   ├── postgresql_manager.py      # Gestionnaire PostgreSQL
│   ├── airport_timezone_provider.py # Gestion fuseaux horaires
│   ├── flight_html_parser.py      # Parser HTML des vols
│   └── airports_ref.csv           # Correspondance IATA/ICAO
├── main.py                  # Point d'entrée principal
├── quick_reset.py          # Reset rapide des bases de données
└── reset_environment.py   # Reset complet avec confirmation
```

## 🔄 Workflow des 7 Étapes

Le système exécute un workflow en 7 étapes avec un **Session ID global** pour lier toutes les données :

### **ÉTAPE 1 : Collecte Vols Temps Réel** 🛫
- **Source** : airportinfo.live
- **Données** : Vols de départ des 200 plus grands aéroports
- **Période** : Prochaine heure (configurable via `hour_offset`)
- **Stockage** : MongoDB collection `flights`

### **ÉTAPE 2 : Collecte Données Météo** 🌤️
- **Sources** : aviationweather.gov
- **METAR** : Observations météo actuelles
- **TAF** : Prévisions météo (Terminal Aerodrome Forecast)
- **Stockage** : MongoDB collections `metar` et `taf`

### **ÉTAPE 3 : Collecte Vols Passés** 🛬
- **Source** : airportinfo.live
- **Données** : Vols réels avec heures d'arrivée/départ effectives
- **Période** : 20 heures dans le passé (configurable via `past_hour_offset`)
- **Liaison** : Même Session ID que l'étape 1

### **ÉTAPE 4 : Association Vols-METAR** 🔗
- **Action** : Associe chaque vol avec les données METAR de l'aéroport de départ
- **Correspondance** : IATA → ICAO via `airports_ref.csv`
- **Résultat** : Ajout du champ `metar_id` aux vols

### **ÉTAPE 5 : Association Vols-TAF** 🔗
- **Action** : Associe chaque vol avec les prévisions TAF de l'aéroport d'arrivée
- **Logique** : Matching intelligent basé sur l'heure d'arrivée prévue
- **Priorité** : FM > BECMG > TEMPO > PROB
- **Résultat** : Ajout du champ `taf_id` aux vols

### **ÉTAPE 6 : Insertion PostgreSQL** 💾
- **Condition** : Vols avec METAR ET TAF associés
- **Tables** : `flight`, `metar`, `taf`
- **Données** : Insertion des données structurées pour l'analyse

### **ÉTAPE 7 : Mise à jour PostgreSQL** 🔄
- **Source** : Données des vols passés (étape 3)
- **Action** : Mise à jour avec heures réelles vs prévues
- **Objectif** : Données complètes pour modélisation des retards

## ⚙️ Configuration

### **Fichier Principal : `main.py`**
```python
def create_my_config() -> CollectionConfig:
    return CollectionConfig(
        # Base de données
        mongodb_uri="mongodb://localhost:27017/",
        database_name="dst_airlines_test",
        
        # PostgreSQL  
        postgresql_uri="postgresql://user:pass@localhost:5433/dst",
        enable_postgresql_insertion=True,
        
        # Collecte
        num_airports=200,           # Nombre d'aéroports à traiter
        delay=1.5,                  # Délai entre requêtes (secondes)
        hour_offset=1,              # Vols temps réel : +1h
        past_hour_offset=-20,       # Vols passés : -20h
        
        # Comportement
        run_once=True,              # True = une fois, False = boucle
        collect_realtime=True,      # Collecte vols temps réel
        collect_past=False,         # Collecte vols passés
        enable_weather=True,    # Collecte météo
        
        # Scheduling (mode boucle)
        schedule_minute=5,          # Exécution à XX:05
        loop_interval_minutes=60    # Toutes les 60 minutes
    )
```

### **Paramètres Avancés**
```python
# Performance
batch_size=500                  # Taille des lots pour MongoDB
log_level="INFO"               # DEBUG, INFO, WARNING, ERROR

# Métadonnées
source="airportinfo.live"
script_version="2.0"
```

## 🗃️ Modèles de Données

### **Document Vol (MongoDB)**
```json
{
  "_id": "LH441_FRA_JFK_20250904_1430",
  "flight_number": "LH441",
  "from_code": "FRA",
  "to_code": "JFK",
  "departure": {
    "scheduled_utc": "2025-09-04T14:30:00Z",
    "actual_utc": "2025-09-04T14:35:00Z"
  },
  "arrival": {
    "scheduled_utc": "2025-09-04T18:45:00Z", 
    "actual_utc": "2025-09-04T18:50:00Z"
  },
  "metar_id": "ObjectId(...)",    # Ajouté étape 4
  "taf_id": "ObjectId(...)",      # Ajouté étape 5
  "_metadata": {
    "collection_type": "realtime_departures",
    "collection_session_id": "20250904_143022_123",
    "collected_at": "2025-09-04T14:30:22Z",
    "is_updated": false,
    "update_count": 0,
    "metar_associated": true,
    "taf_associated": true
  }
}
```

### **Document METAR (MongoDB)**
```json
{
  "_id": "ObjectId(...)",
  "station_id": "EDDF",
  "observation_time": "2025-09-04T14:20:00Z",
  "raw_text": "METAR EDDF 041420Z 27008KT 9999 FEW035 SCT250 19/06 Q1015",
  "temperature_c": 19,
  "wind_speed_kt": 8,
  "visibility_m": 9999
}
```

## 🔧 Classes Principales

### **ExecutionManager**
- **Rôle** : Point d'entrée, gestion des modes d'exécution
- **Méthodes clés** :
  - `run()` : Décide entre exécution unique ou boucle
  - `_run_single()` : Une collecte complète
  - `_run_loop()` : Collectes programmées
  - `_execute_complete_workflow()` : Orchestration des 7 étapes

### **FlightOrchestrator** 
- **Rôle** : Orchestrateur principal, coordination des étapes
- **Responsabilités** :
  - Collecte et stockage des différents types de données
  - Association des données météo aux vols
  - Insertion dans PostgreSQL
- **Méthodes clés** : Une méthode par étape du workflow

### **MongoDBManager**
- **Rôle** : Abstraction MongoDB avec gestion de connexions
- **Fonctionnalités** :
  - Connexion/déconnexion automatique
  - Insertion par lots avec gestion d'erreurs
  - Création d'index optimisés

### **Collecteurs de Données**
- **FlightDataScraper** : Scraping des vols via airportinfo.live
- **MetarCollector** : API METAR aviationweather.gov  
- **TafCollector** : API TAF aviationweather.gov

## 🚀 Utilisation

### **Démarrage Simple**
    - Installer MongoDb et PostgreSQL en local

```bash
# Installation
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Exécution
python main.py
```

### **Reset des Données**
```bash
# Reset rapide (sans confirmation)
python quick_reset.py

# Reset complet (avec confirmation)
python reset_environment.py
```

### **Modes d'Exécution**

#### **Mode Une Fois (Défaut)**
```python
# Dans main.py
run_once=True
collect_realtime=True
collect_past=False      # Optionnel
```
**Résultat** : Une collecte complète puis arrêt

#### **Mode Boucle**
```python
# Dans main.py  
run_once=False
schedule_minute=5       # XX:05
loop_interval_minutes=60
```
**Résultat** : Collecte toutes les heures à XX:05

#### **Collecte Vols Passés**
```python
collect_past=True       # Active l'étape 3
```
**Important** : Nécessite une session de vols temps réel d'abord

## 📊 Session Management

### **Concept du Session ID Global**
Chaque exécution génère un Session ID unique : `YYYYMMDD_HHMMSS_mmm`

**Exemple** : `20250904_143022_123`

### **Liaison des Données**
- **Étape 1** : Génère le Session ID global
- **Étapes 2-7** : Utilisent le même Session ID
- **Avantage** : Traçabilité complète d'une collecte

### **Requêtes par Session**
```javascript
// MongoDB - Tous les vols d'une session
db.flights.find({"_metadata.collection_session_id": "20250904_143022_123"})

// PostgreSQL - Vols avec associations complètes
SELECT * FROM flight WHERE session_id = '20250904_143022_123';
```

## 🔍 Monitoring et Logs

### **Structure des Logs**
```
2025-09-04 14:30:22 | INFO | orchestration.execution_manager | Session ID global: 20250904_143022_123
2025-09-04 14:30:25 | INFO | orchestration.flight_orchestrator | ✓ 1250 vols temps réel collectés
2025-09-04 14:30:35 | INFO | utils.mongodb_manager | Total inserted: 1250/1250 vols
```

### **Métriques Importantes**
- **Taux de succès** par étape
- **Nombre de vols collectés** par session
- **Taux d'association** METAR/TAF
- **Performance** (temps d'exécution par étape)

## 🐛 Dépannage Courant

### **Erreur de Connexion MongoDB**
```bash
# Vérifier MongoDB
mongosh --host localhost:27017
```

### **Erreur de Connexion PostgreSQL**
```python
# Vérifier la chaîne de connexion dans main.py
postgresql_uri="postgresql://user:password@host:port/database"
```

### **Pas de Vols Collectés**
- Vérifier la connectivité internet
- Vérifier `hour_offset` (peut-être aucun vol à cette heure)
- Vérifier les logs pour erreurs de parsing HTML

### **Échec des Associations METAR/TAF**
- Vérifier `airports_ref.csv` pour correspondances IATA/ICAO
- Vérifier que les données météo ont bien été collectées
- Problème de fuseau horaire possible

## 📈 Optimisations

### **Performance**
- `batch_size=500` : Équilibre entre mémoire et réseau
- `delay=1.5` : Évite la limitation de taux de l'API
- Index MongoDB optimisés automatiquement

### **Fiabilité**
- Retry automatique sur erreurs réseau
- Gestion des doublons avec upsert
- Déconnexion propre des bases de données
- Logs détaillés pour debugging

## 🔮 Extensions Possibles

### **Nouvelles Sources de Données**
- APIs d'autres sites de vols
- Données de trafic aérien en temps réel
- Conditions météorologiques détaillées

### **Analyse et ML**
- Modèles de prédiction de retards
- Analyse des patterns de trafic
- Corrélation météo-retards

### **Interface Utilisateur**
- Dashboard temps réel
- API REST pour consultation
- Alertes automatiques

---

## 👥 Contribution

Pour contribuer au projet :

1. **Comprendre** le workflow des 7 étapes
2. **Respecter** l'architecture modulaire existante
3. **Tester** avec `quick_reset.py` entre les modifications
4. **Logger** abondamment pour le debugging
5. **Documenter** les nouvelles fonctionnalités

---

## 📞 Support

En cas de problème :
1. Consulter les logs dans `logs/application.log`
2. Vérifier la configuration dans `main.py`
3. Tester avec une configuration minimale d'abord
4. Utiliser `quick_reset.py` pour repartir à zéro

**Version** : 2.0  
**Dernière mise à jour** : Septembre 2025


cd C:\01_dev_clb\python\projet-avril25_cde_airlines - 2
.venv\Scripts\activate.bat
python main.py
