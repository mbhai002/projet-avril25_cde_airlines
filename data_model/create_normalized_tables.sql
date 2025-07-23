
/* Une premère étape serait de définir les volumes disques/tablespaces utilisés c'est un paramétrage technique non abordé ici - toute segment de données (table ou index) doit normalement être associé à un tablespace */
/* Les index ne sont pas traités à ce stade */
/* Il pourrait aussi être utile de créer des schémas pour regrouper les tables */

-----------------------------------
-- TABLES TECHNIQUES
-----------------------------------

--DROP TABLE API_SOURCE;
/* Referencement des api -> acces par un get dans les scripts */
CREATE TABLE API_SOURCE
(source_code VARCHAR(16),
 uri TEXT
);

--DROP TABLE BATCH;

/* Referencement des batches de maj des données : ce sont des tables hors de l'application  facultatives mais utiles en exploitation pour suivre la chronologie des traitemts 
   Il existe également d'autres outils de suivi des traitements
*/

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

--DROP TABLE BATCH_INSTANCE;

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

/* Dans la plupart des cas, il est utile de connaître la date (généralementy locale de création (creation_date) de la donnée et la date de sa dernière modification (update_date) pour chaque ligne de la table */

--CREATE TABLE TIME_DATES(
--UTC_DATE date);

--DROP TABLE TYPECODE;

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
 
--DROP TABLE COUNTRY;

CREATE TABLE COUNTRY (country_code VARCHAR(2), 
					  country_name TEXT NOT NULL,
					  creation_date date NOT NULL DEFAULT CURRENT_DATE,
	                  update_date date
);

ALTER TABLE COUNTRY ADD CONSTRAINT PK_COUNTRY PRIMARY KEY (country_code);

--DROP TABLE IATA;

/* Au vue du contenu des fichiers csv, Les tables IATA et ICAO ainsi que COUNTRY sont les premières à alimenter pour garantir l'intégrité référentielle */

CREATE TABLE IATA (iata_code TEXT, code_type CHAR(1), CREATION_DATE DATE  DEFAULT CURRENT_DATE, UPDATE_DATE DATE, ACTIVE CHAR(1) NOT NULL DEFAULT 'O' );

ALTER TABLE IATA ADD CONSTRAINT PK_IATA PRIMARY KEY (iata_code, code_type);

ALTER TABLE IATA ADD CONSTRAINT IATA_FK_TYPE_CODE FOREIGN KEY (code_type) REFERENCES TYPECODE(code_type) ;

--DROP TABLE ICAO;

CREATE TABLE ICAO (icao_code TEXT, code_type CHAR(1), CREATION_DATE DATE DEFAULT CURRENT_DATE, UPDATE_DATE DATE, ACTIVE CHAR(1) NOT NULL DEFAULT 'O' );

ALTER TABLE ICAO ADD CONSTRAINT PK_ICAO PRIMARY KEY (icao_code, code_type);

ALTER TABLE ICAO ADD CONSTRAINT ICAO_FK_TYPE_CODE FOREIGN KEY (code_type) REFERENCES TYPECODE(code_type) ;

--DROP TABLE AIRLINE;

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

/* Table de jointure entre les liaisons commerciales et les types d'avions utilisés (plusieurs possibles pour certaines routes commerciales) - Cette table n'est pas essentielle, mais l'information est disponible dans certains fichiers */

CREATE TABLE ROUTE_PLANES
(route_id integer,
plane_type_id integer)
TABLESPACE pg_default;	

ALTER TABLE ROUTE_PLANES ADD CONSTRAINT PK_ROUTE_PLANES PRIMARY KEY (route_id, plane_type_id)

--DROP TABLE FLIGTH;
/* Le vol commercial correspond à une association de route et de date de vol */

CREATE TABLE IF NOT EXISTS FLIGTH
(
	fligth_id integer, -- clé technique
	route_id integer NOT NULL,
	fligth_date_UTC date NOT NULL,
	local_fligth_date date,
	creation_date date NOT NULL DEFAULT CURRENT_DATE,
	update_date date
)
TABLESPACE pg_default;

ALTER TABLE FLIGTH ADD CONSTRAINT PK_FLIGTH PRIMARY KEY (fligth_id);

