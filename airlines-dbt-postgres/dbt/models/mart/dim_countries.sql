{{ config(
    materialized='incremental',
    unique_key='code'
) }}

WITH matches AS (
  SELECT c.id,
         s.country_name,
         s.average_age,
         c.code,
         similarity(c.name, s.country_name) AS score
  FROM {{ ref('ourairports_countries') }} c
  LEFT JOIN {{ ref('fleet_age_by_country') }} s
    ON similarity(c.name, s.country_name) > 0.3
),
ranked AS (
  SELECT *,
         ROW_NUMBER() OVER (PARTITION BY country_name ORDER BY score DESC) AS rn_country,
         ROW_NUMBER() OVER (PARTITION BY code ORDER BY score DESC) AS rn_code
  FROM matches
),
m AS (
  SELECT id, code, country_name, average_age, score
  FROM ranked
  WHERE country_name IS NOT NULL
    AND rn_country = 1
    AND rn_code = 1
),
source AS (
  SELECT * FROM m
  UNION ALL
  SELECT c.id, c.code, c.name AS country_name, NULL::numeric AS average_age, NULL::numeric AS score
  FROM {{ ref('ourairports_countries') }} c
  LEFT JOIN m ON m.id = c.id
  WHERE m.id IS NULL
)

SELECT * FROM source

