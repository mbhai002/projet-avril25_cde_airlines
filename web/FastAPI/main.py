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

app = FastAPI(
    title="DST Airlines API",
    description="API prevision retards vols",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connexion via DSN pour eviter les problemes d'encodage sur Windows
# Utilise la variable d'environnement ou localhost par défaut
import os
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DSN = f"host={DB_HOST} port=5432 dbname=airlines_db user=postgres password=postgres"

# Pool de connexions: maintient 1-10 connexions reutilisables pour eviter de creer/fermer
# une nouvelle connexion a chaque requete, ce qui accelere considerablement l'API
connection_pool = psycopg2.pool.SimpleConnectionPool(1, 10, DSN)

def get_db_connection():
    """Recupere une connexion du pool"""
    return connection_pool.getconn()

def return_db_connection(conn):
    """Retourne la connexion au pool pour reutilisation"""
    connection_pool.putconn(conn)

@atexit.register
def close_pool():
    """Ferme le pool de connexions a la sortie de l'application"""
    if connection_pool:
        connection_pool.closeall()

def init_db_indexes():
    """Cree les index sur les colonnes les plus utilisees pour accelerer les requetes"""
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
    """Execute une requete SQL et retourne tous les resultats"""
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
    limit: int = None
):
    """Recherche de vols avec filtres optionnels sur numero, dates et limite de resultats"""
    where_clauses = ["departure_scheduled_utc IS NOT NULL"]
    
    if flight_number:
        where_clauses.append(f"flight_number ILIKE '%{flight_number}%'")
    if departure_date:
        where_clauses.append(f"DATE(departure_scheduled_utc) = '{departure_date}'")
    if date_start:
        where_clauses.append(f"DATE(departure_scheduled_utc) >= '{date_start}'")
    if date_end:
        where_clauses.append(f"DATE(departure_scheduled_utc) <= '{date_end}'")
    
    where_sql = " AND ".join(where_clauses)
    limit_clause = f"LIMIT {limit}" if limit is not None else ""
    
    query = f"""
    SELECT 
        flight_number,
        from_airport,
        to_airport,
        airline_code,
        departure_scheduled_utc::text as departure_scheduled_utc,
        arrival_scheduled_utc::text as arrival_scheduled_utc,
        arrival_actual_utc::text as arrival_actual_utc,
        delay_min,
        delay_prob,
        delay_risk_level,
        CASE 
            WHEN delay_prob > 0.5 THEN 'OUI'
            WHEN delay_prob IS NOT NULL THEN 'NON'
            ELSE 'N/A'
        END as prediction_retard
    FROM flight
    WHERE {where_sql}
    ORDER BY departure_scheduled_utc DESC
    {limit_clause}
    """
    
    return execute_query(query)

@app.get("/stats", response_model=FlightStats)
def get_flight_stats(delay_threshold: int = 10):
    """Statistiques globales des vols avec taux de retard et precision ML"""
    query = f"""
        SELECT 
            COUNT(*) as total_flights,
            SUM(CASE WHEN delay_min >= {delay_threshold} THEN 1 ELSE 0 END) as delayed_flights,
            ROUND(AVG(CASE WHEN delay_min >= {delay_threshold} THEN 1.0 ELSE 0.0 END) * 100, 2) as delay_rate,
            ROUND(AVG(CASE WHEN delay_min >= {delay_threshold} THEN delay_min ELSE NULL END), 2) as avg_delay,
            COUNT(CASE WHEN delay_prob IS NOT NULL THEN 1 END) as flights_with_ml,
            ROUND(
                AVG(CASE 
                    WHEN delay_prob IS NOT NULL THEN 
                        CASE WHEN (delay_prob > 0.5 AND delay_min >= {delay_threshold}) OR 
                                  (delay_prob <= 0.5 AND delay_min < {delay_threshold}) 
                        THEN 1.0 ELSE 0.0 END 
                END) * 100, 2
            ) as ml_accuracy,
            MIN(departure_scheduled_utc::date) as date_min,
            MAX(departure_scheduled_utc::date) as date_max
        FROM flight
    """
    return execute_query_one(query)

@app.get("/stats/daily", response_model=List[DailyStats])
def get_daily_stats(delay_threshold: int = 10):
    """Statistiques journalieres pour suivre l'evolution des retards dans le temps"""
    query = f"""
        SELECT 
            departure_scheduled_utc::date as date,
            COUNT(*) as total,
            SUM(CASE WHEN delay_min >= {delay_threshold} THEN 1 ELSE 0 END) as delayed,
            ROUND(AVG(CASE WHEN delay_min >= {delay_threshold} THEN 1.0 ELSE 0.0 END) * 100, 2) as delay_rate
        FROM flight
        GROUP BY departure_scheduled_utc::date
        ORDER BY date
    """
    return execute_query(query)

@app.get("/stats/hourly", response_model=List[HourlyStats])
def get_hourly_stats(delay_threshold: int = 10):
    """Statistiques par heure de depart pour identifier les heures a risque"""
    query = f"""
        SELECT 
            EXTRACT(HOUR FROM departure_scheduled_utc)::int as hour,
            COUNT(*)::int as flights,
            ROUND(AVG(CASE WHEN delay_min >= {delay_threshold} THEN 1.0 ELSE 0.0 END) * 100, 2) as delay_rate
        FROM flight
        GROUP BY hour
        ORDER BY hour
    """
    return execute_query(query)

