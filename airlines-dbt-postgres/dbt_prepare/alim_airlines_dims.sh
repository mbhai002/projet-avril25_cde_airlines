#!/bin/bash

#Ce script est utilisé pour extraire les fichiers au format csv sur les sites du net ourairports et openfligths
#Si une différence de contenu est observée par rapport à sa dernière extraction le fichier est renommé en csv et selon la source et recopié dans le répertoire des seeds de dbt pmour intégration
#Les fichiers de données sont récupérés dans un répertoire $ROOT_DEP_DIR du host monté dans le container qaui doit contenir les sous_répertoures suivants :
# - ourairports
# - openfligths
# - opentraveldata
# - statsbase
# - toprocess
# - logs
# cd $ROOT_DEP_DIR && mkdir -p ourairports openfligths opentraveldata statsbase toprocess logs
# Le script extrait les fichiers au format csv dans ces 4 sous répertoires
# Il constitue ensuite une liste $TO_PROCESS_LIST des fichiers à intégrer dans le seeds de dbt
# Une fois cette liste constitués, les fichiers s'il y a une modifaction dans le nouveau téléchargement d'un fichier par rapport au précédent le fichier du seed correspondant est remplacé

set -e

###############################
# CONFIGURATION
###############################

export ROOT_DEP_DIR="${SOURCE_DIR}"
export SEEDS_DIR="${TARGET_DIR}"

OURAIRPORTS_URI="https://davidmegginson.github.io/ourairports-data"
OPENFLIGHTS_URI="https://raw.githubusercontent.com/jpatokal/openflights/master/data"
OPENTRAVELDATA_URI="https://raw.githubusercontent.com/opentraveldata/opentraveldata/master/opentraveldata"

OURAIRPORTS_DIR="$ROOT_DEP_DIR/ourairports"
OPENFLIGHTS_DIR="$ROOT_DEP_DIR/openfligths"
OPENTRAVELDATA_DIR="$ROOT_DEP_DIR/opentraveldata"
STATSBASE_DIR="$ROOT_DEP_DIR/statsbase"

TO_PROCESS_DIR="$ROOT_DEP_DIR/toprocess"
TO_PROCESS_LIST="$TO_PROCESS_DIR/tab_list.lst"

LOGFILE="$ROOT_DEP_DIR/logs/alim_airlines_dims.log"

###############################
# LOG FUNCTION
###############################
log() {
    mkdir -p "$(dirname "$LOGFILE")"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOGFILE"
}

###############################
# CREATE DIRECTORIES
###############################

mkdir -p "$ROOT_DEP_DIR"
mkdir -p "$OURAIRPORTS_DIR"
mkdir -p "$OPENFLIGHTS_DIR"
mkdir -p "$OPENTRAVELDATA_DIR"
mkdir -p "$STATSBASE_DIR"
mkdir -p "$TO_PROCESS_DIR"
mkdir -p "$(dirname "$LOGFILE")"

log "Répertoires initialisés"

###############################
# GET FILE DATE
###############################
get_file_date() {
    local file="$1"
    if [ -f "$file" ]; then
        stat -c %Y "$file"
    else
        echo ""
    fi
}

###############################
# ADD FILE TO PROCESS LIST
###############################
add_in_plist() {
    echo "$1" >> "$TO_PROCESS_LIST"
}

