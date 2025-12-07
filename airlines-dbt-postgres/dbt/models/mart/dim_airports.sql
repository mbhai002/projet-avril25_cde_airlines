{{ config(
    materialized='incremental',
    unique_key='id'
) }}

WITH source AS (
    SELECT
      oa.id,
      oa.ident,
      oa.type AS airport_type,
      oa.name AS airport_name,
      oa.latitude_deg,
      oa.longitude_deg,
      oa.iso_country,
      oa.continent,
      oa.iso_region,
      oa.icao_code,
      oa.iata_code,
      oa.gps_code,
      oa.local_code,
      CASE WHEN ofl.timezone='\\N' THEN NULL ELSE ofl.timezone END AS timezone,
      CASE WHEN ofl.gmt_offset='\\N' THEN NULL ELSE ofl.gmt_offset END AS gmt_offset
    FROM {{ ref('ourairports_airports') }} oa
    LEFT JOIN {{ ref('openfligths_airports') }} ofl
      ON COALESCE(oa.iata_code, oa.icao_code) = COALESCE(ofl.iata_code, ofl.icao_code)
    WHERE (oa.icao_code IS NOT NULL OR oa.iata_code IS NOT NULL)
)

SELECT * FROM source

