# DST Airlines - API FastAPI

API REST pour le projet DST Airlines - Prevision des retards de vols.

## Performance

- Pool de connexions PostgreSQL (10 connexions)
- Index automatiques sur colonnes critiques
- Code optimise

## Structure

```
web/
├── FastAPI/
│   └── main.py              # API REST
├── app.py                   # Dashboard Dash
├── pages/
│   ├── vols.py             # Analyse vols
│   └── meteo.py            # Analyse meteo
└── run_app.py              # Script de lancement
```

## Endpoints

### Recherche Vols

- `GET /search-flights` - Recherche de vols avec filtres
- `GET /filter-options` - Options de filtres disponibles

### Statistiques Vols

- `GET /stats` - Statistiques globales
- `GET /stats/daily` - Stats par jour
- `GET /stats/hourly` - Stats par heure
- `GET /stats/airlines` - Stats par compagnie

### Machine Learning

- `GET /ml/confusion` - Matrice de confusion
- `GET /ml/risk-distribution` - Distribution risques

### Meteo

- `GET /meteo/stats` - Stats METAR/TAF
- `GET /meteo/flight-categories` - Categories vol (VFR/IFR/MVFR/LIFR)
- `GET /meteo/weather-conditions` - Conditions meteo
- `GET /meteo/visibility-distribution` - Distribution visibilite
- `GET /meteo/visibility-timeline` - Evolution visibilite
- `GET /meteo/temperature-stats` - Stats temperature
- `GET /meteo/wind-stats` - Stats vent

## Demarrage

### API seule

```bash
cd web/FastAPI
python main.py
```

API: http://127.0.0.1:8000
Docs: http://127.0.0.1:8000/docs

### API + Dashboard

```bash
python web/run_app.py
```

Services:

- API: http://127.0.0.1:8000
- Dashboard: http://127.0.0.1:8050

## Base de donnees

```
Host: 127.0.0.1:5432
Database: airlines_db
User: postgres
Password: postgres
```

Tables:

- flight (vols avec predictions ML)
- metar (observations meteo)
- taf (previsions meteo)
- sky_condition

## Dependances

```bash
pip install fastapi uvicorn psycopg2-binary pydantic dash plotly requests
```
