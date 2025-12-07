{{ config(
    materialized='incremental',
    unique_key=['airline_iata','source_airport_iata','dest_airport_iata']
) }}

WITH source AS (
  SELECT
    NULLIF(r.airline_iata, '\\N') AS airline_iata,
    a.id AS airline_id,
    NULLIF(r.source_airport_iata, '\\N') AS source_airport_iata,
    aps.id AS source_airport_id,
    NULLIF(r.dest_airport_iata, '\\N') AS dest_airport_iata,
    apd.id AS dest_airport_id,
    NULLIF(r.shared, '\\N') AS shared,
    r.stops,
    NULLIF(r.equipments, '\\N') AS equipments
  FROM {{ ref('openfligths_routes') }} r
  JOIN {{ ref('dim_airlines') }} a
    ON r.airline_iata = a.iata
  JOIN {{ ref('dim_airports') }} aps
    ON r.source_airport_iata = aps.iata_code
  JOIN {{ ref('dim_airports') }} apd
    ON r.dest_airport_iata = apd.iata_code
  WHERE NOT (
    NULLIF(r.airline_iata, '\\N') IS NULL
    OR NULLIF(r.source_airport_iata, '\\N') IS NULL
    OR NULLIF(r.dest_airport_iata, '\\N') IS NULL
  )
)

SELECT * FROM source

