"""
DST Airlines API - Prevision des retards de vols

API REST pour consulter les donnees de vols, les predictions ML et les statistiques meteo.

Base de donnees:
- flight: vols avec predictions ML
- metar: observations meteo
- taf: previsions meteo
- sky_condition: conditions du ciel

Endpoints:
- /search-flights: recherche de vols avec filtres
- /stats: statistiques globales
- /stats/daily: evolution par jour
- /stats/hourly: analyse par heure
- /stats/airlines: classement compagnies
- /ml/confusion: matrice de confusion
- /ml/risk-distribution: repartition par risque
- /meteo/*: donnees meteorologiques
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2 import pool
import psycopg2.extras
from typing import List
from pydantic import BaseModel
from datetime import date
from decimal import Decimal
import atexit
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(
    title="DST Airlines API",
    description="API prevision retards vols avec Machine Learning",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Instrumentation Prometheus 
Instrumentator().instrument(app).expose(app)

# Connexion via DSN pour eviter les problemes d'encodage sur Windows
# Utilise la variable d'environnement ou localhost par défaut
import os
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DSN = f"host={DB_HOST} port=5432 dbname=airlines_db user=postgres password=postgres"

# Pool de connexions: maintient 1-10 connexions reutilisables pour eviter de creer/fermer
# une nouvelle connexion a chaque requete, ce qui accelere considerablement l'API
connection_pool = psycopg2.pool.SimpleConnectionPool(1, 10, DSN)

def get_db_connection():
    return connection_pool.getconn()

def return_db_connection(conn):
    connection_pool.putconn(conn)

@atexit.register
def close_pool():
    if connection_pool:
        connection_pool.closeall()

def init_db_indexes():
    """
    Cree les index sur les colonnes importantes pour accelerer les requetes
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_flight_departure_scheduled ON flight(departure_scheduled_utc)",
            "CREATE INDEX IF NOT EXISTS idx_flight_number ON flight(flight_number)",
            "CREATE INDEX IF NOT EXISTS idx_flight_ml ON flight(delay_prob, delay_risk_level) WHERE delay_prob IS NOT NULL",
            "CREATE INDEX IF NOT EXISTS idx_flight_airline ON flight(airline_code)",
            "CREATE INDEX IF NOT EXISTS idx_metar_station ON metar(station_id)",
            "CREATE INDEX IF NOT EXISTS idx_taf_station ON taf(station_id)"
        ]
        for idx_query in indexes:
            cur.execute(idx_query)
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"Erreur creation index: {e}")
    finally:
        return_db_connection(conn)

def clean_value(value):
    """Convertit les Decimal en float pour la serialisation JSON"""
    if isinstance(value, Decimal):
        return float(value)
    return value

def execute_query(query):
    """Execute une requete SQL et retourne les resultats"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query)
        results = [{k: clean_value(v) for k, v in dict(row).items()} for row in cur.fetchall()]
        cur.close()
        return results
    finally:
        return_db_connection(conn)

def execute_query_one(query):
    """Execute une requete SQL et retourne un seul resultat"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query)
        result = cur.fetchone()
        cur.close()
        return result
    finally:
        return_db_connection(conn)

class FlightStats(BaseModel):
    total_flights: int
    delayed_flights: int
    delay_rate: float
    avg_delay: float
    flights_with_ml: int
    ml_accuracy: float
    date_min: date
    date_max: date

class DailyStats(BaseModel):
    date: date
    total: int
    delayed: int
    delay_rate: float

class HourlyStats(BaseModel):
    hour: int
    flights: int
    delay_rate: float

class AirlineStats(BaseModel):
    airline: str
    airline_name: str = None
    flights: int
    delay_rate: float

class MLConfusion(BaseModel):
    tp: int
    tn: int
    fp: int
    fn: int
    accuracy: float

class RiskDistribution(BaseModel):
    delay_risk_level: str
    count: int

