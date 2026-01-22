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
FLIGHT_FILE="dst4_flight_20d_latest.csv.gz"

echo "=== Starting data restoration from FTP ==="
echo "FTP Host: $FTP_HOST"
echo "Target Database: $PGDATABASE"

# Download using curl
echo "Downloading $REFS_FILE..."
curl -s --user "${FTP_USER}:${FTP_PASS}" "ftp://${FTP_HOST}${FTP_DIR}/${REFS_FILE}" -o "/tmp/${REFS_FILE}"

echo "Downloading $FLIGHT_FILE..."
curl -s --user "${FTP_USER}:${FTP_PASS}" "ftp://${FTP_HOST}${FTP_DIR}/${FLIGHT_FILE}" -o "/tmp/${FLIGHT_FILE}"

# Check if files were downloaded successfully
if [ ! -f "/tmp/${REFS_FILE}" ] || [ ! -f "/tmp/${FLIGHT_FILE}" ]; then
    echo "Error: Failed to download backup files from FTP."
    exit 1
fi

echo "Decompressing files..."
gunzip -f "/tmp/${REFS_FILE}"
gunzip -f "/tmp/${FLIGHT_FILE}"

# The files after gunzip
REFS_SQL="/tmp/dst4_refs_latest.sql"
FLIGHT_CSV="/tmp/dst4_flight_20d_latest.csv"

echo "Truncating existing tables to avoid unique constraint violations..."
# Order is important for FK constraints if CASCADE is not used, but CASCADE is safer.
psql -U "$PGUSER" -d "$PGDATABASE" -c "TRUNCATE public.flight, public.metar, public.taf, public.sky_condition, public.sky_cover_reference RESTART IDENTITY CASCADE;"

echo "Loading reference data (metar, taf, sky_condition, sky_cover_reference)..."
psql -U "$PGUSER" -d "$PGDATABASE" -f "$REFS_SQL"

echo "Loading flight data..."
psql -U "$PGUSER" -d "$PGDATABASE" -c "\copy public.flight FROM '$FLIGHT_CSV' WITH (FORMAT csv, HEADER true)"

echo "Cleaning up temporary files..."
rm -f "$REFS_SQL" "$FLIGHT_CSV"

echo "=== data restoration complete ✔ ==="
