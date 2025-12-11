{{ config(
    materialized='incremental',
    unique_key='id'
) }}

WITH source AS (
  SELECT r.*
  FROM {{ ref('ourairports_runways') }} r
  JOIN {{ ref('dim_airports') }} a 
    ON a.id = r.airport_ref
)

SELECT * FROM source
