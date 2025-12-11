{{ config(materialized='table') }}
SELECT
  Brand,
  Average_Age::numeric as average_age,
  Place::integer as place
FROM {{ ref('statsbase_fleet_average_age_by_company') }}
