CREATE EXTENSION Postgis;

ALTER TABLE AIRPORTs_OPENFLIGTHS ADD geom GEOMETRY(Point, 4326);

UPDATE AIRPORTs_OPENFLIGTHS SET  geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326);

-- Calcul et maj des distances associées aux routes

ALTER TABLE ROUTEs_OPENFLIGTHS ADD DIST FLOAT;

WITH s AS (
  SELECT
    a1.longitude AS source_longitude,
    a1.latitude AS source_latitude,
    a2.longitude AS dest_longitude,
    a2.latitude AS dest_latitude,
    r.airline_iata,
    r.source_airport_iata,
    r.dest_airport_iata
  FROM routes r
  JOIN airports a1 ON a1.airport_id = r.source_airport_id
  JOIN airports a2 ON a2.airport_id = r.dest_airport_id
)
UPDATE routes_OPENFLIGTHS r
SET dist = ST_DistanceSphere(
  ST_MakePoint(s.source_longitude, s.source_latitude),
  ST_MakePoint(s.dest_longitude, s.dest_latitude)
)
FROM s
WHERE
  r.airline_iata = s.airline_iata AND
  r.source_airport_iata = s.source_airport_iata AND
  r.dest_airport_iata = s.dest_airport_iata;

-----------------------------------------------
--Tests


-- routes sans distance associée
select sum(case when dist is null then 1 else 0 end) AS nb_null_dist, sum(case when dist is null then 0 else 1 end) AS nb_not_null_dist FROM routes_OPENFLIGTHS;

/*
892 | 66771
*/

---
-- nombre de paires d'aérorpots  liés
select count(1) from (
select distinct src, dest from (
select dest_airport_iata as src, source_airport_iata dest from routes_OPENFLIGTHS 
union  
select source_airport_iata as src, dest_airport_iata as dest from routes_OPENFLIGTHS) s 
)s; --38513

-- nombre d'allers sans retour associé
select count(1) from (
select source_airport_iata , dest_airport_iata from routes_OPENFLIGTHS
except
select dest_airport_iata , source_airport_iata from routes_OPENFLIGTHS) s; --918

-- nombre de retours sans allé associé
select count(1) from (
select dest_airport_iata , source_airport_iata from routes_OPENFLIGTHS
except
select source_airport_iata , dest_airport_iata from routes_OPENFLIGTHS) s;  --918

-- nombre de routes distinctes
select count(distinct(dest_airport_iata, source_airport_iata)) from routes_OPENFLIGTHS;  --37595
--OU
select count(1) from (
select distinct src, dest from (
select dest_airport_iata as src, source_airport_iata dest from routes_OPENFLIGTHS )s
)s; --37595

--nombre d'aéroports liés
select count(1) from (
select distinct src, dest from (
select dest_airport_iata as src, source_airport_iata dest from routes 
union  
select source_airport_iata as src, dest_airport_iata as dest from routes) s 
)s; --38513

-- Aéroports de distance = 0
select * from routes_OPENFLIGTHS where dist=0
/*
"IL"	10121	"PKN"	3910	"PKN"	3910		0	"AT7"	0
*/

select min(round(dist/1000)), max(round(dist/1000)) from routes_OPENFLIGTHS where dist > 0;
/*
3	16082
*/


select * from routes_OPENFLIGTHS where dist=(select min(dist) from routes where dist>0)
/*
"LM"	3287	"PPW"	5567	"WRY"	5571		0	"BNI"	2822.66363189
"LM"	3287	"WRY"	5571	"PPW"	5567		0	"BNI"	2822.66363189
*/


select a.* from airports_OPENFLIGTHS a 
where iata in ('WRY', 'PPW');
/*
5567	"Papa Westray Airport"	"Papa Westray"	"United Kingdom"	"PPW"	"EGEP"	59.351699829100006	-2.9002799987800003	91	"0"	"E"	"Europe/London"	"airport"
5571	"Westray Airport"	    "Westray"	    "United Kingdom"	"WRY"	"EGEW"	59.3502998352	    -2.95000004768	    29	"0"	"E"	"Europe/London"	"airport"
*/

-- routes de tailles extrêmes pour Roissy Charles de G
select min(round(dist/1000)), max(round(dist/1000)) from routes_OPENFLIGTHS where source_airport_iata='CDG' and dist > 0
/*
251 | 11674
*/


select r.* , round(dist/1000) dkm from routes_OPENFLIGTHS R where dest_airport_iata='PLU' order by dist desc --source_airport_iata

select * from airports_OPENFLIGTHS where iata in ('PLU', 'VDC')

