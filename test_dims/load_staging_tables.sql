SET client_encoding = 'UTF8';

COPY airports_openfligth(airport_id, name, city, country, iata, icao, latitude, longitude, altitude, timezone, dst, tz, type, source) 
FROM 'D:\airlines\airports.dat' WITH (FORMAT csv);

COPY airlines_openfligth(airline_id, name, alias, iata, icao, callsign, country, active) 
FROM 'D:\airlines\airlines.dat' WITH (FORMAT csv);

COPY planes_openfligth(name, iata, icao) FROM 'D:\airlines\planes.dat' WITH (FORMAT csv);

COPY routes_text_openfligth(airline_iata, airline_id, source_airport_iata, source_airport_id, dest_airport_iata, dest_airport_id, shared, stops, equipments) 
FROM 'D:\airlines\routes.dat' WITH (FORMAT csv);

                                                                                           

INSERT INTO routes_openfligth (
    airline_iata, airline_id, source_airport_iata, source_airport_id,
    dest_airport_iata, dest_airport_id, shared, stops, equipments
)
SELECT 
    NULLIF(airline_iata, '\N'),
    CASE WHEN airline_id = '\N' THEN NULL ELSE CAST(airline_id AS INTEGER) END,
    NULLIF(source_airport_iata, '\N'),
    CASE WHEN source_airport_id = '\N' THEN NULL ELSE CAST(source_airport_id AS INTEGER) END,
    NULLIF(dest_airport_iata, '\N'),
    CASE WHEN dest_airport_id = '\N' THEN NULL ELSE CAST(dest_airport_id AS INTEGER) END,
    NULLIF(shared, '\N'),
    CASE WHEN stops = '\N' THEN NULL ELSE CAST(stops AS INTEGER) END,
    NULLIF(equipments, '\N')
FROM routes_text_openfligth;

----------------------------------------------------------

COPY AIRPORTS_OURAIRPORTS (id, ident, type,name,latitude_deg,longitude_deg,elevation_ft,continent,iso_country,iso_region,municipality,scheduled_service,icao_code,iata_code,gps_code,local_code,home_link,wikipedia_link,keywords)
FROM 'D:\airlines\airports_ourairports.csv' WITH (FORMAT csv, HEADER true);
