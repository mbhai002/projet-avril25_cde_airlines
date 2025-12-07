#!/bin/bash

SEED_TARGET_DIR=${TARGET_DIR} # Répertoire des seeds dbt monté dans le contenbeur

add_header_if_missing() {
  FILE=$1
  HEADER=$2
  NAME=$3

  if [ -f "$FILE" ]; then
    FIRST_LINE=$(head -n 1 "$FILE"| tr -d '\r')  # Supprimer les retours chariot éventuels
    if [ "${FIRST_LINE}" != "${HEADER}" ]; then
      echo "$HEADER" | cat - "$FILE" > "$FILE.tmp" && mv "$FILE.tmp" "$FILE"
      echo "✔ Ajout header : $NAME"
    else
      echo "↪ Header déjà présent : $NAME"
    fi
  else
    echo "✘ Fichier introuvable : $FILE"
  fi
}

# === Appels pour les 3 fichiers OpenFlights ===

add_header_if_missing ${SEED_TARGET_DIR}"/openfligths_airlines.csv" \
"id,name,alias,iata,icao,callsign,country_name,active" \
"openfligths_airlines.csv"

add_header_if_missing ${SEED_TARGET_DIR}"/openfligths_airports.csv" \
"id,name,city,country,iata_code,icao_code,latitude,longitude,altitude,gmt_offset,dst,timezone,airporttype,source" \
"openfligths_airports.csv"

add_header_if_missing ${SEED_TARGET_DIR}"/openfligths_routes.csv" \
"airline_iata,airline_id,source_airport_iata,source_airport_id,dest_airport_iata,dest_airport_id,shared,stops,equipments" \
"openfligths_routes.csv"
