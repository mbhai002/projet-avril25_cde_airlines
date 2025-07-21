--select ST_AsGeoJSON(geom) AS geom from airports;

/*
CREATE EXTENSION Postgis;

ALTER TABLE AIRPORTS ADD geom GEOMETRY(Point, 4326);

UPDATE AIRPORTS SET  geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326);


CREATE OR REPLACE VIEW routes_geom AS
SELECT DISTINCT
    r.source_airport_iata || '-' || r.dest_airport_iata as id,
    ST_MakeLine(a1.geom, a2.geom)::geometry(LineString, 4326) AS geom
FROM
    routes r
JOIN
    airports a1 ON r.source_airport_id = a1.airport_id
JOIN
    airports a2 ON r.dest_airport_id = a2.airport_id;
*/
select * from routes_geom LIMIT 10

ALTER TABLE ROUTES ADD DIST FLOAT;

-----------------------------------
-- TABLES TECHNIQUES
-----------------------------------

--DROP TABLE API_SOURCE;
/* Referencement des api -> acces par un get dans les scripts */
CREATE TABLE API_SOURCE
(source_code VARCHAR(16),
 uri TEXT
);

DROP TABLE BATCH;

/* Referencement des batches de maj des données */
CREATE TABLE BATCH
(batch_code VARCHAR(16),
 batch_name TEXT,
 batch_vesion TEXT,
 last_batch_instance_id INTEGER,
 last_batch_instance_status CHAR(1),
 last_ref_batch_instance_id INTEGER, --cas d'un seul batch en dépendance 
 external_dependancy  CHAR(1) DEFAULT 'N',
 previous_occurrence_dependancy CHAR(1) DEFAULT 'N',
 enabled CHAR(1) DEFAULT 'N'
);

ALTER TABLE BATCH ADD CONSTRAINT PK_BATCH PRIMARY KEY (batch_code);

DROP TABLE BATCH_INSTANCE;

CREATE TABLE BATCH_INSTANCE
(batch_instance_id INTEGER,
 ref_batch_instance_id integer, --cas d'un seul batch en dépendance 
 batch_code VARCHAR(16),
 instance_begin date NOT NULL,
 instance_end date,
 instance_status CHAR(1), -- Exemple Status T: Terminé sans erreur, C: En cours, E: En erreur
 nb_insert integer DEFAULT 0,
 nb_updates integer DEFAULT 0,
 nb_api_calls integer DEFAULT 0,
 nb_custom integer DEFAULT 0
);

ALTER TABLE BATCH_INSTANCE ADD CONSTRAINT PK_BATCH_INSTANCE PRIMARY KEY (batch_instance_id);

ALTER TABLE BATCH_INSTANCE ADD CONSTRAINT FK_BATCH_INSTANCE_BATCH FOREIGN KEY (batch_code) REFERENCES BATCH(batch_code) ;

---------------------------------------------------------
-- TABLES DE DIMENSIONS
---------------------------------------------------------

/* Dimension Temps optionnel à ce stade : à alimenter avec un intervalles de dates */
--CREATE TABLE TIME_DATES(
--UTC_DATE date);

DROP TABLE TYPECODE;

CREATE TABLE TYPECODE 
(code_type CHAR(1),
 code_desc TEXT);

ALTER TABLE TYPECODE ADD CONSTRAINT PK_TYPECODE PRIMARY KEY (code_type);

insert into typecode(code_type, code_desc) values 
 ('A', 'Airport'),
 ('L', 'Airline'),
 ('C', 'Country'),
 ('P', 'Plane type'),
 ('E', 'Plane Engine'),
 ('R', 'Route'),
 ('F', 'Fligth'),
 ('M', 'Météo')
 ;
 
DROP TABLE COUNTRY;

CREATE TABLE COUNTRY (country_code VARCHAR(2), 
					  country_name TEXT NOT NULL,
					  creation_date date NOT NULL DEFAULT CURRENT_DATE,
	                  update_date date
);

ALTER TABLE COUNTRY ADD CONSTRAINT PK_COUNTRY PRIMARY KEY (country_code);

DROP TABLE IATA;

/* Les tables IATA et ICAO ainsi que COUNTRY sont les premières à alimenter pour garantir l'intégrité référentielle */

CREATE TABLE IATA (iata_code TEXT, code_type CHAR(1), CREATION_DATE DATE  DEFAULT CURRENT_DATE, UPDATE_DATE DATE, ACTIVE CHAR(1) NOT NULL DEFAULT 'O' );