@app.get("/stats/airlines", response_model=List[AirlineStats])
def get_airline_stats(delay_threshold: int = 10, top: int = 15):
    """Statistiques par compagnie aerienne classees par taux de retard"""
    query = f"""
        WITH ranked_airlines AS (
            SELECT 
                airline_code as airline,
                COUNT(*)::int as flights,
                ROUND(AVG(CASE WHEN delay_min >= {delay_threshold} THEN 1.0 ELSE 0.0 END) * 100, 2) as delay_rate
            FROM flight
            WHERE airline_code IS NOT NULL
            GROUP BY airline_code
            ORDER BY flights DESC
            LIMIT {top}
        )
        SELECT * FROM ranked_airlines ORDER BY delay_rate
    """
    return execute_query(query)

@app.get("/ml/confusion", response_model=MLConfusion)
def get_ml_confusion(delay_threshold: int = 10):
    """Matrice de confusion du modele ML avec vrais/faux positifs et negatifs"""
    query = f"""
        SELECT 
            SUM(CASE WHEN delay_prob > 0.5 AND delay_min >= {delay_threshold} THEN 1 ELSE 0 END)::int as tp,
            SUM(CASE WHEN delay_prob <= 0.5 AND delay_min < {delay_threshold} THEN 1 ELSE 0 END)::int as tn,
            SUM(CASE WHEN delay_prob > 0.5 AND delay_min < {delay_threshold} THEN 1 ELSE 0 END)::int as fp,
            SUM(CASE WHEN delay_prob <= 0.5 AND delay_min >= {delay_threshold} THEN 1 ELSE 0 END)::int as fn
        FROM flight
        WHERE delay_prob IS NOT NULL
    """
    
    result = execute_query_one(query)
    total = result['tp'] + result['tn'] + result['fp'] + result['fn']
    accuracy = ((result['tp'] + result['tn']) / total * 100) if total > 0 else 0
    result['accuracy'] = round(accuracy, 2)
    
    return result

@app.get("/ml/risk-distribution", response_model=List[RiskDistribution])
def get_risk_distribution():
    """Distribution des vols par niveau de risque de retard (low/medium/high)"""
    query = """
        SELECT 
            delay_risk_level,
            COUNT(*)::int as count
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
    return execute_query(query)

@app.get("/meteo/stats", response_model=MeteoStats)
def get_meteo_stats():
    """Statistiques sur les donnees meteo METAR et TAF collectees"""
    query = """
        SELECT 
            (SELECT COUNT(*)::int FROM metar) as total_metar,
            (SELECT COUNT(*)::int FROM taf) as total_taf,
            (SELECT COUNT(*)::int FROM sky_condition) as total_sky_conditions,
            (SELECT COUNT(DISTINCT station_id)::int FROM metar) as airports_metar,
            (SELECT COUNT(DISTINCT station_id)::int FROM taf) as airports_taf,
            (SELECT MIN(observation_time)::date FROM metar) as date_min_metar,
            (SELECT MAX(observation_time)::date FROM metar) as date_max_metar,
            (SELECT MIN(issue_time)::date FROM taf) as date_min_taf,
            (SELECT MAX(issue_time)::date FROM taf) as date_max_taf
    """
    return execute_query_one(query)

@app.get("/meteo/flight-categories", response_model=List[MeteoCondition])
def get_flight_categories():
    """Distribution des categories de vol selon les conditions meteo (VFR/IFR/MVFR/LIFR)"""
    query = """
        SELECT 
            COALESCE(flight_category, 'UNKNOWN') as condition,
            COUNT(*)::int as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
        FROM metar
        WHERE flight_category IS NOT NULL
        GROUP BY flight_category
        ORDER BY count DESC
    """
    return execute_query(query)

@app.get("/meteo/weather-conditions", response_model=List[MeteoCondition])
def get_weather_conditions():
    """Top 20 des conditions meteorologiques observees (pluie/neige/brouillard/etc)"""
    query = """
        SELECT 
            COALESCE(wx_string, 'CLEAR') as condition,
            COUNT(*)::int as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
        FROM metar
        WHERE wx_string IS NOT NULL OR wx_string = ''
        GROUP BY wx_string
        ORDER BY count DESC
        LIMIT 20
    """
    return execute_query(query)

@app.get("/meteo/top-airports")
def get_top_airports(limit: int = 20):
    """Top aeroports avec moyennes meteo (temperature/vent/visibilite)"""
    query = f"""
        SELECT 
            station_id as airport,
            COUNT(*)::int as observations,
            ROUND(AVG(temp_c)::numeric, 2) as avg_temp,
            ROUND(AVG(wind_speed_kt)::numeric, 2) as avg_wind_speed,
            ROUND(AVG(visibility_statute_mi)::numeric, 2) as avg_visibility
        FROM metar
        WHERE temp_c IS NOT NULL
        GROUP BY station_id
        ORDER BY observations DESC
        LIMIT {limit}
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
