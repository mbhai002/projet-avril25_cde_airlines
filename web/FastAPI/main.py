from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import psycopg2.extras
from typing import List
from pydantic import BaseModel
from datetime import date

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

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 5432,
    'database': 'airlines_db',
    'user': 'postgres',
    'password': 'postgres'
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def execute_query(query):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(query)
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results

def execute_query_one(query):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(query)
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result

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
    return {"message": "DST Airlines API", "version": "1.0.0"}

@app.get("/stats", response_model=FlightStats)
def get_flight_stats(delay_threshold: int = 10):
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

@app.get("/correlations/conditions")
def get_conditions_delay_correlation(delay_threshold: int = 10, top: int = 20):
    query = f"""
        SELECT 
            m.flight_category as condition,
            COUNT(f.id)::int as total_flights,
            SUM(CASE WHEN f.delay_min >= {delay_threshold} THEN 1 ELSE 0 END)::int as delayed_flights,
            ROUND(AVG(CASE WHEN f.delay_min >= {delay_threshold} THEN 1.0 ELSE 0.0 END) * 100, 2) as delay_rate,
            ROUND(AVG(f.delay_min)::numeric, 2) as avg_delay_min
        FROM flight f
        INNER JOIN metar m ON f.departure_metar_fk = m.id
        WHERE m.flight_category IS NOT NULL
        GROUP BY m.flight_category
        HAVING COUNT(f.id) >= 10
        ORDER BY delay_rate DESC
        LIMIT {top}
    """
    return execute_query(query)

@app.get("/correlations/visibility")
@app.get("/correlations/visibility-delays")
def get_visibility_delay_correlation(delay_threshold: int = 10):
    query = f"""
        WITH visibility_ranges AS (
            SELECT 
                f.id,
                f.delay_min,
                CASE 
                    WHEN m.visibility_statute_mi < 1 THEN '< 1 mile'
                    WHEN m.visibility_statute_mi < 3 THEN '1-3 miles'
                    WHEN m.visibility_statute_mi < 5 THEN '3-5 miles'
                    WHEN m.visibility_statute_mi < 10 THEN '5-10 miles'
                    ELSE '>= 10 miles'
                END as visibility_range
            FROM flight f
            INNER JOIN metar m ON f.departure_metar_fk = m.id
            WHERE m.visibility_statute_mi IS NOT NULL
        )
        SELECT 
            visibility_range,
            COUNT(id)::int as total_flights,
            SUM(CASE WHEN delay_min >= {delay_threshold} THEN 1 ELSE 0 END)::int as delayed_flights,
            ROUND(AVG(CASE WHEN delay_min >= {delay_threshold} THEN 1.0 ELSE 0.0 END) * 100, 2) as delay_rate
        FROM visibility_ranges
        GROUP BY visibility_range
        ORDER BY 
            CASE 
                WHEN visibility_range = '< 1 mile' THEN 1
                WHEN visibility_range = '1-3 miles' THEN 2
                WHEN visibility_range = '3-5 miles' THEN 3
                WHEN visibility_range = '5-10 miles' THEN 4
                ELSE 5
            END
    """
    return execute_query(query)

@app.get("/correlations/wind")
@app.get("/correlations/wind-delays")
def get_wind_delay_correlation(delay_threshold: int = 10):
    query = f"""
        WITH wind_ranges AS (
            SELECT 
                f.id,
                f.delay_min,
                CASE 
                    WHEN m.wind_speed_kt < 5 THEN '0-5 kt'
                    WHEN m.wind_speed_kt < 10 THEN '5-10 kt'
                    WHEN m.wind_speed_kt < 15 THEN '10-15 kt'
                    WHEN m.wind_speed_kt < 20 THEN '15-20 kt'
                    ELSE '>= 20 kt'
                END as wind_range
            FROM flight f
            INNER JOIN metar m ON f.departure_metar_fk = m.id
            WHERE m.wind_speed_kt IS NOT NULL
        )
        SELECT 
            wind_range,
            COUNT(id)::int as total_flights,
            SUM(CASE WHEN delay_min >= {delay_threshold} THEN 1 ELSE 0 END)::int as delayed_flights,
            ROUND(AVG(CASE WHEN delay_min >= {delay_threshold} THEN 1.0 ELSE 0.0 END) * 100, 2) as delay_rate
        FROM wind_ranges
        GROUP BY wind_range
        ORDER BY 
            CASE 
                WHEN wind_range = '0-5 kt' THEN 1
                WHEN wind_range = '5-10 kt' THEN 2
                WHEN wind_range = '10-15 kt' THEN 3
                WHEN wind_range = '15-20 kt' THEN 4
                ELSE 5
            END
    """
    return execute_query(query)

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*70)
    print("FASTAPI SERVER - DST AIRLINES")
    print("="*70)
    print("API: http://127.0.0.1:8000")
    print("Docs: http://127.0.0.1:8000/docs")
    print("="*70 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)