ALTER TABLE FLIGTH ADD CONSTRAINT UNQ_FLIGTH UNIQUE(route_id, fligth_date_UTC);

ALTER TABLE FLIGTH ADD CONSTRAINT FK_FLIGTH_ROUTE FOREIGN KEY (route_id ) REFERENCES ROUTE(route_id) ;

--DROP TABLE PLANE_TYPE_STATS;
/* Selon que la donnée se rapporte à une compagnie, un pays ou un modèle d'avion country_id ou airline_id est rensignée on pourrait aussi créer une table par catégorie */
CREATE TABLE PLANE_TYPE_STATS(
plane_stat_id integer,
plane_type_id integer NOT NULL,
creation_date date NOT NULL DEFAULT CURRENT_DATE,
aggregate_date date NOT NULL, 
country_code VARCHAR(2),
airline_id integer,
total_count integer NOT NULL,
average_age float NOT NULL)
TABLESPACE pg_default;

ALTER TABLE PLANE_TYPE_STATS ADD CONSTRAINT PK_PLANE_TYPE_STATS PRIMARY KEY (plane_stat_id);

ALTER TABLE PLANE_TYPE_STATS ADD CONSTRAINT FK_PLANE_TYPE_STATS_TYPE FOREIGN KEY (plane_type_id ) REFERENCES PLANE_TYPE(plane_type_id) ;

ALTER TABLE PLANE_TYPE_STATS ADD CONSTRAINT FK_PLANE_TYPE_STATS_COUNTRY FOREIGN KEY (country_code) REFERENCES COUNTRY(country_code) ;

ALTER TABLE PLANE_TYPE_STATS ADD CONSTRAINT FK_PLANE_TYPE_STATS_AIRLINE FOREIGN KEY (airline_id ) REFERENCES AIRLINE(airline_id) ;

--DROP TABLE METRIC;	

/* La création d'une mesure (métrique) correspond à l'ajout d'une ligne dans la table METRIC qui définit la donnée collectée */
/* Cette table est plutôt une table de métadonnées qu'une véritable dimension mais elle est dépendante de l'application contrairement aux tables techniques pures*/
CREATE TABLE METRIC
(metric_ID integer,
 name TEXT,
 description TEXT,
 code_type CHAR(1),-- Pour les données de faits essentiellement 2 valurs M : météo, F: vols
 creation_date date NOT NULL DEFAULT CURRENT_DATE,
 update_date date,
 previsional CHAR(1) DEFAULT 'N', -- donnée prévisionnelle ML 'O'/'N'
 ML_metric CHAR(1) DEFAULT 'N' -- variable explicative du modèle ML 'O'/'N' pour la génération de scripts par exemple
)
TABLESPACE pg_default;

ALTER TABLE METRIC ADD CONSTRAINT PK_METRIC PRIMARY KEY (metric_id);

ALTER TABLE METRIC ADD CONSTRAINT FK_METRIC_TYPE FOREIGN KEY (code_type) REFERENCES TYPECODE(code_type) ;


---------------------------------------------------------
-- TABLES DE FAITS
---------------------------------------------------------

/*
Si une mesure a une valeur fixe dans le temps (comme la logueur d'une route ou l'altitude d'un aéroport à quelques mètres près) la métrique n'est pas un fait mais peut être intégrée dans la table de référence associée au code_type (dimension), ce n'est plus un fait (ce qui ne signifie pas que l'information n'intervient pas dans le modèle ML)
Il peut être commode d'associer systématiquement la création d'une métrique <name> à l'ajout de 2 colonnes dans la table de dimension associée : last_<name>_vale et lest_<name>_date

Pour chaque mesure dans le temps une ligne est ajoutée à la table METRIC_INSTANCE liée à une métrique (PK = metric_id) et à un timestamp UTC qui correspond au moment de la mesure measure_utc_timestamp (à défaut creation_date si cette information n'est pas accessible ou n'est pas utile)

En fonction de la catégorie de la métrique, l'identifiant (country_id, airport_id integer, airline_id integer, plane_type_id integer ou fligth_id) est associé à  chaque mesure

Ceci pourrait concerner notamment:

- Le trafic horaire des aéroprts (code_type = 'A'), nombre de vols quotidiens, nombre de départs et d'arrivées
- Les horaires de vols effectifs et planifiés (code_type = 'F'), les retards
- des relevés météo crrespondant aux localisations des aéroports
Accessoirement
Les engins de vols ou le nombre, l'age moyen des avions par pays, par compagnies ou par aeroport
*/

