#!/bin/bash
set -e

# echo "=== 1. Exécution de fleet_average_age.py - Récupoération de  tables d'ages moyen des flottes par pays et par compagnies au format csv via du web scrating ==="
# python3 /app/fleet_average_age.py || echo "fleet_average_age.py ignoré (nécessite Selenium pour JavaScript)"

echo "=== 2. Exécution de alim_airlines_dims.sh - Récupération de fichiers csv sur le net - Extraction dans un répertoire de dépot puis transfert vers un répertoire seeds sous conditons ==="
/app/alim_airlines_dims.sh
if [ $? -ne 0 ]; then
    echo "❌ Erreur dans alim_airlines_dims.sh"
    exit 1
fi

echo "=== 3. Exécution de fix_headers.sh - Ajout de l'entête de fichier csv dans les seeds si elle est absente ==="
/app/fix_headers.sh
if [ $? -ne 0 ]; then
    echo "❌ Erreur dans fix_headers.sh"
    exit 1
fi

echo "=== 4. Exécution de cleanup_iata_dups.py - désactivation des codes iata de compagnies superflus via l'Api Ninja (faux doublons) ==="
python3 /app/cleanup_iata_dups.py
if [ $? -ne 0 ]; then
    echo "❌ Erreur dans cleanup_iata_dups.py"
    exit 1
fi

echo "✔ Préparation terminée avec succès"
exit 0