ALTER TABLE IATA ADD CONSTRAINT PK_IATA PRIMARY KEY (iata_code, code_type);

ALTER TABLE IATA ADD CONSTRAINT IATA_FK_TYPE_CODE FOREIGN KEY (code_type) REFERENCES TYPECODE(code_type) ;

DROP TABLE ICAO;

CREATE TABLE ICAO (icao_code TEXT, code_type CHAR(1), CREATION_DATE DATE DEFAULT CURRENT_DATE, UPDATE_DATE DATE, ACTIVE CHAR(1) NOT NULL DEFAULT 'O' );

ALTER TABLE ICAO ADD CONSTRAINT PK_ICAO PRIMARY KEY (icao_code, code_type);

ALTER TABLE ICAO ADD CONSTRAINT ICAO_FK_TYPE_CODE FOREIGN KEY (code_type) REFERENCES TYPECODE(code_type) ;

DROP TABLE AIRLINE;

CREATE TABLE IF NOT EXISTS airline
(
    airline_id integer,
	creation_date date NOT NULL DEFAULT CURRENT_DATE,
	update_date date,
	code_type CHAR(1) NOT NULL DEFAULT 'L',
    name text NOT NULL,
    alias text,
    iata text,
    icao text,
    callsign text,
    country_code VARCHAR(2),
    active text,
    updatable CHAR(1) NOT NULL DEFAULT 'O'  -- pour protéger des enregistrements avec des valmeurs fausses dans les sources API	
)
TABLESPACE pg_default;


ALTER TABLE AIRLINE ADD CONSTRAINT PK_AIRLINE PRIMARY KEY (airline_id);

ALTER TABLE AIRLINE ADD CONSTRAINT AIRLINE_UNQ_CODE UNIQUE (code_type, iata, icao);

ALTER TABLE AIRLINE ADD CONSTRAINT AIRLINE_FK_IATA FOREIGN KEY (iata, code_type) REFERENCES ICAO(icao_code, code_type) ;

ALTER TABLE AIRLINE ADD CONSTRAINT AIRLINE_FK_ICAO FOREIGN KEY (icao, code_type) REFERENCES ICAO(icao_code, code_type) ;

ALTER TABLE AIRLINE ADD CONSTRAINT AIRLINE_FK_COUNTRY FOREIGN KEY (country_code) REFERENCES COUNTRY(country_code) ;

CREATE TABLE IF NOT EXISTS PLANE_TYPE
(
    plane_type_id INTEGER,
    code_type CHAR(1) DEFAULT 'P',
    typename text,
    iata text,
    icao text
)

TABLESPACE pg_default;

ALTER TABLE plane_type ADD CONSTRAINT PK_PLANE_TYPE PRIMARY KEY (plane_type_id);

ALTER TABLE plane_type ADD CONSTRAINT PLANE_TYPE_FK_IATA FOREIGN KEY (iata, code_type) REFERENCES ICAO(icao_code, code_type) ;

ALTER TABLE plane_type ADD CONSTRAINT PLANE_TYPE_FK_ICAO FOREIGN KEY (icao, code_type) REFERENCES ICAO(icao_code, code_type) ;

DROP TABLE AIRPORT;

CREATE TABLE IF NOT EXISTS AIRPORT
(
    airport_id integer,
	creation_date date NOT NULL DEFAULT CURRENT_DATE,
	update_date date,
	code_type CHAR(1) NOT NULL DEFAULT 'A',
    name text,
    city text,
    country_code varchar(2),
    iata text,
    icao text,
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    altitude integer,
    timezone text,
    dst text,
    tz text,
    airport_type text,
	updatable CHAR(1) NOT NULL DEFAULT 'O'  -- pour protéger des enregistrements avec des valmeurs fausses dans les sources API
    --,geom geometry(Point,4326)
)
TABLESPACE pg_default;

ALTER TABLE AIRPORT ADD CONSTRAINT PK_AIRPORT PRIMARY KEY (airport_id);

ALTER TABLE AIRPORT ADD CONSTRAINT AIRPORT_UNQ_CODE UNIQUE (code_type, iata, icao);

ALTER TABLE AIRPORT ADD CONSTRAINT AIRPORT_FK_IATA FOREIGN KEY (iata, code_type) REFERENCES ICAO(icao_code, code_type) ;

