CREATE TABLE flight (
    id BIGSERIAL PRIMARY KEY,
    flight_number VARCHAR(20) NOT NULL,
    from_airport VARCHAR(10) NOT NULL,
    to_airport VARCHAR(10) NOT NULL,
    airline_code VARCHAR(10),
    aircraft_code VARCHAR(10),

    -- Stockage temporaire des IDs MongoDB pour le mapping
    departure_metar_external_id TEXT,    -- ID MongoDB du METAR
    arrival_taf_external_id TEXT,        -- ID MongoDB du TAF
    
    -- Clés étrangères courtes (remplies après mapping)
    departure_metar_fk BIGINT,           -- Référence vers metar(id)
    arrival_taf_fk BIGINT,               -- Référence vers taf(id)
    
    departure_scheduled_utc TIMESTAMP WITHOUT TIME ZONE,
    departure_actual_utc TIMESTAMP WITHOUT TIME ZONE,
    departure_terminal VARCHAR(10),
    departure_gate VARCHAR(10),

    arrival_scheduled_utc TIMESTAMP WITHOUT TIME ZONE,
    arrival_actual_utc TIMESTAMP WITHOUT TIME ZONE,
    arrival_terminal VARCHAR(10),
    arrival_gate VARCHAR(10),

    status VARCHAR(200),
    delay_min INTEGER
);




CREATE TABLE metar (
    id BIGSERIAL PRIMARY KEY,               -- Clé primaire courte
    external_id TEXT UNIQUE NOT NULL,       -- ID MongoDB original
    observation_time TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    raw_text TEXT NOT NULL,
    station_id VARCHAR(10) NOT NULL,
    wind_dir_degrees VARCHAR(3),

    temp_c NUMERIC(5,2),
    dewpoint_c NUMERIC(5,2),
    wind_speed_kt SMALLINT,
    wind_gust_kt SMALLINT,
    visibility_statute_mi NUMERIC(5,2),
    altim_in_hg NUMERIC(5,2),
    sea_level_pressure_mb NUMERIC(6,2),

    flight_category VARCHAR(10),
    maxt_c NUMERIC(5,2),
    mint_c NUMERIC(5,2),
    metar_type VARCHAR(20),

    pcp3hr_in NUMERIC(6,3),
    pcp6hr_in NUMERIC(6,3),
    pcp24hr_in NUMERIC(6,3),
    precip_in NUMERIC(6,3),

    three_hr_pressure_tendency_mb NUMERIC(6,2),
    vert_vis_ft INTEGER,
    wx_string VARCHAR(255)
);


CREATE TABLE taf (
    id BIGSERIAL PRIMARY KEY,               -- Clé primaire courte
    external_id TEXT UNIQUE NOT NULL,       -- ID MongoDB original
    station_id VARCHAR(10) NOT NULL, -- code ICAO
    issue_time TIMESTAMP WITHOUT TIME ZONE NOT NULL,   -- moment d’émission
    bulletin_time TIMESTAMP WITHOUT TIME ZONE,         -- timestamp bulletin brut
    valid_time_from TIMESTAMP WITHOUT TIME ZONE,       -- début validité
    valid_time_to TIMESTAMP WITHOUT TIME ZONE,         -- fin validité

    remarks TEXT,
    fcst_time_from TIMESTAMP WITHOUT TIME ZONE,        -- début prévision
    fcst_time_to TIMESTAMP WITHOUT TIME ZONE,          -- fin prévision

    wind_dir_degrees SMALLINT,
    wind_speed_kt SMALLINT,
    wind_gust_kt SMALLINT,
    visibility_statute_mi NUMERIC(5,2),
    vert_vis_ft INTEGER,

    wx_string VARCHAR(255),     -- phénomènes météo (RA, SN, BR, etc.)

    altim_in_hg NUMERIC(5,2),

    change_indicator VARCHAR(20),  -- TEMPO, BECMG, PROBxx, etc.
    probability SMALLINT,          -- probabilité (ex. 30 ou 40 %)

    max_temp_c NUMERIC(5,2),
    min_temp_c NUMERIC(5,2),

    raw_text TEXT NOT NULL          -- TAF complet en texte brut
);




CREATE TABLE sky_condition (
    id BIGSERIAL PRIMARY KEY,
    metar_fk BIGINT,                        -- Référence vers metar(id)
    taf_fk BIGINT,                          -- Référence vers taf(id)
    sky_cover VARCHAR(50) NOT NULL,
    cloud_base_ft_agl INTEGER,
    cloud_type VARCHAR(50),
    condition_order SMALLINT NOT NULL, -- ordre de la condition (1, 2, 3, 4)
    
    FOREIGN KEY (metar_fk) REFERENCES metar(id) ON DELETE CASCADE,
    FOREIGN KEY (taf_fk) REFERENCES taf(id) ON DELETE CASCADE,
    
    -- Contrainte pour s'assurer qu'une condition appartient soit à METAR soit à TAF, mais pas les deux
    CONSTRAINT chk_single_parent CHECK (
        (metar_fk IS NOT NULL AND taf_fk IS NULL) OR 
        (metar_fk IS NULL AND taf_fk IS NOT NULL)
    )
);

-- Ajout des contraintes de clés étrangères pour flight (après création des tables)
ALTER TABLE flight 
    ADD CONSTRAINT fk_flight_metar FOREIGN KEY (departure_metar_fk) REFERENCES metar(id),
    ADD CONSTRAINT fk_flight_taf FOREIGN KEY (arrival_taf_fk) REFERENCES taf(id);