-- Table de référence pour les codes de couverture nuageuse
CREATE TABLE sky_cover_reference (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,       -- Code METAR/TAF (FEW, SCT, BKN, OVC, etc.)
    description VARCHAR(100) NOT NULL,      -- Description en français
    description_en VARCHAR(100) NOT NULL,   -- Description en anglais
    octal_min DECIMAL(2,1),                 -- Couverture minimale en octals (1/8)
    octal_max DECIMAL(2,1),                 -- Couverture maximale en octals (1/8)
    percentage_min INTEGER,                 -- Pourcentage de couverture minimum
    percentage_max INTEGER,                 -- Pourcentage de couverture maximum
    is_special_code BOOLEAN DEFAULT FALSE,  -- Indique si c'est un code spécial (NSC, SKC, etc.)
    sort_order INTEGER,                     -- Ordre de tri pour affichage
    notes TEXT                              -- Notes additionnelles
);

-- Insertion des données de référence pour les codes de couverture nuageuse
INSERT INTO sky_cover_reference (code, description, description_en, octal_min, octal_max, percentage_min, percentage_max, is_special_code, sort_order, notes) VALUES
-- Codes standards de couverture
('FEW', 'Peu de nuages', 'Few clouds', 1.0, 2.0, 12, 25, FALSE, 1, 'Couverture nuageuse de 1/8 à 2/8'),
('SCT', 'Nuages épars', 'Scattered clouds', 3.0, 4.0, 37, 50, FALSE, 2, 'Couverture nuageuse de 3/8 à 4/8'),
('BKN', 'Ciel fragmenté', 'Broken clouds', 5.0, 7.0, 62, 87, FALSE, 3, 'Couverture nuageuse de 5/8 à 7/8'),
('OVC', 'Ciel couvert', 'Overcast clouds', 8.0, 8.0, 100, 100, FALSE, 4, 'Couverture nuageuse complète 8/8'),

-- Codes spéciaux
('NSC', 'Pas de nuages significatifs', 'No significant cloud cover', NULL, NULL, NULL, NULL, TRUE, 10, 'Aucun nuage en dessous de 5000 ft, mais présence possible au-dessus (non CB/TCU)'),
('SKC', 'Ciel dégagé', 'Sky clear', 0.0, 0.0, 0, 0, TRUE, 11, 'Aucune couverture nuageuse (déterminé par météorologue)'),
('NCD', 'Nuages non détectés', 'No clouds detected', NULL, NULL, NULL, NULL, TRUE, 12, 'Aucun nuage mesuré (stations météo automatiques)'),
('CLR', 'Ciel dégagé détecté', 'Clear sky detected', 0.0, 0.0, 0, 0, TRUE, 13, 'Aucune couverture nuageuse détectée en dessous de 12000 ft (stations automatiques)'),

