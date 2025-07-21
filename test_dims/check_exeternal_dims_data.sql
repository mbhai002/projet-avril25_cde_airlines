
/* Nombre de lignes par TABLE*/

SELECT 'AIRPORTS', COUNT(1) as cnt FROM AIRPORTS_OPENFLIGHTS
UNION ALL
SELECT 'AIRLINES', COUNT(1) as cnt FROM AIRLINES_OPENFLIGHTS
UNION ALL
SELECT 'PLANES', COUNT(1) as cnt FROM PLANES_OPENFLIGHTS
UNION ALL
SELECT 'ROUTES_TEXT', COUNT(1) as cnt FROM ROUTES_TEXT_OPENFLIGHTS  -- La table ROUTES_TEXT est introduite car des valeurs \N sont présentes dans le fichier téléchargé pour une colonne numérique, ces valeurs sont transformées en null dans la table ROUTES
UNION ALL
SELECT 'ROUTES', COUNT(1) as cnt FROM ROUTES_OPENFLIGHTS;


/*
 PLANES      |   246
 AIRLINES    |  6162
 AIRPORTS    |  7698
 ROUTES      | 67663
 ROUTES_TEXT | 67663
*/

----------------------------------------------------------------------------
-- ROUTES
----------------------------------------------------------------------------

/* Décompte des colonnes nulles de routes */
 
SELECT 
COUNT(1) as total_routes, --67663
SUM(CASE WHEN airline_iata IS NULL THEN 1 ELSE 0 END) as airline_iata_null_count,  --0
SUM(CASE WHEN airline_id IS NULL THEN 1 ELSE 0 END) as airline_id_null_count,  --479
SUM(CASE WHEN source_airport_iata IS NULL THEN 1 ELSE 0 END) as source_airport_iata_null_count,  --0
SUM(CASE WHEN source_airport_id IS NULL THEN 1 ELSE 0 END) as source_airport_id_null_count,  --220
SUM(CASE WHEN dest_airport_iata IS NULL THEN 1 ELSE 0 END) as dest_airport_iata_null_count,  --0
SUM(CASE WHEN dest_airport_id IS NULL THEN 1 ELSE 0 END) as dest_airport_id_null_count,  --221
SUM(CASE WHEN shared IS NULL THEN 1 ELSE 0 END) as shared_null_count,  --53056
SUM(CASE WHEN stops IS NULL THEN 1 ELSE 0 END) as stops_null_count,  --0
SUM(CASE WHEN equipments IS NULL THEN 1 ELSE 0 END) as equipments_null_count  --18
FROM routes_OPENFLIGHTS;

/* Unicité dans routes */

SELECT count(1) as nb, airline_iata, source_airport_iata, dest_airport_iata
FROM routes_OPENFLIGHTS
GROUP BY airline_iata, source_airport_iata, dest_airport_iata 
HAVING count(1) > 1
ORDER BY 1 desc;

--> airline_iata, source_airport_iata, dest_airport_iata  est une clé unique de routes 

-- Vérification d'une valeur de routes.equipments

select * from routes_OPENFLIGHTS where equipments='738 73W 73H 73C'
/*
 WN           |       4547 | TPA                 |              3646 | HOU               |            3566 |        |     0 | 738 73W 73H 73C
 -- une seule route avec cette valeur
*/

select * from planes_OPENFLIGHTS where iata in ('738', '73W', '73H', '73C');
/* 
Boeing 737-800 | 738  | B738 
-- Un seul enregistrement dans planes pour les 4 valeurs
*/

select * from planes_OPENFLIGHTS where iata like '73%';
/*
 Boeing 737     | 737  | \N
 Boeing 737-200 | 732  | B732
 Boeing 737-300 | 733  | B733
 Boeing 737-400 | 734  | B734
 Boeing 737-500 | 735  | B735
 Boeing 737-600 | 736  | B736
 Boeing 737-700 | 73G  | B737
 Boeing 737-800 | 738  | B738
 Boeing 737-900 | 739  | B739
 */

/* Aérorports ayant le plus de destinations */