select * from routes_OPENFLIGTHS where dist=(select max(dist) from routes_OPENFLIGTHS)
/*
"P0"	4066	"LUN"	907	   "SLI"	5613		0	"J32 J41"	16082277.34108066
"P0"	4066	"SLI"	5613	   "LUN"	907		    0	"J32 J41"	16082277.34108066
*/
select * from airports_OPENFLIGTHS where airport_id in (5613, 907)
/*
907	"Kenneth Kaunda International Airport Lusaka"	"Lusaka"	"Zambia"	"LUN"	"FLLS"	-15.3308000565	28.4526004791	3779	"2"	"U"	"Africa/Lusaka"	"airport"	"OurAirports"
5613	"Los Alamitos Army Air Field"	"Solwesi"	"Zambia"	"\N"	"KSLI"	33.79000092	-118.052002	32	"-8"	"U"	"America/Los_Angeles"	"airport"	"OurAirports"
*/

select * from airlines where airline_id=4066

select r.*, round(dist/1000) from routes_OPENFLIGTHS r where dist is not null and stops > 0 order by dist desc limit 100

select * from airports_OPENFLIGTHS where airport_id in (4089, 3361) 
select * from routes_OPENFLIGTHS where source_airport_id=4066 and dest_airport_id=907


---
-- routes de distance = 0
select * from routes_OPENFLIGTHS where dist=0
/*
"IL"	10121	"PKN"	3910	"PKN"	3910		0	"AT7"	0
*/

-- route la plus longue 
select min(round(dist/1000)), max(round(dist/1000)) from routes_OPENFLIGTHS where dist > 0;
/*
3	16082
*/

-- route la plus courte -> cas vérifié
select * from routes_OPENFLIGTHS where dist=(select min(dist) from routes where dist>0)
/*
"LM"	3287	"PPW"	5567	"WRY"	5571		0	"BNI"	2822.66363189
"LM"	3287	"WRY"	5571	"PPW"	5567		0	"BNI"	2822.66363189
*/


select a.* from airports_OPENFLIGTHS a 
where iata in ('WRY', 'PPW');
/*
5567	"Papa Westray Airport"	"Papa Westray"	"United Kingdom"	"PPW"	"EGEP"	59.351699829100006	-2.9002799987800003	91	"0"	"E"	"Europe/London"	"airport"
5571	"Westray Airport"	    "Westray"	    "United Kingdom"	"WRY"	"EGEW"	59.3502998352	    -2.95000004768	    29	"0"	"E"	"Europe/London"	"airport"
*/

-- route la plus longue
select * from routes_OPENFLIGTHS where dist=(select max(dist) from routes)
/*
"P0"	4066	"LUN"	907	   "SLI"	5613		0	"J32 J41"	16082277.34108066
"P0"	4066	"SLI"	5613	"LUN"	907		    0	"J32 J41"	16082277.34108066
*/
select * from airports_OPENFLIGTHS where airport_id in (5613, 907)
/*
907	"Kenneth Kaunda International Airport Lusaka"	"Lusaka"	"Zambia"	"LUN"	"FLLS"	-15.3308000565	28.4526004791	3779	"2"	"U"	"Africa/Lusaka"	        "airport"	"OurAirports"
5613	"Los Alamitos Army Air Field"	           "Solwesi"	"Zambia"	"\N"	"KSLI"	33.79000092	-118.052002	        32	   "-8"	"U"	"America/Los_Angeles"	"airport"	"OurAirports"
-- Le nom et la localisation de l'aéroport 5613 sont faux -> "Solwesi Airport",-12.173700332641602,26.365100860595703
*/

select * from airlines_OPENFLIGTHS where airline_id=4066
*/
4066	"Proflight Commuter Services"	"\N"	"P0"			"Zambia"	"Y"
*/

-- routes les plus courtes et plus longues (km) à partir de Charles de Gaulle 
select min(round(dist/1000)), max(round(dist/1000)) from routes_OPENFLIGTHS where source_airport_iata='CDG' and dist > 0
/*
251 | 11674
*/

--Creations des arêtes du graphe (visualisation des liaisons entre aéroports)
--------------------------------

CREATE OR REPLACE VIEW routes_OPENFLIGTHS_geom AS
SELECT DISTINCT
    r.source_airport_iata || '-' || r.dest_airport_iata as id,
    ST_MakeLine(a1.geom, a2.geom)::geometry(LineString, 4326) AS geom
FROM
    routes_OPENFLIGTHS r
JOIN
    airports a1 ON r.source_airport_id = a1.airport_id
JOIN
    airports a2 ON r.dest_airport_id = a2.airport_id;

--------------------------------------------------------------------------------------------------------------------------------

ALTER TABLE AIRPORTs_OURAIRPORTS ADD geom GEOMETRY(Point, 4326);

UPDATE AIRPORTs_OURAIRPORTS SET  geom = ST_SetSRID(ST_MakePoint(longitude_deg, latitude_deg), 4326);
                        
