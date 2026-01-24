# Documentation du Pipeline DBT (airlines-dbt-postgres)

Ce document explique l'architecture, le fonctionnement et les étapes de traitement du projet DBT au sein de l'écosystème **CDE Airlines**.

## 1. Architecture des Dossiers

Le projet est divisé en deux composants principaux pour séparer la gestion des données brutes de la transformation :

*   **`dbt_prepare/`** : Ce dossier contient les scripts de "pré-traitement". Sa responsabilité est de collecter, nettoyer et formater les données externes (CSV) avant qu'elles ne soient ingérées par DBT.
*   **`dbt/`** : C'est le cœur du projet DBT. Il contient les modèles de transformation SQL, les macros, et les configurations nécessaires à la création du Data Warehouse dans PostgreSQL.

## 2. Point d'Entrée et Déclenchement

Le pipeline est principalement piloté par le **Makefile** à la racine du projet. 

*   **Déclenchement manuel** : 
    *   `make dbt-prepare` : Lance les scripts de préparation.
    *   `make dbt-seed` : Charge les fichiers CSV (seeds) dans la base de données.
    *   `make dbt-run` : Exécute les transformations SQL (modèles).
    *   `make dbt-all` : Enchaîne les trois étapes précédentes.
*   **Déclenchement automatique** : Inclus dans la commande globale `make all` qui démarre tout le projet (Infrastructure -> Airflow -> DBT).

## 3. Étapes du Traitement

### Étape A : Préparation (`dbt_prepare`)
C'est l'étape où l'on récupère la matière première. Le script principal `run_seed_prepare.sh` exécute :
1.  **Collecte** : Téléchargement de fichiers CSV depuis diverses sources (OpenFlights, OurAirports).
2.  **Nettoyage** : Correction des en-têtes de colonnes (`fix_headers.sh`) et dédoublonnage intelligent des codes IATA via l'API Ninja (`cleanup_iata_dups.py`).
3.  **Stockage** : Les fichiers finalisés sont placés dans le dossier `dbt/seeds/`.

### Étape B : Ingestion Rapide (`dbt-seed`)
Le chargement via `dbt seed` étant lent pour les gros volumes, nous utilisons une méthode optimisée :
1.  **Script Python** : `fast_load_seeds.py` utilise la commande `COPY` de PostgreSQL via `psycopg2`.
2.  **Performance** : Cette méthode est jusqu'à 50x plus rapide que le `dbt seed` standard.
3.  **Schéma** : Les données sont chargées directement dans le schéma `raw`.
4.  **Action** : Déclenché par `make dbt-seed`.

### Étape C : Transformation (`dbt run`)
C'est ici que les données brutes deviennent des informations structurées selon trois niveaux :
1.  **Staging** : Nettoyage léger et renommage des colonnes (schéma `staging`).
2.  **Intermediate** : Calculs complexes, comme l'âge moyen des flottes (schéma `int`).
3.  **Mart** : Tables finales prêtes pour l'analyse ou le Dashboard (schéma `public`).

## 4. Pourquoi deux dossiers ?

La séparation entre `dbt_prepare` et `dbt` respecte les bonnes pratiques d'ingénierie de données :
*   **Isolation des dépendances** : `dbt_prepare` a besoin d'outils comme `wget`, `python` avec `pandas`, alors que `dbt` n'a besoin que du binaire `dbt` et d'une connexion SQL.
*   **Découplage** : Si la source d'un CSV change, vous ne modifiez que le script de préparation, pas votre logique de transformation métier dans DBT.
*   **Contrôle qualité** : On s'assure que les données sont saines avant même que DBT ne commence à travailler.