SELECT COUNT(1) as nb_routes, r.source_airport_iata, a.name, a.country
FROM routes_OPENFLIGHTS R
LEFT JOIN AIRPORTS_OPENFLIGHTS A ON A.iata=R.source_airport_iata
GROUP BY r.source_airport_iata, a.name, a.country
ORDER BY 1 DESC
LIMIT 20;

/*
       915 | ATL                 | Hartsfield Jackson Atlanta International Airport | United States
       558 | ORD                 | Chicago O'Hare International Airport             | United States
       535 | PEK                 | Beijing Capital International Airport            | China
       527 | LHR                 | London Heathrow Airport                          | United Kingdom
       524 | CDG                 | Charles de Gaulle International Airport          | France
       497 | FRA                 | Frankfurt am Main Airport                        | Germany
       492 | LAX                 | Los Angeles International Airport                | United States
       469 | DFW                 | Dallas Fort Worth International Airport          | United States
       456 | JFK                 | John F Kennedy International Airport             | United States
       453 | AMS                 | Amsterdam Airport Schiphol                       | Netherlands
       411 | PVG                 | Shanghai Pudong International Airport            | China
       408 | SIN                 | Singapore Changi Airport                         | Singapore
       391 | BCN                 | Barcelona International Airport                  | Spain
       370 | ICN                 | Incheon International Airport                    | South Korea
       368 | MUC                 | Munich Airport                                   | Germany
       368 | MIA                 | Miami International Airport                      | United States
       361 | DEN                 | Denver International Airport                     | United States
       358 | IST                 | Istanbul Airport                                 | Turkey
       356 | LGW                 | London Gatwick Airport                           | United Kingdom
       356 | DXB                 | Dubai International Airport                      | United Arab Emirate

*/

/* Routes les plus concurrentielles */

SELECT COUNT(1) as nb_airlines, a1.name as source_airport, a1.country as source_country, a2.name as dest_airport, a2.country as dest_country
FROM routes_OPENFLIGHTS R
JOIN AIRPORTS_OPENFLIGHTS A1 ON A1.iata=R.source_airport_iata
JOIN AIRPORTS_OPENFLIGHTS A2 ON A2.iata=R.dest_airport_iata
GROUP BY a1.name, a1.country, a2.name, a2.country
ORDER BY 1 DESC
LIMIT 20;

/*

          20 | Chicago O'Hare International Airport             | United States        | Hartsfield Jackson Atlanta International Airport  | United States
          19 | Hartsfield Jackson Atlanta International Airport | United States        | Chicago O'Hare International Airport              | United States
          13 | Chicago O'Hare International Airport             | United States        | Louis ArmstrongNew Orleans International Airport | United States
          13 | Phuket International Airport                     | Thailand             | Suvarnabhumi Airport                              | Thailand
          12 | Hamad International Airport                      | Qatar                | Bahrain International Airport                     | Bahrain
          12 | London Heathrow Airport                          | United Kingdom       | John F Kennedy International Airport              | United States
          12 | Hartsfield Jackson Atlanta International Airport | United States        | Miami International Airport                       | United States
          12 | Miami International Airport                      | United States        | Hartsfield Jackson Atlanta International Airport  | United States
          12 | Suvarnabhumi Airport                             | Thailand             | Hong Kong International Airport                   | Hong Kong
          12 | Hong Kong International Airport                  | Hong Kong            | Suvarnabhumi Airport                              | Thailand
          12 | Abu Dhabi International Airport                  | United Arab Emirates | Muscat International Airport                      | Oman
          12 | Guangzhou Baiyun International Airport           | China                | Hangzhou Xiaoshan International Airport           | China
          12 | John F Kennedy International Airport             | United States        | London HeathrowAirport                           | United Kingdom
          11 | Kigali International Airport                     | Rwanda               | Entebbe International Airport                     | Uganda
          11 | John F Kennedy International Airport             | United States        | Louis ArmstrongNew Orleans International Airport | United States
          11 | Chiang Mai International Airport                 | Thailand             | Suvarnabhumi Airport                              | Thailand
          11 | London Heathrow Airport                          | United Kingdom       | Los Angeles International Airport                 | United States
          11 | Denver International Airport                     | United States        | Hartsfield Jackson Atlanta International Airport  | United States

*/