ALTER TABLE AIRPORT ADD CONSTRAINT AIRPORT_FK_ICAO FOREIGN KEY (icao, code_type) REFERENCES ICAO(icao_code, code_type) ;

ALTER TABLE AIRPORT ADD CONSTRAINT AIRPORT_FK_COUNTRY FOREIGN KEY (country_code) REFERENCES COUNTRY(country_code) ;

DROP TABLE AIRPORT_LINK;

/* Liaisons entre les aéroports  */
CREATE TABLE IF NOT EXISTS AIRPORT_LINK
(
	airport_link_id integer, --clé technique
	source_airport_id integer NOT NULL,
    dest_airport_id integer NOT NULL,
	creation_date date NOT NULL DEFAULT CURRENT_DATE,
	update_date date,
	dist float  -- distance à calculer entre source et destination
)
TABLESPACE pg_default;

ALTER TABLE AIRPORT_LINK ADD CONSTRAINT PK_AIRPORT_LINK PRIMARY KEY (airport_link_id);

ALTER TABLE AIRPORT_LINK ADD CONSTRAINT FK_SOURCE_AIRPORT FOREIGN KEY (source_airport_id) REFERENCES AIRPORT(airport_id) ;

ALTER TABLE AIRPORT_LINK ADD CONSTRAINT FK_DEST_AIRPORT FOREIGN KEY (dest_airport_id) REFERENCES AIRPORT(airport_id) ;

ALTER TABLE AIRPORT_LINK ADD CONSTRAINT UNQ_AIRPORT_LINK UNIQUE (source_airport_id, dest_airport_id);

/* La route commerciale correspond à l'association d'un lien entre aéroports et une compagnie */

DROP TABLE ROUTE;

CREATE TABLE IF NOT EXISTS ROUTE
(
	route_id integer, --clé technique
	airport_link_id integer, 
    airline_id integer,
	creation_date date NOT NULL DEFAULT CURRENT_DATE,
	update_date date,
	updatable CHAR(1) NOT NULL DEFAULT 'O'  -- pour protéger des enregistrements avec des valmeurs fausses dans les sources API
)
TABLESPACE pg_default;	

ALTER TABLE ROUTE ADD CONSTRAINT PK_ROUTE PRIMARY KEY (route_id);

ALTER TABLE ROUTE ADD CONSTRAINT FK_ROUTE_AIRPORT_LINK FOREIGN KEY (airport_link_id ) REFERENCES AIRPORT_LINK(airport_link_id) ;

ALTER TABLE ROUTE ADD CONSTRAINT FK_ROUTE_AIRLINE_LINK FOREIGN KEY (airline_id) REFERENCES AIRLINE(airline_id) ;

ALTER TABLE ROUTE ADD CONSTRAINT PK_ROUTE PRIMARY KEY (route_id);

ALTER TABLE ROUTE ADD CONSTRAINT FK_ROUTE_AIRPORT_LINK FOREIGN KEY (airport_link_id ) REFERENCES AIRPORT_LINK(airport_link_id) ;


DROP TABLE ROUTE_PLANES;

/* Table de jointure entre les liaisons commerciales et les types d'avions utilisés (plusieurs possibles pour certaines routes commerciales */
CREATE TABLE ROUTE_PLANES
(route_id integer,
plane_type_id integer)
TABLESPACE pg_default;	

ALTER TABLE ROUTE_PLANES ADD CONSTRAINT PK_ROUTE_PLANES PRIMARY KEY (route_id, plane_type_id)

DROP TABLE FLIGTH;
/* Le vol commercial correspond à une association de route et de date de vol */

CREATE TABLE IF NOT EXISTS FLIGTH
(
	flight_id integer, -- clé technique
	route_id integer NOT NULL,
	fligth_date_UTC date NOT NULL,
	local_fligth_date date,
	creation_date date NOT NULL DEFAULT CURRENT_DATE,
	update_date date
)
TABLESPACE pg_default;

ALTER TABLE FLIGTH ADD CONSTRAINT PK_FLIGTH PRIMARY KEY (flight_id);

ALTER TABLE FLIGTH ADD CONSTRAINT UNQ_FLIGTH UNIQUE(route_id, fligth_date_UTC);

ALTER TABLE FLIGTH ADD CONSTRAINT FK_FLIGTH_ROUTE FOREIGN KEY (route_id ) REFERENCES ROUTE(route_id) ;


---------------------------------------------------------
-- TABLES DE FAITS
---------------------------------------------------------

DROP TABLE METRIC;	

