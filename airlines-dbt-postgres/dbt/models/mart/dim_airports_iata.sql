{{ config(materialized='table') }}
SELECT DISTINCT id, iata_code
FROM {{ ref('dim_airports') }}
WHERE iata_code IS NOT NULL
