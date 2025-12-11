.PHONY: up prepare seed run all down

# Démarre uniquement Postgres
up:
	docker compose up -d postgres pgadmin

# Prépare l'environnement (par ex. installation dépendances)
prepare: up
	docker compose run --rm dbt_prepare

# Exécute dbt seed à la demande
seed: up
	docker compose run --rm dbt seed --profiles-dir /app --full-refresh

# Exécute dbt run à la demande
run: up
	docker compose run --rm dbt run --profiles-dir /app --full-refresh

# Pipeline complet
all: prepare seed run

# Stoppe tous les services
down:
	docker compose down

