{{ config(
    materialized='incremental',
    unique_key='id'
) }}

WITH source AS (
    SELECT
      a.id,
      a.name,
      a.iata,
      a.icao,
      c.code AS country_code,
      fa.average_age,
      a.active
    FROM {{ ref('openfligths_airlines') }} a
    LEFT JOIN {{ ref('dim_countries') }} c
      ON a.country_name = c.country_name
    LEFT JOIN {{ ref('fleet_age_by_company') }} fa
      ON UPPER(fa."Brand") = UPPER(a.name)
    WHERE (LENGTH(a.iata) = 2 OR LENGTH(a.icao) = 3)
)

{% if is_incremental() %}
SELECT
    s.id,
    s.name,
    s.iata,
    s.icao,
    s.country_code,
    s.average_age,
    CASE
      WHEN d.active = 'Y' AND UPPER(s.active) = 'N' THEN 'N'
      WHEN d.active = 'N' AND UPPER(s.active) = 'Y' THEN 'Y'
      ELSE d.active
    END AS active
FROM source s
LEFT JOIN {{ this }} d
  ON s.id = d.id

{% else %}
SELECT
    s.id,
    s.name,
    s.iata,
    s.icao,
    s.country_code,
    s.average_age,
    CASE WHEN UPPER(s.active) = 'Y' THEN 'Y' ELSE 'N' END AS active
FROM source s
{% endif %}