CREATE TABLE METRIC_INSTANCE -- table de FAITS
/* il est important ici de prévoire une date utc ou Linux pour s'affranchir des décalages de fuseaux horaires, changements d'heures locals qui compliquent notamment le calcul des durées de vol */
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
 batch_instance_id INTEGER, -- permet un lien entre les mesures (également pour les type_codes différents de type F et M/A)
 /*  
 ref_batch_instance_id INTEGER, 
   Si la météo et les vols sont collectés dans les batches disticts, les collectes météos pouvant dépendantes des horais de vols 
   l'instance du batch de maj des vols pourra être référencé ici, batch_instance_id identifiant l'instance de la météo
   A voir s'il est préférable de créer une colonne refmetric_id avec une autojointure ou une table de jointure des instances de batches dépendants (mieux) ou intégrer le ref_batch_id dans BATCH_INSTANCE
 -> voir les actions en cas de plantage en cours de mise à jour, les traitement des rejets, des alertes etc
 */
 prevision_utc_timestamp timestamp -- pour les évaluations prévisionnelles la date pour laquelle est faite la prévison
 )
 TABLESPACE pg_default;
 
ALTER TABLE METRIC_INSTANCE ADD CONSTRAINT FK_METRIC_INSTANCE_METRIC FOREIGN KEY metric_id REFERENCES METRIC(metric_id) ;

ALTER TABLE METRIC_INSTANCE ADD CONSTRAINT FK_METRIC_INSTANCE_BATCH FOREIGN KEY batch_instance_id REFERENCES BATCH_INSTANCE(batch_instance_id) ;

/* Les contraites référentielles avec les tables METRIC, AIRPORT, AIRLINE, PLANE_TYPE, FLIGHT sont à ajoutées si ce modèle est retenu */

/* Si METRIC_INSTANCE n'est pas retenu */
--DROP TABLE AIRPORT_METEO_METRIC
CREATE TABLE AIRPORT_METEO_METRIC(
airport_meteo_Id integer,
creation_date date NOT NULL DEFAULT CURRENT_DATE,
--update_date date,
airport_id integer NOT NULL,
metric_id integer NOT NULL,
metric_value text -- ou numérique
)
TABLESPACE pg_default;

ALTER TABLE AIRPORT_METEO_METRIC ADD CONSTRAINT PK_AIRPORT_METEO_METRIC PRIMARY KEY (airport_meteo_id);
ALTER TABLE AIRPORT_METEO_METRIC ADD CONSTRAINT FK_AIRPORT_METEO_METRIC_AIRPORT FOREIGN KEY (airport_id) REFERENCES AIRPORT(airport_id);
ALTER TABLE AIRPORT_METEO_METRIC ADD CONSTRAINT FK_AIRPORT_METEO_METRIC_METRIC FOREIGN KEY (metric_id) REFERENCES METRIC(metric_id);

CREATE TABLE FLIGTH_AIRPORTS_METEOS(
fligth_id integer, -- -> fligth a déjà le lien avec route qui fournit airlines_id et airportlink_id et airportl_ink_id donnne accès à source_aiport_id et dest_airport_id qui permettent la jointure avec AEROPORT_METEO
airport_meteo_id integer,
airport_fligth_type CHAR(1) NOT NULL, -- 'S' pour aeroport source, 'D' pour aéroport destination (on pourait envisager 'E' pour une escale, mais il faudrait aussi une nouvelle association FLIGHT - AIRPORT pour introduire le concept)
creation_date date NOT NULL DEFAULT CURRENT_DATE,
distance_horaire_meteo integer DEFAULT 0,
decalage_distance_horaire integer DEFAULT 0
)
TABLESPACE pg_default;