SELECT count(1) as nb, stops
FROM routes_OPENFLIGHTS
GROUP BY stops
ORDER BY 2;
/*
  nb   | stops
-------+-------
 67652 |     0
    11 |     1
*/

SELECT  a1.name as source_airport, a1.country as source_country, a2.name as dest_airport, a2.country as dest_country
FROM routes_OPENFLIGHTS R
JOIN AIRPORTS_OPENFLIGHTS_OPENFLIGHTS_OPENFLIGHTS A1 ON A1.iata=R.source_airport_iata
JOIN AIRPORTS_OPENFLIGHTS_OPENFLIGHTS A2 ON A2.iata=R.dest_airport_iata
WHERE stops = 1
GROUP BY a1.name, a1.country, a2.name, a2.country
ORDER BY 1;
/*
                   source_airport                    | source_country |                    dest_airport                     | dest_country
-----------------------------------------------------+----------------+-----------------------------------------------------+---------------
 General Edward Lawrence Logan International Airport | United States  | Orlando International Airport                       | United States
 Leonardo da Vinci├óÔé¼ÔÇ£Fiumicino Airport          | Italy          | Jos├â┬® Mart├â┬¡ International Airport              | Cuba
 Orlando International Airport                       | United States  | Akron Canton Regional Airport                       | United States
 Orlando International Airport                       | United States  | General Edward Lawrence Logan International Airport | United States
 Orlando International Airport                       | United States  | Norfolk International Airport                       | United States
 Orlando International Airport                       | United States  | William P Hobby Airport                             | United States
 Port Bouet Airport                                  | Cote d'Ivoire  | Brussels Airport                                    | Belgium
 Rankin Inlet Airport                                | Canada         | Arviat Airport                                      | Canada
 Stockholm-Arlanda Airport                           | Sweden         | G├â┬ñllivare Airport                                | Sweden
 Vancouver International Airport                     | Canada         | Campbell River Airport                              | Canada
 William P Hobby Airport                             | United States  | San Antonio International Airport                   | United States
(11 rows)
*/


----------------------------------------------------------------------------
-- PLANES
----------------------------------------------------------------------------

select count(1) as nb, iata from planes_OPENFLIGHTS
 group by iata having count(1) > 1;
 
 /*
 nb | iata
----+------
  4 | CN1
  2 | E7W
 12 | \N
  2 | LRJ
  2 | ER3
  2 | H25
  8 | CNJ
(7 rows)
*/

select count(1) as nb, icao from planes_OPENFLIGHTS
 group by icao having count(1) > 1;
 
 /*
 nb | icao
----+------
  2 | E135
 14 | \N
(2 rows)
*/

select * from planes_OPENFLIGHTS where iata='\N' or icao='\N';

/*
               name               | iata | icao
----------------------------------+------+------
 Airbus A330                      | 330  | \N
 Airbus A330-700 Beluga XL        | \N   | A337
 Airbus A340                      | 340  | \N
 Airbus A350                      | 350  | \N
 Airbus A380                      | 380  | \N
 BAe 146                          | 146  | \N
 Beechcraft Baron                 | \N   | BE58
 Beechcraft Baron / 55 Baron      | \N   | BE55
 Boeing 727                       | 727  | \N
 Boeing 737                       | 737  | \N
 Boeing 737 MAX 10                | 7MJ  | \N
 Boeing 747                       | 747  | \N
 Boeing 757                       | 757  | \N
 Boeing 767                       | 767  | \N
 Boeing 777                       | 777  | \N
 Boeing 787                       | 787  | \N
 Bombardier 415                   | \N   | CL2T
 Bombardier BD-100 Challenger 300 | \N   | CL30
 Cessna 152                       | \N   | C152
 COMAC C-919                      | \N   | C919
 Embraer 175                      | E75  | \N
 Embraer Legacy 450               | \N   | E545
 Piper PA-28├é┬á(above 200├é┬áhp) | \N   | P28B
 Piper PA-28├é┬á(up to 180├é┬áhp) | \N   | P28A
 Piper PA-44 Seminole             | \N   | PA44
 Tupolev Tu-144                   | \N   | T144
(26 rows)
*/