class MLReliability(BaseModel):
    risk_level: str
    total_vols: int
    vrais_retards: int
    vols_a_l_heure: int
    taux_retard_reel: float

class MeteoStats(BaseModel):
    total_metar: int
    total_taf: int
    total_sky_conditions: int
    airports_metar: int
    airports_taf: int
    date_min_metar: date
    date_max_metar: date
    date_min_taf: date
    date_max_taf: date

class MeteoCondition(BaseModel):
    condition: str
    count: int
    percentage: float

@app.get("/")
def root():
    """Point d'entree de l'API"""
    return {"message": "DST Airlines API", "version": "1.0.0"}

@app.get("/search-flights")
def search_flights(
    flight_number: str = None,
    departure_date: str = None,
    date_start: str = None,
    date_end: str = None,
    airline_code: str = None,
    risk_levels: str = None,
    delayed_only: bool = None,
    predicted_delay_only: bool = None,
    has_ml_prediction: bool = None,
    delay_min_threshold: int = 10,
    limit: int = None
):  
    """
    Recherche de vols avec filtres multiples
    """
    where_clauses = ["departure_scheduled_utc IS NOT NULL"]
    
    if flight_number:
        where_clauses.append(f"flight_number ILIKE '%{flight_number}%'")
    if departure_date:
        where_clauses.append(f"departure_scheduled_utc::date = '{departure_date}'::date")
    if date_start:
        where_clauses.append(f"departure_scheduled_utc >= '{date_start}'::timestamp")
    if date_end:
        where_clauses.append(f"departure_scheduled_utc <= '{date_end}'::timestamp + interval '1 day'")
    if airline_code:
        where_clauses.append(f"airline_code = '{airline_code}'")
    
    if risk_levels:
        levels = [f"'{level.strip().lower()}'" for level in risk_levels.split(',')]
        where_clauses.append(f"delay_risk_level IN ({','.join(levels)})")
    
    if delayed_only:
        where_clauses.append(f"delay_min >= {delay_min_threshold}")
    
    if predicted_delay_only:
        where_clauses.append("delay_prob > 0.5")
    
    if has_ml_prediction:
        where_clauses.append("delay_prob IS NOT NULL")
    
    where_sql = " AND ".join(where_clauses)
    limit_clause = f"LIMIT {limit}" if limit is not None else "LIMIT 10000"
    
    query = f"""
    SELECT 
        f.flight_number,
        f.from_airport,
        da_from.city as from_city,
        da_from.airport_name as from_airport_name,
        f.to_airport,
        da_to.city as to_city,
        da_to.airport_name as to_airport_name,
        f.airline_code,
        da.name as airline_name,
        to_char(f.departure_scheduled_utc, 'YYYY-MM-DD HH24:MI:SS') as departure_scheduled_utc,
        to_char(f.arrival_scheduled_utc, 'YYYY-MM-DD HH24:MI:SS') as arrival_scheduled_utc,
        to_char(f.arrival_actual_utc, 'YYYY-MM-DD HH24:MI:SS') as arrival_actual_utc,
        COALESCE(
            f.delay_min,
            CASE 
                WHEN f.arrival_actual_utc IS NOT NULL AND f.arrival_scheduled_utc IS NOT NULL 
                THEN EXTRACT(EPOCH FROM (f.arrival_actual_utc - f.arrival_scheduled_utc))/60
                ELSE NULL
            END
        ) as delay_min,
        f.delay_prob,
        f.delay_risk_level,
        m.visibility_statute_mi as dep_visibility_mi,
        m.flight_category as dep_flight_category,
        m.temp_c as dep_temp_c,
        m.wind_speed_kt as dep_wind_speed_kt,
        m.wx_string as dep_weather_conditions
    FROM flight f
    LEFT JOIN metar m ON f.departure_metar_fk = m.id
    LEFT JOIN dim_airports da_from ON f.from_airport = da_from.iata_code
    LEFT JOIN dim_airports da_to ON f.to_airport = da_to.iata_code
    LEFT JOIN dim_airlines da ON f.airline_code = da.iata
    WHERE {where_sql}
    ORDER BY f.departure_scheduled_utc DESC
    {limit_clause}
    """
    
    return execute_query(query)

