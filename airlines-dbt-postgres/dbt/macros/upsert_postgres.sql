{% macro upsert_postgres(target_table, source_table, unique_key) %}
-- Macro UPSERT compatible PostgreSQL
INSERT INTO {{ target_table }}
SELECT * FROM {{ source_table }}
ON CONFLICT ({{ unique_key }})
DO UPDATE
SET
  {% for c in adapter.get_columns_in_relation(source_table) %}
  {{ c.name }} = EXCLUDED.{{ c.name }}{% if not loop.last %}, {% endif %}
  {% endfor %};
{% endmacro %}