select * from planes_OPENFLIGHTS where iata='CNJ';

/*
           name            | iata | icao
---------------------------+------+------
 Cessna Citation CJ3       | CNJ  | C25B
 Cessna Citation CJ4       | CNJ  | C25C
 Cessna Citation Excel     | CNJ  | C56X
 Cessna Citation I         | CNJ  | C500
 Cessna Citation II        | CNJ  | C550
 Cessna Citation Mustang   | CNJ  | C510
 Cessna Citation Sovereign | CNJ  | C680
 Cessna Citation X         | CNJ  | C750
(8 rows)
*/
----------------------------------------------------------------------------
-- AIRPORTS
----------------------------------------------------------------------------

SELECT
  count(1) AS total_airlines, --6162
  SUM(CASE WHEN alias='\N' THEN 1 ELSE 0 END) as alias_null_ncount,  --5478
  SUM(CASE WHEN  iata='\N' THEN 1 ELSE 0 END) as iata_null_ncount,  --1
  SUM(CASE WHEN  icao='\N' THEN 1 ELSE 0 END) as icao_null_ncount,  --188
  SUM(CASE WHEN  callsign='\N' THEN 1 ELSE 0 END) as iata_callsign_ncount,  --3
  SUM(CASE WHEN  country='\N' THEN 1 ELSE 0 END) as iata_country_ncount,  --3
  SUM(CASE WHEN  active='\N' THEN 1 ELSE 0 END) as iata_active_ncount --0
 FROM airlines_OPENFLIGHTS;
 
SELECT
  count(1) AS total_airlines, --6162
  SUM(CASE WHEN alias IS NULL THEN 1 ELSE 0 END) as alias_null_ncount,  --0
  SUM(CASE WHEN  iata IS NULL THEN 1 ELSE 0 END) as iata_null_ncount,  --0
  SUM(CASE WHEN  icao IS NULL THEN 1 ELSE 0 END) as icao_null_ncount,  --0
  SUM(CASE WHEN  callsign IS NULL THEN 1 ELSE 0 END) as iata_callsign_ncount,  --0
  SUM(CASE WHEN  country IS NULL THEN 1 ELSE 0 END) as iata_country_ncount,  --0
  SUM(CASE WHEN  active IS NULL THEN 1 ELSE 0 END) as iata_active_ncount --0
 FROM airlines_OPENFLIGHTS;

SELECT
  count(1) AS total_airports, --7690
  SUM(CASE WHEN  name='\N' THEN 1 ELSE 0 END) as name_null_ncount,  --0
  SUM(CASE WHEN  city='\N' THEN 1 ELSE 0 END) as iata_city_ncount,  --0
  SUM(CASE WHEN  country='\N' THEN 1 ELSE 0 END) as iata_country_ncount,  --0
  SUM(CASE WHEN  iata='\N' THEN 1 ELSE 0 END) as iata_null_ncount,  --1626
  SUM(CASE WHEN  icao='\N' THEN 1 ELSE 0 END) as icao_null_ncount,  --1
  SUM(CASE WHEN  latitude IS NULL THEN 1 ELSE 0 END) as latitude_null_count,  --0
  SUM(CASE WHEN  longitude IS NULL THEN 1 ELSE 0 END) as longitude_null_count,  --0
  SUM(CASE WHEN  altitude IS NULL THEN 1 ELSE 0 END) as altitude_null_ncount,  --0 
  SUM(CASE WHEN  timezone='\N' THEN 1 ELSE 0 END) as timezone_ncount,  --3
  SUM(CASE WHEN  dst='\N' THEN 1 ELSE 0 END) as dst_ncount,  --353
  SUM(CASE WHEN  tz='\N' THEN 1 ELSE 0 END) as tz_ncount,  --1021
  SUM(CASE WHEN  type='\N' THEN 1 ELSE 0 END) as type_ncount,  --0
  SUM(CASE WHEN  source='\N' THEN 1 ELSE 0 END) as source_ncount --0
 FROM airports_OPENFLIGHTS;
 