###############################
# PROCESS ONE FILE
###############################
fname_process() {
    local FNAME="$1"
    local DNAME="$2"
    local URI TAG

    case "$DNAME" in
        "$OURAIRPORTS_DIR")     URI="$OURAIRPORTS_URI"; TAG="ourairports" ;;
        "$OPENFLIGHTS_DIR")     URI="$OPENFLIGHTS_URI"; TAG="openfligths" ;;
        "$OPENTRAVELDATA_DIR")  URI="$OPENTRAVELDATA_URI"; TAG="opentraveldata" ;;
        "$STATSBASE_DIR")       URI=""; TAG="statsbase" ;; # pas de téléchargement ici
        *) log "ERREUR : répertoire inconnu : $DNAME"; return 1 ;;
    esac
    
    log "Traitement de $FNAME dans $DNAME"
    
    cd "$DNAME"

    local base="${FNAME%.*}"

    if [ -f "$FNAME" ]; then
        # Sauvegarde
        local ts
        ts=$(get_file_date "$FNAME")
        local backup="${FNAME}.${ts}"
        mv "$FNAME" "$backup"

        # Téléchargement
        wget -q "$URI/$FNAME" -O "$FNAME" || {
            log "Erreur de téléchargement $URI/$FNAME, restauration."
            mv "$backup" "$FNAME"
            return 1
        }

        # Comparaison
        if diff -q "$FNAME" "$backup" >/dev/null; then
            rm -f "$FNAME"
            mv "$backup" "$FNAME"
            log "$FNAME inchangé."
        else
            log "$FNAME mis à jour."
            add_in_plist "${TAG}_${base}"
        fi

    else
        # Téléchargement initial
        wget -q "$URI/$FNAME" -O "$FNAME" || {
            log "Erreur téléchargement initial : $URI/$FNAME"
            return 1
        }
        add_in_plist "${TAG}_${base}"
        log "Téléchargement initial OK : $FNAME"
    fi
}

###############################
# RESET LIST
###############################
rm -f "$TO_PROCESS_LIST"
touch "$TO_PROCESS_LIST"

###############################
# PROCESS FILE GROUPS
###############################

# Opentraveldata
#for fname in "optd_airports.csv" "optd_airlines.csv"; do
#   fname_process "$fname" "$OPENTRAVELDATA_DIR"
#done

# OurAirports
for fname in "airports.csv" "runways.csv" "countries.csv"; do
    fname_process "$fname" "$OURAIRPORTS_DIR"
done

# OpenFlights
for fname in "airports.dat" "airlines.dat" "planes.dat" "routes.dat"; do
    fname_process "$fname" "$OPENFLIGHTS_DIR"
done

###############################
# COPY UPDATED FILES TO DBT SEEDS
###############################
# echo "Désactivation temporaire de la copie des fichiers mis à jour" 
# exit 0 ## Désactivation temporaire de la copie des fichiers mis à jour
 
if [ ! -s "$TO_PROCESS_LIST" ]; then
    echo "Aucun fichier mis à jour."
    exit 0
fi

echo "Fichiers mis à jour :"
cat "$TO_PROCESS_LIST"

while read -r entry; do
    TAG=$(echo "$entry" | cut -d_ -f1)
    NAME=$(echo "$entry" | cut -d_ -f2)

    case "$TAG" in
        opentraveldata)  DIR="$OPENTRAVELDATA_DIR"; EXT="csv" ;;
        ourairports)     DIR="$OURAIRPORTS_DIR";    EXT="csv" ;;
        openfligths)     DIR="$OPENFLIGHTS_DIR";    EXT="dat" ;;
        statsbase)       DIR="$STATSBASE_DIR";      EXT="csv" ;;
        *) log "TAG inconnu : $TAG"; continue ;;
    esac

    SRC="${DIR}/${NAME}.${EXT}" # Fichier de la liste à traiter généré auparavant dans le répertoire de dépot
    DST="${SEEDS_DIR}/${TAG}_${NAME}.csv" # Fichier de destination dans le répertoire des seeds de dbt, avec extension csv (obliigatoire pour dbt)

    if [ -f "$SRC" ]; then
        cp -p "$SRC" "$DST"
        log "Copie : $SRC → $DST"
    else
        log "ERREUR : fichier introuvable $SRC"
    fi

done < "$TO_PROCESS_LIST"

rm -f "$TO_PROCESS_LIST"

echo "✔ Mise à jour des seeds terminée."
exit 0


