--Tables de stagging pour préparer les chargements depuis les fichiers csv

CREATE TABLE IF NOT EXISTS public.airlines_openfligths
(
    airline_id integer,
    name text,
    alias text,
    iata text,
    icao text,
    callsign text,
    country text,
    active text
);

CREATE TABLE IF NOT EXISTS public.airports_openfligths
(
    airport_id integer,
    name text,
    city text,
    country text,
    iata text,
    icao text,
    latitude double precision,
    longitude double precision,
    altitude integer,
    timezone text,
    dst text,
    tz text,
    type text,
    source text,
--    geom geometry(Point,4326)
);

CREATE TABLE IF NOT EXISTS public.planes_openfligths
(
    name text,
    iata text,
    icao text
);

CREATE TABLE IF NOT EXISTS public.routes_openfligths
(
    airline_iata text,
    airline_id integer,
    source_airport_iata text,
    source_airport_id integer,
    dest_airport_iata text,
    dest_airport_id integer,
    shared text,
    stops integer,
    equipments text,
    dist double precision
);

CREATE TABLE IF NOT EXISTS public.routes_text_openfligths
(
    airline_iata text,
    airline_id text,
    source_airport_iata text,
    source_airport_id text,
    dest_airport_iata text,
    dest_airport_id text,
    shared text,
    stops text,
    equipments text
);

CREATE TABLE AIRPORTS_OURAIRPORTSCREATE TABLE AIRPORTS_OURAIRPORTS (
id integer,
ident text,
type text,
name text,
latitude_deg double precision,
longitude_deg double precision,
elevation_ft float,
continent TEXT,
iso_country TEXT,
iso_region TEXT,
municipality TEXT,
scheduled_service TEXT,
icao_code TEXT,
iata_code TEXT,
gps_code TEXT,
local_code TEXT,
home_link TEXT,
wikipedia_link TEXT,
keywords TEXT);
;