CREATE TABLE METRIC
(metric_ID integer,
 name TEXT,
 description TEXT,
 code_type CHAR(1),-- Pour les données de faits essentiellement 2 valurs M : météo, F: vols
 creation_date date NOT NULL DEFAULT CURRENT_DATE,
 update_date date,
 previsional CHAR(1) DEFAULT 'N', -- donnée prévisionnelle ML 'O'/'N'
 ML_metric CHAR(1) DEFAULT 'N' -- variable explicative du modèle ML 'O'/'N' pour la génération de scripts par exemple
);


ALTER TABLE METRIC ADD CONSTRAINT PK_METRIC PRIMARY KEY (metric_id);

ALTER TABLE METRIC ADD CONSTRAINT FK_METRIC_TYPE FOREIGN KEY (code_type) REFERENCES TYPECODE(code_type) ;


/*
En fonction du code_type une colonne parmi les clés étrangères est renseignée
Ceci concerne essentiellement:
- Le trafic horaire des aéroprts (code_type = 'A'), nombre de vols quotidiens, nombre de départs et d'arrivées
- Les horaires de vols effectifs et planifiés (code_type = 'F'), les retards
Accessoirement
Les engins de vols ou le nombre, l'age moyen des avions par pays, par compagnies ou par aeroport
*/
CREATE TABLE METRIC_INSTANCE -- table de FAITS
(metric_ID integer NOT NULL,
 country_id integer,
 airport_id integer,
 airline_id integer,
 plane_type_id integer,
 fligth_id integer,
 creation_date date NOT NULL DEFAULT CURRENT_DATE,
 measure_utc_timestamp timestamp, --timmestamp effectif de la mesure
 measure_utc_date DATE not null, --facultatif pour la jointure avec TIME_DATES -> utilité de purge et partitionnement des données (pour archivage/purges/performances) en forte volumétrie
 metric_value TEXT,
 batch_instance_id INTEGER, -- permet un lien entre les mesures (également pour les type_codes différents de type M et M)
 /*  ref_batch_instance_id INTEGER, 

 Si la météo et les vols sont collectés dans les batches disticts, les collectes météos pouvant dépendantes des horais de vols 
 l'instance du batch de maj des vols pourra être référencé ici, batch_instance_id identifiant l'instance de la météo
 A voir s'il est préférable de créer une colonne refmetric_id avec une autojointure ou une table de jointure des instances de batches dépendants (mieux) ou intégrer le ref_batch_id dans BATCH_INSTANCE
 -> voir les actions en cas de plantage en cours de mise à jour, les traitement des rejets, des alertes etc
 */
 prevision_utc_timestamp timestamp -- pour les évaluations prévisionnelles la date pour laquelle est faite la prévison
 );
 

ALTER TABLE METRIC_INSTANCE ADD CONSTRAINT FK_METRIC_INSTANCE_METRIC FOREIGN KEY (metric_id) REFERENCES METRIC(metric_id) ;

ALTER TABLE METRIC_INSTANCE ADD CONSTRAINT FK_METRIC_INSTANCE_BATCH FOREIGN KEY (batch_instance_id) REFERENCES BATCH_INSTANCE(batch_instance_id) ;

ALTER TABLE METRIC_INSTANCE ADD CONSTRAINT CC_ID_NOT_NULL CHECK (country_id IS NOT NULL OR airport_id IS NOT NULL OR airline_id IS NOT NULL OR fligth_id IS NOT NULL) ;



/* Pour tenir compte des evénements locaux pouvant perturber les horaires exemple congés et mouvements sociaux */

CREATE TABLE  EXTERNAL_EVENT(
event_id INTEGER,
event_name TEXT,
code_type CHAR(1));

ALTER TABLE EXTERNAL_EVENT ADD CONSTRAINT PK_EXTERNAL_EVENT PRIMARY KEY (event_id);

ALTER TABLE EXTERNAL_EVENT ADD CONSTRAINT FK_EXTEVENT_TYPE FOREIGN KEY (code_type) REFERENCES TYPECODE(code_type) ;


CREATE TABLE EVENT_INSTANCE (
 event_id integer,
 creation_date date,
 airport_id integer,
 country_id integer,
 airline_id integer,
 begin_date date NOT NULL,
 end_date date
);

ALTER TABLE EVENT_INSTANCE ADD CONSTRAINT PK_EVENT_INSTANCE PRIMARY KEY (event_id, creation_date);

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