@app.get("/filter-options")
def get_filter_options():
    """Retourne les options de filtres disponibles"""
    query_airlines = """
        SELECT DISTINCT airline_code 
        FROM flight 
        WHERE airline_code IS NOT NULL 
        ORDER BY airline_code
    """
    
    query_risk_levels = """
        SELECT DISTINCT delay_risk_level, COUNT(*) as count
        FROM flight 
        WHERE delay_risk_level IS NOT NULL 
        GROUP BY delay_risk_level
        ORDER BY 
            CASE delay_risk_level
                WHEN 'low' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'high' THEN 3
            END
    """
    
    airlines = execute_query(query_airlines)
    risk_levels = execute_query(query_risk_levels)
    
    return {
        "airlines": [a['airline_code'] for a in airlines],
        "risk_levels": [
            {"value": r['delay_risk_level'], "count": r['count']} 
            for r in risk_levels
        ],
        "delay_thresholds": [5, 10, 15, 20, 30, 45, 60]
    }

@app.get("/stats", response_model=FlightStats)
def get_flight_stats(delay_threshold: int = 10, date_start: str = None, date_end: str = None):
    """Statistiques globales des vols"""
    where_clause = "WHERE 1=1"
    if date_start:
        where_clause += f" AND departure_scheduled_utc::date >= '{date_start}'::date"
    if date_end:
        where_clause += f" AND departure_scheduled_utc::date <= '{date_end}'::date"
    
    query = f"""
        SELECT 
            COUNT(*) as total_flights,
            SUM(CASE WHEN delay_min >= {delay_threshold} THEN 1 ELSE 0 END) as delayed_flights,
            ROUND(AVG(CASE WHEN delay_min >= {delay_threshold} THEN 1.0 ELSE 0.0 END) * 100, 2) as delay_rate,
            COALESCE(ROUND(AVG(CASE WHEN delay_min >= {delay_threshold} THEN delay_min ELSE NULL END), 2), 0) as avg_delay,
            COUNT(CASE WHEN delay_prob IS NOT NULL THEN 1 END) as flights_with_ml,
            COALESCE(ROUND(
                AVG(CASE 
                    WHEN delay_prob IS NOT NULL THEN 
                        CASE WHEN (delay_prob > 0.5 AND delay_min >= {delay_threshold}) OR 
                                  (delay_prob <= 0.5 AND delay_min < {delay_threshold}) 
                        THEN 1.0 ELSE 0.0 END 
                END) * 100, 2
            ), 0) as ml_accuracy,
            MIN(departure_scheduled_utc::date) as date_min,
            MAX(departure_scheduled_utc::date) as date_max
        FROM flight
        {where_clause}
    """
    return execute_query_one(query)

@app.get("/stats/daily", response_model=List[DailyStats])
def get_daily_stats(delay_threshold: int = 10, date_start: str = None, date_end: str = None):
    """
    Statistiques par jour
    """
    where_clause = "WHERE 1=1"
    if date_start:
        where_clause += f" AND departure_scheduled_utc::date >= '{date_start}'::date"
    if date_end:
        where_clause += f" AND departure_scheduled_utc::date <= '{date_end}'::date"
    
    query = f"""
        SELECT 
            departure_scheduled_utc::date as date,
            COUNT(*) as total,
            SUM(CASE WHEN delay_min >= {delay_threshold} THEN 1 ELSE 0 END) as delayed,
            ROUND(AVG(CASE WHEN delay_min >= {delay_threshold} THEN 1.0 ELSE 0.0 END) * 100, 2) as delay_rate
        FROM flight
        {where_clause}
        GROUP BY departure_scheduled_utc::date
        ORDER BY date
    """
    return execute_query(query)

