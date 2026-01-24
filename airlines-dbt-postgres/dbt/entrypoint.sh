#!/bin/bash
set -e

export PGPORT=5432
export PGHOST="${DBT_HOST:-airlines_postgresql}" # Nom du service sur le contenair. PGHOST="127.0.0.1" sur la machine local au lieu du conteneur docker (exemple avec WSL)
export PGUSER="${DBT_USER:-postgres}"

echo "Waiting for PostgreSQL..."

n_max=150
nb_iter=0
until pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" >/dev/null 2>&1; do
      sleep 2
      nb_iter=$((nb_iter+1))   # incrémentation en bash
      if [ "$nb_iter" -gt "$n_max" ]; then
        echo "Échec de connexion à PostgreSQL sur $PGHOST:$PGPORT compte $PGUSER après $n_max tentatives."
        exit 1
      fi
done
echo "PostgreSQL is ready."

echo "Checking dbt configuration..."
dbt debug --profiles-dir /app

echo "Running dbt command: dbt $@"
exec dbt "$@"

