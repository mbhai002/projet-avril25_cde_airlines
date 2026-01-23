#!/bin/bash
set -e

# Configuration
FTP_HOST="${FTP_HOST}"
FTP_USER="${FTP_USER}"
FTP_PASS="${FTP_PASS}"
FTP_DIR="${FTP_DIR:-/backup}"

if [ -z "$FTP_HOST" ] || [ -z "$FTP_USER" ] || [ -z "$FTP_PASS" ]; then
    echo "Error: FTP_HOST, FTP_USER or FTP_PASS is not set. Restoration aborted."
    exit 1
fi

# Database config
PGUSER="${POSTGRES_USER:-postgres}"
PGDATABASE="${POSTGRES_DB:-airlines_db}"
export PGPASSWORD="${POSTGRES_PASSWORD:-postgres}"

# Filenames produced by the export script
REFS_FILE="dst4_refs_latest.sql.gz"
METAR_FILE="dst4_metar_latest.csv.gz"
TAF_FILE="dst4_taf_latest.csv.gz"
SKY_COND_FILE="dst4_sky_condition_latest.csv.gz"
FLIGHT_FILE="dst4_flight_latest.csv.gz"

echo "=== Starting data restoration from FTP ==="
echo "FTP Host: $FTP_HOST"
echo "Target Database: $PGDATABASE"

# Download using curl
for FILE in "$REFS_FILE" "$METAR_FILE" "$TAF_FILE" "$SKY_COND_FILE" "$FLIGHT_FILE"; do
    echo "Downloading $FILE..."
    curl -s --user "${FTP_USER}:${FTP_PASS}" "ftp://${FTP_HOST}${FTP_DIR}/${FILE}" -o "/tmp/${FILE}"
done

# Check if files were downloaded successfully
for FILE in "$REFS_FILE" "$METAR_FILE" "$TAF_FILE" "$SKY_COND_FILE" "$FLIGHT_FILE"; do
    if [ ! -f "/tmp/${FILE}" ]; then
        echo "Error: Failed to download $FILE from FTP."
        exit 1
    fi
done

echo "Decompressing files..."
gunzip -f "/tmp/${REFS_FILE}"
gunzip -f "/tmp/${METAR_FILE}"
gunzip -f "/tmp/${TAF_FILE}"
gunzip -f "/tmp/${SKY_COND_FILE}"
gunzip -f "/tmp/${FLIGHT_FILE}"

# Paths for imported files (gunzip removes the .gz extension)
REFS_SQL="/tmp/${REFS_FILE%.gz}"
METAR_CSV="/tmp/${METAR_FILE%.gz}"
TAF_CSV="/tmp/${TAF_FILE%.gz}"
SKY_COND_CSV="/tmp/${SKY_COND_FILE%.gz}"
FLIGHT_CSV="/tmp/${FLIGHT_FILE%.gz}"

echo "Truncating existing tables to avoid unique constraint violations..."
psql -U "$PGUSER" -d "$PGDATABASE" -c "TRUNCATE public.flight, public.metar, public.taf, public.sky_condition, public.sky_cover_reference RESTART IDENTITY CASCADE;"

echo "Loading reference data (sky_cover_reference)..."
psql -U "$PGUSER" -d "$PGDATABASE" -f "$REFS_SQL"

echo "Loading METAR data..."
psql -U "$PGUSER" -d "$PGDATABASE" -c "\copy public.metar FROM '$METAR_CSV' WITH (FORMAT csv, HEADER true)"

echo "Loading TAF data..."
psql -U "$PGUSER" -d "$PGDATABASE" -c "\copy public.taf FROM '$TAF_CSV' WITH (FORMAT csv, HEADER true)"

echo "Loading Sky Conditions data..."
psql -U "$PGUSER" -d "$PGDATABASE" -c "\copy public.sky_condition FROM '$SKY_COND_CSV' WITH (FORMAT csv, HEADER true)"

echo "Loading flight data..."
psql -U "$PGUSER" -d "$PGDATABASE" -c "\copy public.flight FROM '$FLIGHT_CSV' WITH (FORMAT csv, HEADER true)"

echo "Cleaning up temporary files..."
rm -f "$REFS_SQL" "$METAR_CSV" "$TAF_CSV" "$SKY_COND_CSV" "$FLIGHT_CSV"

echo "=== data restoration complete ✔ ==="