@app.get("/stats/hourly", response_model=List[HourlyStats])
def get_hourly_stats(delay_threshold: int = 10, date_start: str = None, date_end: str = None):
    """Statistiques par heure de depart"""
    where_clause = "WHERE 1=1"
    if date_start:
        where_clause += f" AND departure_scheduled_utc::date >= '{date_start}'::date"
    if date_end:
        where_clause += f" AND departure_scheduled_utc::date <= '{date_end}'::date"
    
    query = f"""
        SELECT 
            EXTRACT(HOUR FROM departure_scheduled_utc)::int as hour,
            COUNT(*)::int as flights,
            ROUND(AVG(CASE WHEN delay_min >= {delay_threshold} THEN 1.0 ELSE 0.0 END) * 100, 2) as delay_rate
        FROM flight
        {where_clause}
        GROUP BY hour
        ORDER BY hour
    """
    return execute_query(query)

@app.get("/stats/airlines", response_model=List[AirlineStats])
def get_airline_stats(delay_threshold: int = 10, top: int = 15, date_start: str = None, date_end: str = None):
    where_clause = "WHERE airline_code IS NOT NULL"
    if date_start:
        where_clause += f" AND departure_scheduled_utc::date >= '{date_start}'::date"
    if date_end:
        where_clause += f" AND departure_scheduled_utc::date <= '{date_end}'::date"
    
    query = f"""
        WITH ranked_airlines AS (
            SELECT 
                airline_code as airline,
                COUNT(*)::int as flights,
                ROUND(AVG(CASE WHEN delay_min >= {delay_threshold} THEN 1.0 ELSE 0.0 END) * 100, 2) as delay_rate
            FROM flight
            {where_clause}
            GROUP BY airline_code
            ORDER BY flights DESC
            LIMIT {top}
        )
        SELECT 
            ra.airline,
            da.name as airline_name,
            ra.flights,
            ra.delay_rate 
        FROM ranked_airlines ra
        LEFT JOIN dim_airlines da ON ra.airline = da.iata
        ORDER BY delay_rate
    """
    return execute_query(query)

@app.get("/ml/confusion", response_model=MLConfusion)
def get_ml_confusion(delay_threshold: int = 10, date_start: str = None, date_end: str = None):
    """Matrice de confusion du modele ML"""
    where_clause = "WHERE delay_prob IS NOT NULL"
    if date_start:
        where_clause += f" AND departure_scheduled_utc::date >= '{date_start}'::date"
    if date_end:
        where_clause += f" AND departure_scheduled_utc::date <= '{date_end}'::date"
    
    query = f"""
        SELECT 
            SUM(CASE WHEN delay_prob > 0.5 AND delay_min >= {delay_threshold} THEN 1 ELSE 0 END)::int as tp,
            SUM(CASE WHEN delay_prob <= 0.5 AND delay_min < {delay_threshold} THEN 1 ELSE 0 END)::int as tn,
            SUM(CASE WHEN delay_prob > 0.5 AND delay_min < {delay_threshold} THEN 1 ELSE 0 END)::int as fp,
            SUM(CASE WHEN delay_prob <= 0.5 AND delay_min >= {delay_threshold} THEN 1 ELSE 0 END)::int as fn
        FROM flight
        {where_clause}
    """
    
    result = execute_query_one(query)
    total = result['tp'] + result['tn'] + result['fp'] + result['fn']
    accuracy = ((result['tp'] + result['tn']) / total * 100) if total > 0 else 0
    result['accuracy'] = round(accuracy, 2)
    
    return result

@app.get("/ml/risk-distribution", response_model=List[RiskDistribution])
def get_risk_distribution(date_start: str = None, date_end: str = None):
    """Distribution des vols par niveau de risque ML"""
    where_clause = "WHERE delay_risk_level IS NOT NULL"
    if date_start:
        where_clause += f" AND departure_scheduled_utc::date >= '{date_start}'::date"
    if date_end:
        where_clause += f" AND departure_scheduled_utc::date <= '{date_end}'::date"
    
    query = f"""
        SELECT 
            delay_risk_level,
            COUNT(*)::int as count
        FROM flight
        {where_clause}
        GROUP BY delay_risk_level
        ORDER BY 
            CASE delay_risk_level
                WHEN 'low' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'high' THEN 3
            END
    """
    return execute_query(query)

