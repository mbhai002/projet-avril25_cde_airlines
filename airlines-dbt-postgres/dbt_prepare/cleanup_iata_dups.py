#!/usr/bin/env python3 
""" Correction du flag active=N des lignes avec le même code iata de manière à n'avoir seule qu'une ligne active pour chaque valeur du code IATA arlines.csv 
Pour chaque doublon, l'API api-ninjas est interrogée et un score est calculé pour chaque ligne active en doublon, 
la ligne qui a la meilleure correspondance sur le nom et le code icao conserve la valeur active='Y', les autres prennent la valeur active='N' 
Principe de détermination de la ligne retenue :
 1. Extraction des codes iata (clé) et des lignes associées (valeur=liste de records))
 2. Pour chaque record de la liste associée à un code iata en doublon :
  Si active=Y
    Si code icao est le même que celui retourné par icao -> ligne retenue
    Sinon Si le nom est le même que celui retourné par l'API (à la casse près) -> ligne retenue
    Sinon 
      Calcul d'un score de similitude entre le nom de la compagnie dans la ligne et le nom retourné par l'API pour ce code_iata
      Si score > score des lignes précédents pour ce cide iata -> best_score = score et ligne stockée dans une varianle best -> retenue en fin de boucle sur la liste des doublons
      Sinon valeur stockéee dans best inchangée  
      Fin Si
    Fin Si
   Sinon (active=N) -> ligne non prise en compte
   Fin Si
  3. Les modifications sont répercutées dans le fichier arlines.csv """

import os
import logging
import requests
import csv
from difflib import SequenceMatcher

# Configuration du logger
API_KEY = os.environ.get("API_NINJAS_KEY")
SEED_DIR = os.environ.get("TARGET_DIR")  # répertoire cible des seeds vu dans le container
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("cleanup.log", encoding="utf-8")]
)
log = logging.getLogger("cleanup")

def similar(a, b):
    if not a or not b:
        return 0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def choose_best_row(rows, api_entries):
    active_rows = [r for r in rows if r.get("active", "").upper() == "Y"]
    if not active_rows:
        return None, None

    best = None
    best_score = -1
    best_index = None

    for r in active_rows:
        r_name = r.get("name")
        r_icao = r.get("icao")

        for api in api_entries:
            api_name = api.get("name")
            api_icao = api.get("icao")

            if api_icao and r_icao and api_icao.upper() == r_icao.upper():
                return r, rows.index(r)

            if api_name and r_name and api_name.lower() == r_name.lower():
                return r, rows.index(r)

            score = similar(r_name, api_name)
            if score > best_score:
                best_score = score
                best = r
                best_index = rows.index(r)

    return best, best_index

# Cache pour éviter les appels multiples
api_cache = {}
def call_api(iata):
    if iata in api_cache:
        return api_cache[iata]

    url = f"https://api.api-ninjas.com/v1/airlines?iata={iata}"
    headers = {"X-Api-Key": API_KEY}
    try:
        api_resp = requests.get(url, headers=headers, timeout=5).json()
    except Exception as e:
        log.warning(f"Erreur API pour {iata}: {e}")
        api_resp = []

    if isinstance(api_resp, dict):
        api_resp = [api_resp]

    api_cache[iata] = api_resp
    return api_resp

# Construction du chemin complet vers airlines.csv
csv_path = os.path.join(SEED_DIR, "openfligths_airlines.csv")

# Lecture CSV
with open(csv_path, newline='', encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

# Regroupement par IATA
by_iata = {}
for r in rows:
    iata = r.get("iata")
    if iata and iata != "\\N":
        by_iata.setdefault(iata, []).append(r)

# Trouver les IATA avec plusieurs lignes actives
iata_active_dupl = {
    iata
    for iata, group in by_iata.items()
    if sum(r["active"].upper() == "Y" for r in group) > 1
}

# Déterminer la meilleure ligne uniquement pour les doublons
d_iata = {}
for iata in iata_active_dupl:
    api_entries = call_api(iata)
    best, best_index = choose_best_row(by_iata[iata], api_entries)
    if best_index is not None:
        d_iata[iata] = best_index

# Modification des lignes + logging
total_disabled = 0
for iata in iata_active_dupl:
    group = by_iata[iata]
    best_index = d_iata.get(iata)
    for idx, r in enumerate(group):
        if r["active"].upper() == "Y" and idx != best_index:
            log.info(f"Désactivation: IATA={iata}, Nom={r.get('name')}, ICAO={r.get('icao')}")
            r["active"] = "N"
            total_disabled += 1

log.info(f"Nettoyage terminé: {total_disabled} lignes désactivées.")

# Réécriture du fichier CSV
with open(csv_path, "w", newline='', encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