/*
Plusieurs approches sont possibles qui peuvent modifier le choix du modèle de données:

- Collecter les données météo et vols dans le même processus avec un timestamp ou un identifiant de prcessus qui permet de lier ces données en quel cas la table AIRPORT_METEO_METRIC n'est pas nécessaire (les multiples informations étant directement injectées dans la table FLIGTH)
  mais cela peut retarder le processus en mettant des dépendances entre les appels API (on peut aussi extraire un fichier d'horaires et aéoroports une fois passé les extractions de vols qui permettre une extraction météo groupée)
  Danc ce cas de figure, on peut avoir distance_horaire_source_meteo=0 et distance_horaire_meteo=0 (colonne expliquée ci-après)
- Collecter les données météo et vols dans des processus asynchrones. Dans ce cas, il y a plus de données météo collectées par aéroport et il faut lier le vol à l'horaire le plus proche disponible au départ et à l'arrivée
  d'où la notion de distance horaire collectée. 
- Enfin, il est possible lier les données vol et météo à H, H-1, H-3, H+1, H+3 pour les prévisions météo par exemple.... Dans ce cas il faut introduire dans la clé primaire de  FLIGTH_AIRPORTS_METEOS 
  la colonne decalage_distance_horaire 

L'introduction de measure_instance_id liée à la table MEASURE_INSTANCE donne un contrôle très précis de l'intégrité des métriques mais plus de lignes dans la table, on a pouussé là la normalisation à l'extrême.
Pour simplifier la lecture des données et la compréhension du modèle, on peut mettre en dur des colonnes comme vitesse du vent, température, visibilité etc... directement dans la table AEROPORT_METEO
La table METRIC a intérêt à être maintenue pour constituer un dictionnaire de mesures, en revanche METRIC_INSTANCE a beaucoup moins d'intérêt dans ce dernier cas (mais elle peut servir pour d'autres besoins)
*/

ALTER TABLE FLIGTH_AIRPORTS_METEOS ADD CONSTRAINT PK_FLIGTH_AIRPORTS_METEOS PRIMARY KEY (fligth_id, airport_meteo_id, airport_fligth_type);
ALTER TABLE FLIGTH_AIRPORTS_METEOS ADD CONSTRAINT FLIGTH_AIRPORTS_METEOS PRIMARY KEY (mairport_id);
ALTER TABLE FLIGTH_AIRPORTS_METEOS ADD CONSTRAINT AIRPORT_METEO_METRIC_METRIC PRIMARY KEY (metric_id);
ALTER TABLE FLIGTH_AIRPORTS_METEOS ADD CONSTRAINT CC_FLIGTH_AIRPORTS_METEOS CHECK airport_fligth_type in ('S', 'D');

/* Une idée pour tenir compte des evénements locaux pouvant perturber les horaires exemple périodes congés/forte affluence ou mouvements sociaux des personnels au sol/navigants */
CREATE TABLE  EXTERNAL_EVENT(
event_id INTEGER,
event_name TEXT,
code_type CHAR(1));

ALTER TABLE EXTERNAL_EVENT ADD CONSTRAINT PK_EXTERNAL_EVENT PRIMARY KEY (event_id);

ALTER TABLE EXTERNAL_EVENT ADD CONSTRAINT FK_EXTEVENT_TYPE FOREIGN KEY (code_type) REFERENCES TYPECODE(code_type) ;

/* Selon que l'évènement touche un aéroport, une compagnie spécifique ou un pays entier la colonne airport_id, airline_id ou country_id est renseignée */
CREATE TABLE EVENT_INSTANCE (
 event_id integer,
 creation_date date,
 airport_id integer,
 country_id integer,
 airline_id integer,
 begin_date date NOT NULL,
 end_date date
);

/* Les contraites référentielles avec les tables COUNTRY, AIRPORT, AIRLINE sont à ajouter si ce modèle est retenu */

ALTER TABLE EVENT_INSTANCE ADD CONSTRAINT PK_EVENT_INSTANCE PRIMARY KEY (event_id, creation_date);

ALTER TABLE EVENT_INSTANCE ADD CONSTRAINT EVENT_INSTANCE_PK FOREIGN KEY (envent_id) REFERENCES EXTERNAL_EVENT(event_id) ;
