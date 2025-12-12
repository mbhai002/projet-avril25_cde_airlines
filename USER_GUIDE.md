# DST Airlines - User Guide
## Flight Delay Prediction System

---

## Table of Contents
1. [System Overview](#system-overview)
2. [Accessing the Application](#accessing-the-application)
3. [Dashboard Guide](#dashboard-guide)
4. [API Documentation](#api-documentation)
5. [Database Management](#database-management)
6. [Data Collection Process](#data-collection-process)
7. [Machine Learning Predictions](#machine-learning-predictions)
8. [Common Tasks](#common-tasks)
9. [Frequently Asked Questions](#frequently-asked-questions)

---

## System Overview

### What is DST Airlines?

DST Airlines is a comprehensive flight delay prediction system that:
- **Collects** real-time flight data from 200+ airports worldwide
- **Gathers** weather information (METAR/TAF) for each airport
- **Predicts** flight delays using machine learning models
- **Visualizes** flight statistics and analytics through interactive dashboards
- **Provides** RESTful API access to all data

### Architecture Components

| Component | Purpose | Access URL |
|-----------|---------|------------|
| **Flight Collector** | Automated data collection service | Background service (no UI) |
| **PostgreSQL** | Main relational database | Port 5432 (database clients) |
| **MongoDB** | NoSQL database for raw data | Port 27017 (database clients) |
| **FastAPI** | REST API for data access | http://35.181.7.121:8000 |
| **Dash Dashboard** | Interactive web visualization | http://35.181.7.121:8050 |
| **pgAdmin** | Database management interface | http://35.181.7.121:5050 |

### System Capabilities

**Data Collection:**
- 200 airports monitored continuously
- Real-time flight information
- Historical flight data (past 20 hours)
- Weather conditions (METAR/TAF)
- Automated hourly updates

**Machine Learning:**
- XGBoost-based delay prediction model
- Risk categorization (low/medium/high)
- Probability scores for each flight
- Feature importance analysis

**Analytics:**
- Daily delay statistics
- Hourly delay patterns
- Airline performance comparison
- Weather impact analysis
- ML model accuracy metrics

---

## Accessing the Application

### Service URLs

**All services are accessible via the public IP: 35.181.7.121**

#### 1. Interactive Dashboard (Primary User Interface)
```
URL: http://35.181.7.121:8050
Access: Public (no login required)
```

#### 2. REST API & Documentation
```
URL: http://35.181.7.121:8000
API Docs: http://35.181.7.121:8000/docs
Access: Public (no authentication)
```

#### 3. Database Administration (pgAdmin)
```
URL: http://35.181.7.121:5050
Login: admin@admin.com
Password: admin
Access: Web-based login required
```

### Browser Compatibility

**Recommended Browsers:**
- Google Chrome (latest)
- Mozilla Firefox (latest)
- Microsoft Edge (latest)
- Safari (latest)

**Not Supported:**
- Internet Explorer

### Network Requirements

- Stable internet connection
- No VPN restrictions on ports 8000, 8050, 5050
- JavaScript enabled in browser
- Cookies enabled for pgAdmin

---

## Dashboard Guide

### Accessing the Dashboard

**URL:** http://35.181.7.121:8050

The dashboard has three main pages accessible via the top navigation bar:

1. **Vols** (Flights) - Flight search and details
2. **Meteo** (Weather) - Weather statistics
3. **Analyses** (Analytics) - Performance analysis

---

### Page 1: Vols (Flights)

**Purpose:** Search and view flight information with delay predictions

#### Search Filters

**Flight Number Search:**
- Enter partial or complete flight number (e.g., "AF", "BA123")
- Case-insensitive search
- Supports wildcards

**Date Filters:**
- **Departure Date:** Specific date (YYYY-MM-DD)
- **Date Range:** Start and end dates
- Leave blank to search all dates

**Result Limit:**
- Default: 100 flights
- Adjustable: 10 to 1000 results
- Higher limits may slow down loading

#### Flight Information Display

**Table Columns:**

| Column | Description | Example |
|--------|-------------|---------|
| Flight Number | Airline code + flight number | AF1234 |
| From | Departure airport code | CDG |
| To | Arrival airport code | JFK |
| Airline | Airline IATA code | AF |
| Scheduled Departure | Planned departure time (UTC) | 2025-12-11 14:30:00 |
| Scheduled Arrival | Planned arrival time (UTC) | 2025-12-11 18:45:00 |
| Actual Arrival | Real arrival time (UTC) | 2025-12-11 19:15:00 |
| Delay (min) | Actual delay in minutes | 30 |
| Delay Probability | ML prediction probability | 0.75 (75%) |
| Risk Level | Risk category | high |
| Prediction | Will it be delayed? | OUI (YES) |

**Understanding Predictions:**

- **Delay Probability:**
  - 0.0 to 1.0 (0% to 100%)
  - > 0.5 = Predicted delayed
  - ≤ 0.5 = Predicted on-time

- **Risk Levels:**
  - **low:** < 30% chance of delay
  - **medium:** 30-70% chance of delay
  - **high:** > 70% chance of delay

- **Prediction Column:**
  - **OUI** (YES): Model predicts delay
  - **NON** (NO): Model predicts on-time
  - **N/A**: No prediction available (flight not processed yet)

#### Example Searches

**Search 1: All Air France flights today**
- Flight Number: AF
- Departure Date: 2025-12-11
- Limit: 100

**Search 2: Specific flight**
- Flight Number: BA123
- Date Range: Last 7 days
- Limit: 50

**Search 3: All flights with high delay risk**
- Leave filters empty
- Check results for "high" risk level
- Sort by delay probability (if available)

---

### Page 2: Meteo (Weather)

**Purpose:** View weather statistics and conditions

#### Weather Statistics Card

**Displays:**
- Total METAR observations collected
- Total TAF forecasts collected
- Total sky conditions recorded
- Number of airports with weather data
- Date range of available data

#### Flight Categories Distribution

**Categories (based on visibility and ceiling):**

| Category | Meaning | Conditions |
|----------|---------|------------|
| **VFR** | Visual Flight Rules | Good visibility, clear skies |
| **MVFR** | Marginal VFR | Moderate visibility |
| **IFR** | Instrument Flight Rules | Poor visibility, low clouds |
| **LIFR** | Low IFR | Very poor visibility |

**Chart Shows:**
- Percentage of each category
- Total count per category
- Color-coded bars for easy identification

#### Weather Conditions Distribution

**Common Conditions:**
- **CLEAR:** No significant weather
- **BR:** Mist/Haze
- **RA:** Rain
- **SN:** Snow
- **FG:** Fog
- **TS:** Thunderstorm
- **DZ:** Drizzle

**Chart Shows:**
- Top 20 most common weather conditions
- Percentage and count for each
- Impact on flight operations

#### Top Airports Weather Data

**Table Displays:**

| Column | Description |
|--------|-------------|
| Airport | Airport ICAO code (e.g., LFPG for Paris CDG) |
| Observations | Number of weather reports |
| Avg Temperature | Average temperature in Celsius |
| Avg Wind Speed | Average wind speed in knots |
| Avg Visibility | Average visibility in statute miles |

**Sorted by:** Number of observations (most active airports first)

---

### Page 3: Analyses (Analytics)

**Purpose:** Deep dive into flight delay patterns and ML model performance

#### Global Statistics Card

**Key Metrics:**

| Metric | Description |
|--------|-------------|
| Total Flights | All flights in database |
| Delayed Flights | Flights delayed ≥ 10 minutes |
| Delay Rate | Percentage of delayed flights |
| Average Delay | Mean delay for delayed flights (minutes) |
| Flights with ML | Number of flights with predictions |
| ML Accuracy | Model prediction accuracy (%) |
| Date Range | Data coverage period |

**Delay Threshold:**
- Default: 10 minutes
- Flights delayed < 10 minutes = on-time
- Flights delayed ≥ 10 minutes = delayed

#### Daily Delay Evolution Chart

**Line Graph Showing:**
- X-axis: Date
- Y-axis: Delay rate (%)
- Shows trend over time
- Helps identify patterns (weekdays vs weekends)

**Use Cases:**
- Identify problematic days
- Seasonal patterns
- Impact of events

#### Hourly Delay Patterns Chart

**Bar Graph Showing:**
- X-axis: Hour of day (0-23)
- Y-axis: Delay rate (%)
- Shows which hours have most delays

**Common Patterns:**
- Morning hours (6-9): Often lower delays
- Afternoon (14-18): Higher delays (cascade effect)
- Evening (20-23): Peak delays

**Use Cases:**
- Best time to book flights
- Airport capacity planning
- Staff scheduling

#### Top Airlines by Delay Rate

**Horizontal Bar Chart:**
- Top 15 airlines by flight count
- Sorted by delay rate (ascending)
- Compare airline performance

**Insights:**
- Which airlines are most reliable
- Industry benchmarks
- Airline-specific patterns

#### ML Model Performance Section

**Confusion Matrix:**

| | Predicted On-Time | Predicted Delayed |
|---|---|---|
| **Actually On-Time** | True Negative (TN) | False Positive (FP) |
| **Actually Delayed** | False Negative (FN) | True Positive (TP) |

**Metrics:**
- **Accuracy:** (TP + TN) / Total
- **Precision:** TP / (TP + FP) - When model says "delayed", how often is it right?
- **Recall:** TP / (TP + FN) - Of all actual delays, how many did model catch?

**Risk Distribution Chart:**
- Shows distribution of flights by risk level
- Pie chart or bar chart
- Validates model calibration

---

## API Documentation

### Accessing API Documentation

**Interactive API Docs (Swagger UI):**
```
URL: http://35.181.7.121:8000/docs
```

**Alternative (ReDoc):**
```
URL: http://35.181.7.121:8000/redoc
```

### Available Endpoints

#### 1. Root Endpoint
```http
GET /
```
**Purpose:** API health check
**Response:**
```json
{
  "message": "DST Airlines API",
  "version": "1.0.0"
}
```

#### 2. Search Flights
```http
GET /search-flights
```

**Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| flight_number | string | No | Flight number (partial match) | AF123 |
| departure_date | string | No | Specific date (YYYY-MM-DD) | 2025-12-11 |
| date_start | string | No | Range start date | 2025-12-01 |
| date_end | string | No | Range end date | 2025-12-31 |
| limit | integer | No | Max results (default: all) | 100 |

**Example Request:**
```
http://35.181.7.121:8000/search-flights?flight_number=AF&limit=10
```

**Response:**
```json
[
  {
    "flight_number": "AF1234",
    "from_airport": "CDG",
    "to_airport": "JFK",
    "airline_code": "AF",
    "departure_scheduled_utc": "2025-12-11T14:30:00",
    "arrival_scheduled_utc": "2025-12-11T18:45:00",
    "arrival_actual_utc": "2025-12-11T19:15:00",
    "delay_min": 30,
    "delay_prob": 0.75,
    "delay_risk_level": "high",
    "prediction_retard": "OUI"
  }
]
```

#### 3. Global Statistics
```http
GET /stats?delay_threshold=10
```

**Parameters:**
- `delay_threshold` (integer, optional): Minutes to consider as delayed (default: 10)

**Response:**
```json
{
  "total_flights": 15420,
  "delayed_flights": 3245,
  "delay_rate": 21.05,
  "avg_delay": 45.3,
  "flights_with_ml": 12300,
  "ml_accuracy": 78.5,
  "date_min": "2025-11-01",
  "date_max": "2025-12-11"
}
```

#### 4. Daily Statistics
```http
GET /stats/daily?delay_threshold=10
```

**Returns:** Array of daily statistics

```json
[
  {
    "date": "2025-12-11",
    "total": 1250,
    "delayed": 285,
    "delay_rate": 22.8
  }
]
```

#### 5. Hourly Statistics
```http
GET /stats/hourly?delay_threshold=10
```

**Returns:** Array of hourly patterns (0-23)

```json
[
  {
    "hour": 14,
    "flights": 850,
    "delay_rate": 28.5
  }
]
```

#### 6. Airline Statistics
```http
GET /stats/airlines?delay_threshold=10&top=15
```

**Parameters:**
- `delay_threshold`: Minutes for delay definition
- `top`: Number of airlines to return (default: 15)

**Returns:** Top airlines ranked by flight count, sorted by delay rate

#### 7. ML Confusion Matrix
```http
GET /ml/confusion?delay_threshold=10
```

**Response:**
```json
{
  "tp": 1250,
  "tn": 8900,
  "fp": 780,
  "fn": 1370,
  "accuracy": 82.45
}
```

#### 8. ML Risk Distribution
```http
GET /ml/risk-distribution
```

**Response:**
```json
[
  {
    "delay_risk_level": "low",
    "count": 6500
  },
  {
    "delay_risk_level": "medium",
    "count": 3200
  },
  {
    "delay_risk_level": "high",
    "count": 2600
  }
]
```

#### 9. Weather Statistics
```http
GET /meteo/stats
```

**Response:**
```json
{
  "total_metar": 45230,
  "total_taf": 12450,
  "total_sky_conditions": 89560,
  "airports_metar": 185,
  "airports_taf": 142,
  "date_min_metar": "2025-11-01",
  "date_max_metar": "2025-12-11",
  "date_min_taf": "2025-11-01",
  "date_max_taf": "2025-12-11"
}
```

#### 10. Flight Categories
```http
GET /meteo/flight-categories
```

**Returns:** Distribution of VFR/IFR/MVFR/LIFR

#### 11. Weather Conditions
```http
GET /meteo/weather-conditions
```

**Returns:** Top 20 weather conditions with counts

#### 12. Top Airports (Weather)
```http
GET /meteo/top-airports?limit=20
```

**Returns:** Airports with most weather observations

### Using the API

#### Browser (Simple GET Requests)

Just paste URL in browser:
```
http://35.181.7.121:8000/stats
```

#### Command Line (curl)

```bash
# Get global statistics
curl http://35.181.7.121:8000/stats

# Search flights
curl "http://35.181.7.121:8000/search-flights?flight_number=AF&limit=10"

# Get daily stats with custom threshold
curl "http://35.181.7.121:8000/stats/daily?delay_threshold=15"
```

#### Python (requests library)

```python
import requests

# Base URL
BASE_URL = "http://35.181.7.121:8000"

# Get statistics
response = requests.get(f"{BASE_URL}/stats")
data = response.json()
print(f"Total flights: {data['total_flights']}")

# Search flights
params = {
    "flight_number": "AF",
    "departure_date": "2025-12-11",
    "limit": 10
}
response = requests.get(f"{BASE_URL}/search-flights", params=params)
flights = response.json()
for flight in flights:
    print(f"{flight['flight_number']}: {flight['delay_prob']}")
```

#### JavaScript (fetch API)

```javascript
// Get statistics
fetch('http://35.181.7.121:8000/stats')
  .then(response => response.json())
  .then(data => {
    console.log('Total flights:', data.total_flights);
    console.log('Delay rate:', data.delay_rate + '%');
  });

// Search flights
const params = new URLSearchParams({
  flight_number: 'AF',
  limit: 10
});
fetch(`http://35.181.7.121:8000/search-flights?${params}`)
  .then(response => response.json())
  .then(flights => {
    flights.forEach(flight => {
      console.log(`${flight.flight_number}: ${flight.prediction_retard}`);
    });
  });
```

---

## Database Management

### Accessing pgAdmin

**URL:** http://35.181.7.121:5050

**Login Credentials:**
- Email: `admin@admin.com`
- Password: `admin`

### First Time Setup

**Connect to PostgreSQL Database:**

1. After logging in, click **Servers** in left panel
2. Right-click **Servers** → **Register** → **Server**
3. In **General** tab:
   - Name: `Airlines PostgreSQL`
4. In **Connection** tab:
   - Host name/address: `airlines_postgresql`
   - Port: `5432`
   - Maintenance database: `airlines_db`
   - Username: `postgres`
   - Password: `postgres`
   - Check ✓ **Save password**
5. Click **Save**

### Database Structure

**Database:** `airlines_db`

**Main Tables:**

#### 1. flight
**Stores:** Flight information and predictions

**Key Columns:**
- `flight_id` (primary key)
- `flight_number` (e.g., "AF1234")
- `from_airport` (departure airport code)
- `to_airport` (arrival airport code)
- `airline_code` (airline IATA code)
- `departure_scheduled_utc` (planned departure)
- `arrival_scheduled_utc` (planned arrival)
- `arrival_actual_utc` (actual arrival)
- `delay_min` (actual delay in minutes)
- `delay_prob` (ML prediction probability)
- `delay_risk_level` (low/medium/high)

#### 2. metar
**Stores:** Weather observations (current conditions)

**Key Columns:**
- `metar_id` (primary key)
- `station_id` (airport ICAO code)
- `observation_time` (when observed)
- `temp_c` (temperature Celsius)
- `wind_speed_kt` (wind speed knots)
- `visibility_statute_mi` (visibility miles)
- `flight_category` (VFR/IFR/MVFR/LIFR)
- `wx_string` (weather phenomena)

#### 3. taf
**Stores:** Terminal Aerodrome Forecasts (weather predictions)

**Key Columns:**
- `taf_id` (primary key)
- `station_id` (airport ICAO code)
- `issue_time` (when issued)
- `valid_from` (forecast start)
- `valid_to` (forecast end)
- `raw_text` (full TAF text)

#### 4. sky_condition
**Stores:** Cloud layers and ceiling information

**Key Columns:**
- `sky_condition_id` (primary key)
- `metar_id` (foreign key to metar)
- `sky_cover` (SKC/FEW/SCT/BKN/OVC)
- `cloud_base_ft_agl` (cloud base in feet)

### Common Queries

**Query 1: Recent flights with delays**
```sql
SELECT
    flight_number,
    from_airport,
    to_airport,
    departure_scheduled_utc,
    delay_min,
    delay_prob,
    delay_risk_level
FROM flight
WHERE delay_min >= 10
ORDER BY departure_scheduled_utc DESC
LIMIT 100;
```

**Query 2: Airline performance**
```sql
SELECT
    airline_code,
    COUNT(*) as total_flights,
    AVG(delay_min) as avg_delay,
    SUM(CASE WHEN delay_min >= 10 THEN 1 ELSE 0 END) as delayed_count,
    ROUND(AVG(CASE WHEN delay_min >= 10 THEN 1.0 ELSE 0.0 END) * 100, 2) as delay_rate
FROM flight
WHERE airline_code IS NOT NULL
GROUP BY airline_code
ORDER BY total_flights DESC
LIMIT 20;
```

**Query 3: Weather impact**
```sql
SELECT
    m.flight_category,
    COUNT(DISTINCT f.flight_id) as flights,
    AVG(f.delay_min) as avg_delay,
    SUM(CASE WHEN f.delay_min >= 10 THEN 1 ELSE 0 END) as delayed_flights
FROM flight f
JOIN metar m ON f.from_airport = m.station_id
WHERE m.observation_time BETWEEN f.departure_scheduled_utc - INTERVAL '2 hours'
    AND f.departure_scheduled_utc + INTERVAL '2 hours'
GROUP BY m.flight_category
ORDER BY delayed_flights DESC;
```

**Query 4: ML model accuracy by risk level**
```sql
SELECT
    delay_risk_level,
    COUNT(*) as total,
    SUM(CASE
        WHEN (delay_prob > 0.5 AND delay_min >= 10) OR
             (delay_prob <= 0.5 AND delay_min < 10)
        THEN 1 ELSE 0
    END) as correct_predictions,
    ROUND(AVG(CASE
        WHEN (delay_prob > 0.5 AND delay_min >= 10) OR
             (delay_prob <= 0.5 AND delay_min < 10)
        THEN 1.0 ELSE 0.0
    END) * 100, 2) as accuracy
FROM flight
WHERE delay_prob IS NOT NULL
GROUP BY delay_risk_level
ORDER BY
    CASE delay_risk_level
        WHEN 'low' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'high' THEN 3
    END;
```

### Exporting Data

**From pgAdmin:**
1. Right-click on table → **Import/Export Data**
2. Select **Export**
3. Choose format (CSV, JSON, etc.)
4. Set file location
5. Click **OK**

**From Command Line:**
```bash
# Export to CSV
docker exec airlines_postgresql psql -U postgres -d airlines_db -c "COPY (SELECT * FROM flight WHERE departure_scheduled_utc >= '2025-12-01') TO STDOUT WITH CSV HEADER" > flights_export.csv

# Export full table
docker exec airlines_postgresql pg_dump -U postgres -d airlines_db -t flight --data-only --column-inserts > flight_data.sql
```

---

## Data Collection Process

### How Data Collection Works

**Automated Schedule:**
- Runs every 60 minutes
- Executes at minute 35 of each hour (XX:35)
- Collects both real-time and historical data

**Collection Workflow:**

1. **Airport Selection:**
   - Top 200 airports by traffic
   - Worldwide coverage
   - Focus on major hubs

2. **Flight Data Collection:**
   - **Real-time:** Next 1 hour of departures
   - **Historical:** Past 20 hours of arrivals
   - Source: airportinfo.live

3. **Weather Data Collection:**
   - METAR (current observations)
   - TAF (forecasts)
   - Source: NOAA Aviation Weather

4. **Machine Learning Prediction:**
   - Applies trained XGBoost model
   - Calculates delay probability
   - Assigns risk level

5. **Database Storage:**
   - Raw data → MongoDB
   - Processed data → PostgreSQL
   - Indexed for fast queries

### Monitoring Collection

**View real-time logs:**
```bash
# SSH into EC2
ssh -i ~/Downloads/airlines-key-v2.pem ubuntu@35.181.7.121

# Navigate to project
cd projet-avril25_cde_airlines-dockerisation

# View logs
docker-compose logs -f flight-collector
```

**Log Indicators:**

✅ **Healthy:**
```
[15:35:00] === Démarrage de la collecte ===
[15:35:05] Collecte temps réel: 200 aéroports
[15:35:30] 1,234 vols collectés
[15:36:00] Collecte historique: 200 aéroports
[15:37:00] 2,456 vols collectés
[15:38:00] Prédictions ML appliquées: 3,690 vols
[15:39:00] === Collecte terminée avec succès ===
```

❌ **Issues:**
```
ERROR: Rate limit exceeded
ERROR: API key invalid
ERROR: Database connection failed
ERROR: Timeout collecting airport XXXX
```

### Manual Collection Trigger

**Force immediate collection:**
```bash
# SSH into EC2
ssh -i ~/Downloads/airlines-key-v2.pem ubuntu@35.181.7.121

cd projet-avril25_cde_airlines-dockerisation

# Stop current service
docker-compose stop flight-collector

# Run once manually
docker-compose run --rm flight-collector

# Or restart service
docker-compose start flight-collector
```

### Data Retention

**Current Setup:**
- No automatic deletion
- All historical data retained
- Manual cleanup required for disk space

**Manual Cleanup (if needed):**
```sql
-- Delete flights older than 30 days
DELETE FROM flight
WHERE departure_scheduled_utc < NOW() - INTERVAL '30 days';

-- Delete weather data older than 7 days
DELETE FROM metar
WHERE observation_time < NOW() - INTERVAL '7 days';

DELETE FROM taf
WHERE issue_time < NOW() - INTERVAL '7 days';
```

---

## Machine Learning Predictions

### Model Information

**Algorithm:** XGBoost (Extreme Gradient Boosting)
**Task:** Binary classification (delayed vs on-time)
**Threshold:** 10 minutes delay
**Training Data:** Historical flight data with actual delay outcomes

### Features Used by Model

**Flight Features:**
- Hour of departure
- Day of week
- Month
- Airline
- Origin airport
- Destination airport
- Flight distance (if available)

**Weather Features (if available):**
- Temperature
- Wind speed
- Visibility
- Flight category (VFR/IFR)
- Weather phenomena

**Historical Features:**
- Airport average delays
- Airline average delays
- Route average delays

### Understanding Predictions

**Delay Probability (delay_prob):**
- Range: 0.0 to 1.0
- Interpretation:
  - 0.0-0.3: Low risk of delay
  - 0.3-0.7: Medium risk of delay
  - 0.7-1.0: High risk of delay
- Threshold: 0.5 (> 0.5 = predicted delayed)

**Risk Level (delay_risk_level):**
- **low:** delay_prob < 0.3
- **medium:** 0.3 ≤ delay_prob ≤ 0.7
- **high:** delay_prob > 0.7

**Binary Prediction (prediction_retard):**
- **OUI** (YES): delay_prob > 0.5
- **NON** (NO): delay_prob ≤ 0.5
- **N/A**: No prediction available

### Model Performance

**Typical Metrics:**
- Accuracy: ~75-85%
- Precision: ~70-80%
- Recall: ~60-75%
- F1-Score: ~65-77%

**Note:** Performance varies by:
- Airline (some more predictable)
- Airport (hub complexity)
- Weather severity
- Time period

### When Predictions Are Not Available

**Reasons for N/A:**
- Flight just added to system
- Missing required features
- Model not yet processed this flight
- Data quality issues

**Wait for next cycle** (runs hourly at XX:35)

### Model Updates

**Current Model:**
- Location: `machine_learning/model_output/`
- Files:
  - `flight_delay_model_*.joblib` (model)
  - `preprocessor_*.joblib` (feature processor)
  - `production_config_*.json` (configuration)
  - `model_metrics_*.json` (performance metrics)

**Retraining:**
- Manual process (not automated)
- Requires sufficient historical data
- Update model files and restart service

---

## Common Tasks

### Task 1: Search for a Specific Flight

**Via Dashboard:**
1. Go to http://35.181.7.121:8050
2. Click **Vols** tab
3. Enter flight number in search box
4. Optionally add date filter
5. Click search button
6. View results in table

**Via API:**
```bash
curl "http://35.181.7.121:8000/search-flights?flight_number=AF1234&departure_date=2025-12-11"
```

### Task 2: Check System Status

**SSH into server:**
```bash
ssh -i ~/Downloads/airlines-key-v2.pem ubuntu@35.181.7.121
cd projet-avril25_cde_airlines-dockerisation
docker-compose ps
```

**All services should show "Up" status**

### Task 3: View Recent Collection Logs

```bash
# SSH into server
ssh -i ~/Downloads/airlines-key-v2.pem ubuntu@35.181.7.121
cd projet-avril25_cde_airlines-dockerisation
docker-compose logs --tail=100 flight-collector
```

### Task 4: Export Flight Data

**Via pgAdmin:**
1. Login to http://35.181.7.121:5050
2. Navigate to Airlines PostgreSQL → airlines_db → Schemas → public → Tables → flight
3. Right-click → **Import/Export Data**
4. Select **Export**
5. Choose CSV format
6. Download file

**Via API:**
```bash
# Get all flights from today
curl "http://35.181.7.121:8000/search-flights?departure_date=2025-12-11&limit=10000" > flights_today.json
```

### Task 5: Restart a Service

```bash
# SSH into server
ssh -i ~/Downloads/airlines-key-v2.pem ubuntu@35.181.7.121
cd projet-avril25_cde_airlines-dockerisation

# Restart specific service
docker-compose restart fastapi
# or
docker-compose restart flight-collector
# or
docker-compose restart dash
```

### Task 6: Check Database Size

**Via pgAdmin:**
```sql
SELECT
    pg_size_pretty(pg_database_size('airlines_db')) as database_size,
    pg_size_pretty(pg_total_relation_size('flight')) as flight_table_size,
    pg_size_pretty(pg_total_relation_size('metar')) as metar_table_size;
```

**Via SSH:**
```bash
docker exec airlines_postgresql psql -U postgres -d airlines_db -c "SELECT pg_size_pretty(pg_database_size('airlines_db'));"
```

### Task 7: View ML Model Performance

**Via Dashboard:**
1. Go to http://35.181.7.121:8050
2. Click **Analyses** tab
3. Scroll to "ML Model Performance" section
4. View confusion matrix and accuracy

**Via API:**
```bash
curl http://35.181.7.121:8000/ml/confusion
curl http://35.181.7.121:8000/ml/risk-distribution
```

### Task 8: Update Configuration

```bash
# SSH into server
ssh -i ~/Downloads/airlines-key-v2.pem ubuntu@35.181.7.121
cd projet-avril25_cde_airlines-dockerisation

# Edit .env file
nano .env

# Make changes (e.g., NUM_AIRPORTS, ENABLE_WEATHER)
# Save: Ctrl+X, Y, Enter

# Restart affected services
docker-compose restart flight-collector
```

### Task 9: Backup Database

```bash
# SSH into server
ssh -i ~/Downloads/airlines-key-v2.pem ubuntu@35.181.7.121

# Backup PostgreSQL
docker exec airlines_postgresql pg_dump -U postgres airlines_db > ~/backup_$(date +%Y%m%d).sql

# Download to local machine (run from local PowerShell)
scp -i ~/Downloads/airlines-key-v2.pem ubuntu@35.181.7.121:~/backup_*.sql ./
```

### Task 10: Check Disk Space

```bash
# SSH into server
ssh -i ~/Downloads/airlines-key-v2.pem ubuntu@35.181.7.121

# Check overall disk usage
df -h

# Check Docker disk usage
docker system df

# Check database sizes
du -sh ~/projet-avril25_cde_airlines-dockerisation/
```

---

## Frequently Asked Questions

### General Questions

**Q: How often is data collected?**
A: Every 60 minutes at minute :35 (e.g., 15:35, 16:35, 17:35)

**Q: How many airports are monitored?**
A: 200 major airports worldwide (configurable in .env)

**Q: Is the system running 24/7?**
A: Yes, as long as the EC2 instance is running

**Q: Can I access this from mobile?**
A: Yes, the dashboard is responsive and works on mobile browsers

**Q: Is there a cost to use this?**
A: Free tier for first year on AWS. After that, ~$8-30/month depending on usage

### Data Questions

**Q: How far back does historical data go?**
A: Depends on when you started collecting. System stores all data indefinitely

**Q: Why do some flights not have predictions?**
A: Predictions are added during the next collection cycle (hourly)

**Q: What does "N/A" mean in predictions?**
A: Flight hasn't been processed by ML model yet. Wait for next collection cycle

**Q: How accurate are the predictions?**
A: Typically 75-85% accuracy. Check actual metrics in Analyses page

**Q: Can I download the data?**
A: Yes, via pgAdmin export or API calls

### Technical Questions

**Q: Services are not accessible from browser?**
A: Check:
1. EC2 instance is running
2. Security group rules are correct
3. Docker containers are running (`docker-compose ps`)
4. No firewall blocking ports on your network

**Q: pgAdmin shows password error?**
A: Manually add server connection with credentials: postgres/postgres, host: airlines_postgresql

**Q: Flight collector logs show errors?**
A: Common issues:
- API rate limiting (reduce NUM_AIRPORTS or increase DELAY)
- API key missing (add API_NINJAS_KEY for weather)
- Database connection (check PostgreSQL is healthy)

**Q: Dashboard is slow?**
A:
- Reduce date range in queries
- Lower result limit
- Consider upgrading to t3.small instance (more RAM)

**Q: How do I stop the system?**
A: SSH into server, run `docker-compose down`

**Q: How do I restart after stopping?**
A: SSH into server, run `docker-compose up -d`

**Q: Can I change collection frequency?**
A: Yes, edit LOOP_INTERVAL_MINUTES in .env file

**Q: How do I add more airports?**
A: Increase NUM_AIRPORTS in .env (max depends on source data availability)

### Troubleshooting Questions

**Q: Dashboard shows "Connection Error"?**
A: FastAPI service might be down. Check with `docker-compose ps` and restart if needed

**Q: No new data being collected?**
A: Check flight-collector logs: `docker-compose logs -f flight-collector`

**Q: Out of disk space?**
A:
1. Check usage: `df -h`
2. Clean old data from database
3. Increase EBS volume size in AWS console

**Q: Out of memory?**
A: t2.micro only has 1GB RAM. Upgrade to t3.small or reduce NUM_AIRPORTS

**Q: API returns empty results?**
A: Database might be empty. Wait for first collection cycle to complete

### Configuration Questions

**Q: How do I change database passwords?**
A:
1. Update docker-compose.yml (service environment variables)
2. Update .env file (connection URIs)
3. Recreate containers: `docker-compose down -v && docker-compose up -d`

**Q: How do I disable weather collection?**
A: Set `ENABLE_WEATHER=false` in .env and restart flight-collector

**Q: Can I collect only real-time data (no historical)?**
A: Set `COLLECT_PAST=false` in .env

**Q: How do I run collection only once (testing)?**
A: Set `RUN_ONCE=true` in .env

**Q: Where are logs stored?**
A: Docker container logs. View with `docker-compose logs`

---

## Getting Help

### Resources

**Project Files:**
- `README.md` - Basic project information
- `AWS_DEPLOYMENT_CONFIGURATION.md` - Deployment guide
- `USER_GUIDE.md` - This document

**AWS Documentation:**
- EC2: https://docs.aws.amazon.com/ec2/
- Security Groups: https://docs.aws.amazon.com/vpc/latest/userguide/VPC_SecurityGroups.html

**Docker Documentation:**
- Docker Compose: https://docs.docker.com/compose/
- Container logs: https://docs.docker.com/engine/reference/commandline/logs/

**API Documentation:**
- FastAPI: https://fastapi.tiangolo.com/
- Interactive Docs: http://35.181.7.121:8000/docs

### Support Contacts

**Technical Issues:**
- Check logs first: `docker-compose logs [service-name]`
- Review troubleshooting section above
- Search online for specific error messages

**AWS Issues:**
- AWS Support: https://console.aws.amazon.com/support/
- AWS Free Tier FAQ: https://aws.amazon.com/free/

**Database Issues:**
- PostgreSQL Docs: https://www.postgresql.org/docs/
- pgAdmin Docs: https://www.pgadmin.org/docs/

---

## Appendix

### Quick Reference Commands

**SSH Connection:**
```bash
ssh -i ~/Downloads/airlines-key-v2.pem ubuntu@35.181.7.121
```

**Navigate to Project:**
```bash
cd projet-avril25_cde_airlines-dockerisation
```

**View All Containers:**
```bash
docker-compose ps
```

**View Logs:**
```bash
docker-compose logs -f [service-name]
```

**Restart Service:**
```bash
docker-compose restart [service-name]
```

**Stop All:**
```bash
docker-compose down
```

**Start All:**
```bash
docker-compose up -d
```

**Clean Restart:**
```bash
docker-compose down -v
docker-compose up -d
```

### Service Ports Quick Reference

| Port | Service | Access |
|------|---------|--------|
| 22 | SSH | Terminal only |
| 5432 | PostgreSQL | Database clients |
| 27017 | MongoDB | Database clients |
| 5050 | pgAdmin | http://35.181.7.121:5050 |
| 8000 | FastAPI | http://35.181.7.121:8000 |
| 8050 | Dash | http://35.181.7.121:8050 |

### Airport Codes Reference

**Major Hubs Monitored:**
- CDG - Paris Charles de Gaulle
- JFK - New York JFK
- LHR - London Heathrow
- FRA - Frankfurt
- AMS - Amsterdam Schiphol
- DXB - Dubai
- HND - Tokyo Haneda
- SIN - Singapore Changi
- ORD - Chicago O'Hare
- LAX - Los Angeles
- And 190+ more...

### Weather Codes Reference

**Flight Categories:**
- VFR - Visual Flight Rules (good weather)
- MVFR - Marginal VFR (moderate weather)
- IFR - Instrument Flight Rules (poor weather)
- LIFR - Low IFR (very poor weather)

**Common Weather Phenomena:**
- BR - Mist
- FG - Fog
- RA - Rain
- SN - Snow
- TS - Thunderstorm
- DZ - Drizzle
- GR - Hail
- FU - Smoke
- VA - Volcanic Ash

---

*Document Version: 1.0*
*Last Updated: December 11, 2025*
*System Deployed: December 11, 2025*
*Public IP: 35.181.7.121*