select count(1) as nb, type from airports_OPENFLIGHTS group by type order by 1 desc;

/*
  nb  |  type
------+---------
 7698 | airport
 */
 
 select min(longitude),max(longitude), min(latitude), max(latitude), min(altitude), max(altitude) from airports_OPENFLIGHTS;

/*
 -179.876998901 | 179.951004028 | -90 | 89.5 | -1266 | 14472
 */
 

select airport_id, iata, icao, city, country, altitude from airports_OPENFLIGHTS where altitude <0 order by altitude;

/*
 airport_id | iata | icao |     city     |    country    | altitude
------------+------+------+--------------+---------------+----------
       1600 | MTZ  | LLMZ | Metzada      | Israel        |    -1266
       1595 | EIY  | LLEY | Eyn-yahav    | Israel        |     -164
       7646 | TRM  | KTRM | Palm Springs | UnitedStates  |     -115
       4357 | GUW  | UATG | Atyrau       | Kazakhstan    |      -72
       2151 | RZR  | OINR | Ramsar       | Iran          |      -70
      14104 | \N   | XRAP | Astrakhan    | Russia        |      -66  -- aéroport militaire
       2966 | ASF  | URWA | Astrakhan    | Russia        |      -65
       5932 | NSH  | OINN | Noshahr      | Iran          |      -61
       3689 | IPL  | KIPL | Imperial     | UnitedStates  |      -54
       3758 | NJK  | KNJK | El Centro    | UnitedStates  |      -42
       2123 | RAS  | OIGG | Rasht        | Iran          |      -40
       6747 | GBT  | OING | Gorgan       | Iran          |      -24
        591 | RTM  | EHRD | Rotterdam    | Netherlands   |      -15
        589 | LEY  | EHLE | Lelystad     | Netherlands   |      -13
        580 | AMS  | EHAM | Amsterdam    | Netherands    |      -11
       1126 | ALY  | HEAX | Alexandria   | Egypt         |       -6
	   */
-- Les altitudes sont données en pieds	   
	   
	   select airport_id, iata, icao, city, country, altitude from airports_OPENFLIGHTS where altitude>=10000 order by altitude desc;
	   
/*
 airport_id | iata | icao |    city     |  country  | altitude
  ------------+------+------+-------------+-----------+----------
       9310 | DCY  | ZUDC | Daocheng    | China     |     14472
       6396 | BPX  | ZUBD | Bangda      | China     |     14219
       8921 | KGT  | ZUKD | Kangding    | China     |     14042
       7932 | NGQ  | ZUAL | Shiquanhe   | China     |     14022
       2762 | LPB  | SLLP | La Paz      | Bolivia   |     13355
       2764 | POI  | SLPO | Potosi      | Bolivia   |     12913
       7894 | YUS  | ZYLS | Yushu       | China     |     12816
       8969 | \N   | SLCC | Copacabana  | Bolivia   |     12591
       2792 | JUL  | SPJL | Juliaca     | Peru      |     12552
      13483 | GMQ  | ZLGL | Golog       | China     |     12426
       7766 | SYH  | VNSB | Syangboche  | Nepal     |     12400
       2763 | ORU  | SLOR | Oruro       | Bolivia   |     12152
       4097 | LXA  | ZULS | Lhasa       | China     |     11713
      10943 | AHJ  | ZUHY | Ngawa       | China     |     11600
       2464 | \N   | SAOL | Laboulaye   | Argentina |     11414
       4301 | JZH  | ZUJZ | Jiuzhaigou  | China     |     11327
       2787 | ANS  | SPHY | Andahuaylas | Peru      |     11300
       7313 | UYU  | SLUY | Uyuni       | Bolivia   |     11136
       2791 | JAU  | SPJJ | Jauja       | Peru      |     11034
       4174 | NGX  | VNMA | Manang      | Nepal     |     11001
       2812 | CUZ  | SPZO | Cuzco       | Peru      |     10860
      13490 | NLH  | ZPNL | Ninglang    | China     |     10804
       6375 | DIG  | ZPDQ | Shangri-La  | China     |     10761
       3104 | IXL  | VILH | Leh         | India     |     10682
       9311 | GXH  | ZLXH | Xiahe city  | China     |     10510
(25 rows)
*/