@app.get("/ml/reliability", response_model=List[MLReliability])
def get_ml_reliability(delay_threshold: int = 15):
    """Analyse de fiabilite des niveaux de risque par rapport aux retards reels"""
    query = f"""
        SELECT 
            delay_risk_level as risk_level,
            COUNT(*)::int as total_vols,
            SUM(CASE WHEN delay_min >= {delay_threshold} THEN 1 ELSE 0 END)::int as vrais_retards,
            SUM(CASE WHEN delay_min < {delay_threshold} OR delay_min IS NULL THEN 1 ELSE 0 END)::int as vols_a_l_heure
        FROM flight
        WHERE delay_risk_level IS NOT NULL
        GROUP BY delay_risk_level
        ORDER BY 
            CASE delay_risk_level
                WHEN 'low' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'high' THEN 3
            END
    """
    results = execute_query(query)
    for r in results:
        r['taux_retard_reel'] = round((r['vrais_retards'] / r['total_vols'] * 100), 1) if r['total_vols'] > 0 else 0
    return results

@app.get("/meteo/stats", response_model=MeteoStats)
def get_meteo_stats(date_start: str = None, date_end: str = None, station: str = None):
    """
    Statistiques sur les donnees meteo METAR et TAF collectees
    
    
    
    
    
    """
    where_metar = "WHERE 1=1"
    where_taf = "WHERE 1=1"
    
    if station:
        where_metar += f" AND station_id = '{station}'"
        where_taf += f" AND station_id = '{station}'"
    if date_start:
        where_metar += f" AND observation_time::date >= '{date_start}'::date"
        where_taf += f" AND issue_time::date >= '{date_start}'::date"
    if date_end:
        where_metar += f" AND observation_time::date <= '{date_end}'::date"
        where_taf += f" AND issue_time::date <= '{date_end}'::date"
    
    query = f"""
        SELECT 
            (SELECT COUNT(*)::int FROM metar {where_metar}) as total_metar,
            (SELECT COUNT(*)::int FROM taf {where_taf}) as total_taf,
            (SELECT COUNT(*)::int FROM sky_condition) as total_sky_conditions,
            (SELECT COUNT(DISTINCT station_id)::int FROM metar {where_metar}) as airports_metar,
            (SELECT COUNT(DISTINCT station_id)::int FROM taf {where_taf}) as airports_taf,
            (SELECT MIN(observation_time)::date FROM metar {where_metar}) as date_min_metar,
            (SELECT MAX(observation_time)::date FROM metar {where_metar}) as date_max_metar,
            (SELECT MIN(issue_time)::date FROM taf {where_taf}) as date_min_taf,
            (SELECT MAX(issue_time)::date FROM taf {where_taf}) as date_max_taf
    """
    return execute_query_one(query)

@app.get("/meteo/flight-categories", response_model=List[MeteoCondition])
def get_flight_categories(date_start: str = None, date_end: str = None, station: str = None):
    """
    Distribution des categories de vol selon les conditions meteo (VFR/IFR/MVFR/LIFR)
    
    Filtre les observations METAR par periode.
    
    
    
    
    """
    where_clause = "WHERE flight_category IS NOT NULL"
    if station:
        where_clause += f" AND station_id = '{station}'"
    if date_start:
        where_clause += f" AND observation_time::date >= '{date_start}'::date"
    if date_end:
        where_clause += f" AND observation_time::date <= '{date_end}'::date"
    
    query = f"""
        SELECT 
            COALESCE(flight_category, 'UNKNOWN') as condition,
            COUNT(*)::int as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
        FROM metar
        {where_clause}
        GROUP BY flight_category
        ORDER BY count DESC
    """
    return execute_query(query)

