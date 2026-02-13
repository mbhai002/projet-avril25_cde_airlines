#!/bin/bash
set -euo pipefail

psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<EOF
DO
\$\$
BEGIN
   IF NOT EXISTS (
      SELECT 1 FROM pg_roles WHERE rolname = 'exporter'
   ) THEN
      EXECUTE format(
        'CREATE USER exporter WITH PASSWORD %L',
        '$EXPORTER_PASSWORD'
      );
   ELSE
      EXECUTE format(
        'ALTER USER exporter WITH PASSWORD %L',
        '$EXPORTER_PASSWORD'
      );
   END IF;
END
\$\$;

GRANT pg_monitor TO exporter;
EOF