SELECT distinct source_airport_iata from ROUTES_OPENFLIGHTS
WHERE
source_airport_iata not in (SELECT iata from AIRPORTS_OPENFLIGHTS)
ORDER BY 1; --> 157 aéroports non référencés par source_airport_iata dans AIRPORTS_OPENFLIGHTS

SELECT distinct source_airport_id from ROUTES_OPENFLIGHTS
WHERE
source_airport_id not in (SELECT airport_id from AIRPORTS_OPENFLIGHTS)
ORDER BY 1; --> 109 données manquantes dans le fichier airports.csv

SELECT source_airport_id from ROUTES_OPENFLIGHTS
WHERE
source_airport_id not in (SELECT airport_id from AIRPORTS_OPENFLIGHTS)
UNION -- élimine les doublons
SELECT dest_airport_id from ROUTES_OPENFLIGHTS
WHERE
dest_airport_id not in (SELECT airport_id from AIRPORTS_OPENFLIGHTS)
ORDER BY 1; --> 112 données manquantes dans le fichier airports.csv



-----------------------------------------------------------------------------------------------------------------------------------------------
/* vérification de AIRPORTS_OURAIRPORTS */

select count(1) nb_lignes, count(distinct(ident)) from AIRPORTS_OURAIRPORTS
/*
83312	83312
*/

select max(cnt) from (select count(1) as cnt, ident from AIRPORTS_OURAIRPORTS group by ident)
/*
1 -> ident est une clé primaire de AIRPORTS_OURAIRPORTS
*/

select 
count(distinct(ident)) nb_ident, --83312
(select count(1) from AIRPORTS_OPENFLIGTHS) nb_of, --7698
sum(case when ident not in (coalesce(icao_code,''), coalesce(iata_code,''), coalesce(gps_code,''), coalesce(local_code,'')) then 1 else 0 end) nb_out, --45079
sum(case when icao_code is null and iata_code is null and gps_code is null and local_code is null then 1 else 0 end) nb_all_nulls, --33061
sum(case when ident=iata_code then 1 else 0 end) nb_iata,--344
sum(case when ident=gps_code then 1 else 0 end) nb_gps,  --37245
sum(case when ident=local_code then 1 else 0 end) nb_local,  --17531
sum(case when local_code=gps_code then 1 else 0 end) nb_gps_egal_local, --19213
sum(case when local_code=iata_code then 1 else 0 end) nb_iata_egal_local, --1852
sum(case when local_code=icao_code then 1 else 0 end) nb_icao_egal_local, --72
sum(case when iata_code=gps_code then 1 else 0 end) nb_gps_egal_iata, --43
sum(case when ident=gps_code and coalesce(icao_code,'')<>gps_code and coalesce(iata_code,'')<>gps_code and gps_code<>coalesce(local_code, '') then 1 else 0 end) nb_gps_pur, --11832
sum(case when ident=icao_code and icao_code<>coalesce(gps_code, '') and icao_code<>coalesce(local_code, '')then 1 else 0 end) nb_icao_pur --23
from
AIRPORTS_OURAIRPORTS ;
-- Conclusion :
-- La clé unique ident est parfois la valeur d'une des colonnes icao_code, iata_code,gps_code, local_code  parfois c'est une valeurs en dehors et plusieurs de ces 4 colonnes peuvent avoir la même valeur non nulle

select max(nb) from (select count(1) nb, iata_code from AIRPORTS_OURAIRPORTS where iata_code is not null group by iata_code); --1

select max(nb) from (select count(1) nb, icao_code from AIRPORTS_OURAIRPORTS where icao_code is not null group by icao_code); --1

select max(nb) from (select count(1) nb, gps_code from AIRPORTS_OURAIRPORTS where gps_code is not null group by gps_code); --1

-- iata_code, icao_code et iata_code sont des clés uniques mais pas toujours présentes

select max(nb) from (select count(1) nb, local_code from AIRPORTS_OURAIRPORTS where icao_code is not null group by local_code);
/*
6215
*/
--local_code n'est pas unique