@app.get("/meteo/weather-conditions", response_model=List[MeteoCondition])
def get_weather_conditions(date_start: str = None, date_end: str = None, station: str = None):
    """
    Top 20 des conditions meteorologiques observees (pluie/neige/brouillard/etc)
    
    Filtre les observations METAR par periode.
    
    
    
    
    """
    where_clause = "WHERE wx_string IS NOT NULL OR wx_string = ''"
    if station:
        where_clause += f" AND station_id = '{station}'"
    if date_start:
        where_clause += f" AND observation_time::date >= '{date_start}'::date"
    if date_end:
        where_clause += f" AND observation_time::date <= '{date_end}'::date"
    
    query = f"""
        SELECT 
            COALESCE(wx_string, 'CLEAR') as condition,
            COUNT(*)::int as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
        FROM metar
        {where_clause}
        GROUP BY wx_string
        ORDER BY count DESC
        LIMIT 20
    """
    return execute_query(query)

@app.get("/meteo/top-airports")
def get_top_airports(limit: int = 20, date_start: str = None, date_end: str = None):
    """
    Top aeroports avec moyennes meteo (temperature/vent/visibilite)
    
    Filtre les observations METAR par periode.
    
    
    
    
    """
    where_clause = "WHERE temp_c IS NOT NULL"
    if date_start:
        where_clause += f" AND observation_time::date >= '{date_start}'::date"
    if date_end:
        where_clause += f" AND observation_time::date <= '{date_end}'::date"
    
    query = f"""
        SELECT 
            station_id as airport,
            COUNT(*)::int as observations,
            ROUND(AVG(temp_c)::numeric, 2) as avg_temp,
            ROUND(AVG(wind_speed_kt)::numeric, 2) as avg_wind_speed,
            ROUND(AVG(visibility_statute_mi)::numeric, 2) as avg_visibility
        FROM metar
        {where_clause}
        GROUP BY station_id
        ORDER BY observations DESC
        LIMIT {limit}
    """
    return execute_query(query)

@app.get("/meteo/visibility-distribution")
def get_visibility_distribution(date_start: str = None, date_end: str = None, station: str = None):
    """
    Distribution des observations par plages de visibilite
    
    
    
    
    """
    where_clause = "WHERE visibility_statute_mi IS NOT NULL"
    if station:
        where_clause += f" AND station_id = '{station}'"
    if date_start:
        where_clause += f" AND observation_time::date >= '{date_start}'::date"
    if date_end:
        where_clause += f" AND observation_time::date <= '{date_end}'::date"
    
    query = f"""
        SELECT 
            CASE 
                WHEN visibility_statute_mi < 1 THEN '< 1 mi'
                WHEN visibility_statute_mi >= 1 AND visibility_statute_mi < 3 THEN '1-3 mi'
                WHEN visibility_statute_mi >= 3 AND visibility_statute_mi < 5 THEN '3-5 mi'
                WHEN visibility_statute_mi >= 5 AND visibility_statute_mi < 10 THEN '5-10 mi'
                ELSE '>= 10 mi'
            END as visibility_range,
            COUNT(*)::int as count,
            MIN(visibility_statute_mi) as min_vis
        FROM metar
        {where_clause}
        GROUP BY 
            CASE 
                WHEN visibility_statute_mi < 1 THEN '< 1 mi'
                WHEN visibility_statute_mi >= 1 AND visibility_statute_mi < 3 THEN '1-3 mi'
                WHEN visibility_statute_mi >= 3 AND visibility_statute_mi < 5 THEN '3-5 mi'
                WHEN visibility_statute_mi >= 5 AND visibility_statute_mi < 10 THEN '5-10 mi'
                ELSE '>= 10 mi'
            END
        ORDER BY min_vis
    """
    return execute_query(query)