-- Code pour visibilité verticale
('VV', 'Visibilité verticale', 'Vertical visibility', NULL, NULL, NULL, NULL, TRUE, 20, 'Visibilité verticale obscurcie, base nuageuse impossible à établir');



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
    departure_final_utc TIMESTAMP WITHOUT TIME ZONE,
    departure_terminal VARCHAR(10),
    departure_gate VARCHAR(10),

    arrival_scheduled_utc TIMESTAMP WITHOUT TIME ZONE,
    arrival_actual_utc TIMESTAMP WITHOUT TIME ZONE,
    arrival_terminal VARCHAR(10),
    arrival_gate VARCHAR(10),

    status VARCHAR(200),                 -- Statut initial du vol (lors de l'insertion)
    status_final VARCHAR(200),           -- Statut final du vol (mis à jour avec les données réelles)
    delay_min INTEGER,
    delay_prob NUMERIC(5,4),
    delay_risk_level VARCHAR(20)
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
    --FOREIGN KEY (sky_cover) REFERENCES sky_cover_reference(code) ON DELETE RESTRICT,
    
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

CREATE INDEX IF NOT EXISTS sc_metar_ord1
  ON sky_condition (metar_fk, condition_order)
  WHERE metar_fk IS NOT NULL;

CREATE INDEX IF NOT EXISTS sc_taf_ord1
  ON sky_condition (taf_fk, condition_order)
  WHERE taf_fk IS NOT NULL;

-- Index composite optimal pour les mises à jour de vols
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flight_update_lookup 
ON flight (flight_number, from_airport, to_airport, departure_scheduled_utc);

-- Index partiel pour les vols pas encore mis à jour (optionnel mais très utile)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_flight_pending_updates 
ON flight (flight_number, from_airport, to_airport) 
WHERE status_final IS NULL;





CREATE OR REPLACE VIEW public."all"
 AS
 SELECT f.id AS f_id,
    f.flight_number,
    f.from_airport,
    f.to_airport,
    f.airline_code,
    f.aircraft_code,
    f.departure_metar_fk,
    f.arrival_taf_fk,
    f.departure_scheduled_utc,
    f.departure_actual_utc,
    f.departure_terminal,
    f.departure_gate,
    f.arrival_scheduled_utc,
    f.arrival_actual_utc,
    f.arrival_terminal,
    f.arrival_gate,
    f.status,
    f.status_final,
    f.delay_min,
    m.observation_time,
    m.station_id AS m_station_id,
    m.wind_dir_degrees,
    m.temp_c,
    m.dewpoint_c,
    m.wind_speed_kt,
    m.wind_gust_kt,
    m.visibility_statute_mi,
    m.altim_in_hg,
    m.sea_level_pressure_mb,
    m.flight_category,
    m.maxt_c,
    m.mint_c,
    m.metar_type,
    m.pcp3hr_in,
    m.pcp6hr_in,
    m.pcp24hr_in,
    m.precip_in,
    m.three_hr_pressure_tendency_mb,
    m.vert_vis_ft,
    m.wx_string,
    msc.sky_cover AS msc_sky_cover,
    mscr.description AS msc_sky_cover_description,
    msc.cloud_base_ft_agl AS msc_cloud_base_ft_agl,
    msc.cloud_type AS msc_cloud_type,
    t.station_id AS t_station_id,
    t.issue_time,
    t.bulletin_time,
    t.valid_time_from,
    t.valid_time_to,
    t.remarks,
    t.fcst_time_from,
    t.fcst_time_to,
    t.wind_dir_degrees AS t_wind_dir_degrees,
    t.wind_speed_kt AS t_wind_speed_kt,
    t.wind_gust_kt AS t_wind_gust_kt,
    t.visibility_statute_mi AS t_visibility_statute_mi,
    t.vert_vis_ft AS t_vert_vis_ft,
    t.wx_string AS t_wx_string,
    t.altim_in_hg AS t_altim_in_hg,
    t.change_indicator,
    t.probability,
    t.max_temp_c,
    t.min_temp_c,
    tsc.sky_cover AS tsc_sky_cover,
    tscr.description AS tsc_sky_cover_description,
    tsc.cloud_base_ft_agl AS tsc_cloud_base_ft_agl,
    tsc.cloud_type AS tsc_cloud_type
   FROM flight f
     LEFT JOIN metar m ON f.departure_metar_fk = m.id
     LEFT JOIN sky_condition msc ON msc.metar_fk = m.id AND msc.condition_order = 1
     LEFT JOIN sky_cover_reference mscr ON msc.sky_cover::text = mscr.code::text
     LEFT JOIN taf t ON f.arrival_taf_fk = t.id
     LEFT JOIN sky_condition tsc ON tsc.taf_fk = t.id AND tsc.condition_order = 1
     LEFT JOIN sky_cover_reference tscr ON tsc.sky_cover::text = tscr.code::text;

ALTER TABLE public."all"
    OWNER TO postgres;
