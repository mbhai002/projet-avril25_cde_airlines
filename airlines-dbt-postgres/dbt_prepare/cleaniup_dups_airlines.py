#!/usr/bin/env python3
"""
Nettoyage des doublons dans raw.openfligths_airlines.

- Détecte les doublons IATA
- Interroge l'API api-ninjas
- Sélectionne la meilleure ligne
- Construit la table raw.openfligths_airlines_cleaned

Ne modifie jamais dim_airlines.
"""

import os
import sys
import time
import logging
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from difflib import SequenceMatcher

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("cleanup")

DB_HOST = os.environ.get("DB_HOST", "postgres")
DB_PORT = int(os.environ.get("DB_PORT", 5432))
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")
DB_NAME = os.environ.get("DB_NAME", "airlines")
API_KEY = os.environ.get("API_NINJAS_KEY")

def similar(a, b):
    if not a or not b:
        return 0
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def choose_best_row(rows, api_entries):
    if not rows:
        return None

    best = None
    best_score = -1

    for r in rows:
        r_name = r["name"]
        r_icao = r["icao"]

        for api in api_entries:
            api_name = api.get("name")
            api_icao = api.get("icao")

            if api_icao and r_icao and api_icao.upper() == r_icao.upper():
                return r

            if api_name and r_name and api_name.lower() == r_name.lower():
                return r

            score = similar(r_name, api_name)
            if score > best_score:
                best_score = score
                best = r
    return best


def main():
    log.info("Nettoyage des seeds openfligths_airlines…")

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD,
        dbname=DB_NAME
    )

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 1️⃣ — lire toutes les lignes du seed
    cur.execute("SELECT * FROM raw.openfligths_airlines;")
    rows = cur.fetchall()

    # les regrouper par IATA
    by_iata = {}
    for r in rows:
        iata = r["iata"]
        if not iata:
            continue
        by_iata.setdefault(iata, []).append(r)

    cleaned = []

    for iata, group in by_iata.items():

        if len(group) == 1:
            cleaned.append(group[0])
            continue

        # 2️⃣ — doublon ⇒ API call
        url = f"https://api.api-ninjas.com/v1/airlines?iata={iata}"
        headers = {"X-Api-Key": API_KEY}
        try:
            api_resp = requests.get(url, headers=headers, timeout=10).json()
        except:
            api_resp = []

        if isinstance(api_resp, dict):
            api_resp = [api_resp]

        best = choose_best_row(group, api_resp)
        cleaned.append(best)

        log.info(f"IATA {iata}: doublon → ligne conservée id={best['id']}")

        time.sleep(0.5)  # rate limit

    # 3️⃣ — écriture dans la nouvelle table cleaned
    cur.execute("DROP TABLE IF EXISTS staging.openfligths_airlines_cleaned;")
    conn.commit()

    create_sql = """
    CREATE TABLE staging.openfligths_airlines_cleaned AS
    SELECT *
    FROM raw.openfligths_airlines
    WHERE false;
    """
    cur.execute(create_sql)
    conn.commit()

    # insert
    for row in cleaned:
        cols = row.keys()
        sql = f"""
            INSERT INTO staging.openfligths_airlines_cleaned ({",".join(cols)})
            VALUES ({",".join(["%s"] * len(cols))})
        """
        cur.execute(sql, list(row.values()))

    conn.commit()
    conn.close()

    log.info("✔ Nettoyage terminé : table staging.openfligths_airlines_cleaned créée.")


if __name__ == "__main__":
    main()