@app.get("/meteo/visibility-timeline")
def get_visibility_timeline(date_start: str = None, date_end: str = None, station: str = None):
    """
    Evolution de la visibilite moyenne par jour
    
    
    
    
    """
    where_clause = "WHERE visibility_statute_mi IS NOT NULL"
    if station:
        where_clause += f" AND station_id = '{station}'"
    if date_start:
        where_clause += f" AND observation_time::date >= '{date_start}'::date"
    if date_end:
        where_clause += f" AND observation_time::date <= '{date_end}'::date"
    
    query = f"""
        SELECT 
            observation_time::date as date,
            ROUND(AVG(visibility_statute_mi)::numeric, 2) as avg_visibility,
            COUNT(*)::int as observations
        FROM metar
        {where_clause}
        GROUP BY observation_time::date
        ORDER BY date
    """
    return execute_query(query)

@app.get("/meteo/temperature-stats")
def get_temperature_stats(date_start: str = None, date_end: str = None, station: str = None):
    """
    Evolution temperature et point de rosee par jour
    
    
    
    
    """
    where_clause = "WHERE temp_c IS NOT NULL AND dewpoint_c IS NOT NULL"
    if station:
        where_clause += f" AND station_id = '{station}'"
    if date_start:
        where_clause += f" AND observation_time::date >= '{date_start}'::date"
    if date_end:
        where_clause += f" AND observation_time::date <= '{date_end}'::date"
    
    query = f"""
        SELECT 
            observation_time::date as date,
            ROUND(AVG(temp_c)::numeric, 2) as avg_temp,
            ROUND(AVG(dewpoint_c)::numeric, 2) as avg_dewpoint,
            COUNT(*)::int as observations
        FROM metar
        {where_clause}
        GROUP BY observation_time::date
        ORDER BY date
    """
    return execute_query(query)

@app.get("/meteo/wind-stats")
def get_wind_stats(date_start: str = None, date_end: str = None, station: str = None):
    where_clause = "WHERE wind_speed_kt IS NOT NULL"
    if station:
        where_clause += f" AND station_id = '{station}'"
    if date_start:
        where_clause += f" AND observation_time::date >= '{date_start}'::date"
    if date_end:
        where_clause += f" AND observation_time::date <= '{date_end}'::date"
    
    query = f"""
        SELECT 
            CASE 
                WHEN wind_speed_kt < 5 THEN '< 5 kt'
                WHEN wind_speed_kt >= 5 AND wind_speed_kt < 10 THEN '5-10 kt'
                WHEN wind_speed_kt >= 10 AND wind_speed_kt < 15 THEN '10-15 kt'
                WHEN wind_speed_kt >= 15 AND wind_speed_kt < 20 THEN '15-20 kt'
                WHEN wind_speed_kt >= 20 AND wind_speed_kt < 25 THEN '20-25 kt'
                ELSE '>= 25 kt'
            END as wind_range,
            COUNT(*)::int as count,
            MIN(wind_speed_kt) as min_wind
        FROM metar
        {where_clause}
        GROUP BY 
            CASE 
                WHEN wind_speed_kt < 5 THEN '< 5 kt'
                WHEN wind_speed_kt >= 5 AND wind_speed_kt < 10 THEN '5-10 kt'
                WHEN wind_speed_kt >= 10 AND wind_speed_kt < 15 THEN '10-15 kt'
                WHEN wind_speed_kt >= 15 AND wind_speed_kt < 20 THEN '15-20 kt'
                WHEN wind_speed_kt >= 20 AND wind_speed_kt < 25 THEN '20-25 kt'
                ELSE '>= 25 kt'
            END
        ORDER BY min_wind
    """
    return execute_query(query)

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*70)
    print("FASTAPI SERVER - DST AIRLINES")
    print("="*70)
    print("Initialisation index base de donnees...")
    init_db_indexes()
    print("Index crees avec succes")
    print("API: http://127.0.0.1:8000")
    print("Docs: http://127.0.0.1:8000/docs")
    print("="*70 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)
