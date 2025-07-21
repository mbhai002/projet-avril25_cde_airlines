La création d'une métrique  consiste à mettre en place une mesure dans l'écosystème "Ailines" qui va extraire une série temporelle d'informations (faits).

La première étape est une catégorisation de la mesure en introdisant une table de types d'information, en voici un exemple :

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

Cette création de métrique correspond à l'ajout d'une ligne dans la table METRIC qui définit la donnée collectée:

CREATE TABLE METRIC
(metric_ID integer,
 name TEXT,
 description TEXT,
 code_type CHAR(1),-- Pour les données de faits essentiellement 2 valeurs M : météo, F: vols
 creation_date date NOT NULL DEFAULT CURRENT_DATE,
 update_date date,
 previsional CHAR(1) DEFAULT 'N', -- donnée prévisionnelle ML 'O'/'N'
 ML_metric CHAR(1) DEFAULT 'N' -- variable explicative du modèle ML 'O'/'N' pour la génération de scripts par exemple
);

Si une mesure a une valeur fixe dans le temps (comme la logueur d'une route ou l'altitude d'un aéroport à quelques mètres près) la métrique n'est pas un fait mais peut être intégrée dans la table de référence associée au code_type (dimension), ce n'est plus un fait (ce qui ne signifie pas que l'information n'intervient pas dans le modèle ML)
Il peut être commode d'associer systématiquement la création d'une métrique <name> à l'ajout de 2 colonnes dans la table de dimension associée : last_<name>_vale et lest_<name>_date

Pour chaque mesure dans le temps une ligne est ajoutée à la table METRIC_INSTANCE liée à une métrique (PK = metric_id) et à un timestamp UTC qui correspond au moment de la mesure measure_utc_timestamp (à défaut creation_date si cette information n'est pas accessible ou n'est pas utile)

En fonction de la catégorie de la métrique, l'identifiant (country_id, airport_id integer, airline_id integer, plane_type_id integer ou fligth_id) est associé à  chaque mesure dans :

CREATE TABLE METRIC_INSTANCE -- table de FAITS
(metric_ID integer NOT NULL,
 country_id integer,
 airport_id integer,
 airline_id integer,
 plane_type_id integer,
 fligth_id integer,
 creation_date date NOT NULL DEFAULT CURRENT_DATE,
 measure_utc_timestamp timestamp not null, --timmestamp effectif de la mesure
 measure_utc_date DATE NOT NULL, --facultatif pour la jointure avec TIME_DATES -> utilité de purge et partitionnement des données (pour archivage/purges/performances) en forte volumétrie
 metric_value TEXT,
 batch_instance_id INTEGER, -- permet un lien entre les mesures et le processus d'alimentation (batch) associé
 /*  ref_batch_instance_id INTEGER, -- les mises à jour des valeurs de différentes métriques peuvent être associées à des processus de maj différents (particulièement pour les type_codes différents de      type M et F, le choix des horaires des collectes de données météos locales pouvant par exemple être dépendante des horaires de vols. Le plus simple est de créer un seul processus
     En cas contraire, l'instance du batch de maj des vols pourra être référencé ici dans ref_batch_instance_id, batch_instance_id identifiant l'instance de la météo
     -> voir les actions en cas de plantage en cours de mise à jour, les traitement des rejets, des alertes etc
 */
 prevision_utc_timestamp timestamp -- pour les évaluations prévisionnelles la date pour laquelle est faite la prévison
 );

Des tables de jointure comme PLANE_TYPE_COUNTRY renfermant par exemple le nombre ou l'âge des avions par pays avec une mise à jour annuelle ne necessite pas la mise en place d'une métrique mais l'information pourra être récupérée dans le modèle ML si elle est utile.