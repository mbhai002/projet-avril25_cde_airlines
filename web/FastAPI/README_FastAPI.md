# DST Airlines - API FastAPI

API REST pour le projet DST Airlines - Prevision des retards de vols.

## Architecture

```
web/
├── FastAPI/
│   ├── main.py              # API REST avec FastAPI
│   └── main_old.py          # Version avec SQLAlchemy (archive)
├── app.py                   # Application Dash principale
├── pages/                   # Pages du dashboard
│   ├── vols.py             # Analyse des vols
│   ├── meteo.py            # Analyse meteo + correlations retards
│   └── analyses.py         # Statistiques detaillees
├── run_app.py              # Script de lancement
└── Data_for_VIZ/           # Backups PostgreSQL
```

## Endpoints de l'API

### Statistiques Vols

- `GET /` - Informations sur l'API
- `GET /stats` - Statistiques globales des vols
  - Parametre: `delay_threshold` (defaut: 10 minutes)
  - Retourne: total vols, vols retardes, taux de retard, retard moyen, ML accuracy
- `GET /stats/daily` - Statistiques journalieres (evolution temporelle)
- `GET /stats/hourly` - Statistiques par heure de depart
- `GET /stats/airlines` - Statistiques par compagnie aerienne
  - Parametre: `top` (defaut: 15)

### Machine Learning

- `GET /ml/confusion` - Matrice de confusion du modele ML
  - Retourne: TP, TN, FP, FN, accuracy
- `GET /ml/risk-distribution` - Distribution des niveaux de risque
  - Niveaux: LOW, MEDIUM, HIGH

### Statistiques Meteo

- `GET /meteo/stats` - Statistiques globales METAR/TAF
- `GET /meteo/flight-categories` - Repartition des categories de vol
  - Categories: VFR, MVFR, IFR, LIFR
- `GET /meteo/weather-conditions` - Top 20 conditions meteorologiques
- `GET /meteo/top-airports` - Top aeroports avec statistiques meteo
  - Parametre: `limit` (defaut: 20)

### Correlations Meteo-Retards

- `GET /correlations/meteo-delays` - Correlations conditions meteo et retards
  - Filtre: minimum 10 vols par condition
- `GET /correlations/visibility-delays` - Impact de la visibilite sur les retards
  - Ranges: < 1 mile, 1-3 miles, 3-5 miles, 5-10 miles, >= 10 miles
- `GET /correlations/wind-delays` - Impact du vent sur les retards
  - Ranges: 0-5 kt, 5-10 kt, 10-15 kt, 15-20 kt, >= 20 kt

## Demarrage

### Option 1: Demarrer l'API seule

```bash
cd web/FastAPI
python main.py
```

API disponible sur http://127.0.0.1:8000
Documentation interactive sur http://127.0.0.1:8000/docs

### Option 2: Demarrer API + Dashboard

```bash
python web/run_app.py
```

Services demarres automatiquement:

- API FastAPI sur http://127.0.0.1:8000
- Dashboard Dash sur http://127.0.0.1:8050

Dashboard multi-pages:

- Page Vols: http://127.0.0.1:8050/
- Page Meteo: http://127.0.0.1:8050/meteo
- Page Analyses: http://127.0.0.1:8050/analyses

## Base de donnees

Connexion PostgreSQL via Docker:

```
Host: 127.0.0.1:5432
Database: airlines_db
User: postgres
Password: postgres
```

Tables utilisees:

- flight (841,745 vols avec predictions ML)
- metar (82,732 observations)
- taf (102,899 previsions)
- sky_condition (243,541 conditions)
- sky_cover_reference (9 references)

## Dependances

```bash
pip install fastapi uvicorn psycopg2-binary pydantic dash plotly requests
```

Note: Version actuelle utilise psycopg2 (bibliotheque standard du cours).
Version avec SQLAlchemy archivee dans main_old.py.

## Implementation

L'API utilise psycopg2 avec RealDictCursor pour retourner directement des dictionnaires:

```python
def execute_query(query):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(query)
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results
```

Modeles Pydantic pour validation automatique:

- FlightStats, DailyStats, HourlyStats, AirlineStats
- MLConfusion, RiskDistribution
- MeteoStats, MeteoCondition
