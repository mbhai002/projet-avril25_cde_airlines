.PHONY: help up down restart logs clean all dbt-prepare dbt-seed dbt-run dbt-all build

help:
	@echo "Commandes disponibles:"
	@echo "  make build           - Reconstruit les images Docker"
	@echo "  make up              - Démarre tous les services"
	@echo "  make down            - Arrête tous les services"
	@echo "  make restart         - Redémarre tous les services"
	@echo "  make logs            - Affiche les logs de tous les services"
	@echo "  make clean           - Supprime tous les conteneurs et volumes"
	@echo "  make dbt-prepare     - Prépare les données pour DBT"
	@echo "  make dbt-seed        - Charge les seeds DBT"
	@echo "  make dbt-run         - Exécute les transformations DBT"
	@echo "  make dbt-all         - Pipeline complet DBT (prepare + seed + run)"
	@echo "  make all             - Démarre tout (services + pipeline DBT)"

build:
	@echo "Reconstruction des images Docker..."
	docker compose build --no-cache dbt dbt_prepare
	@echo "Images reconstruites!"

up:
	@echo "Démarrage de tous les services..."
	docker compose up -d
	@echo "Services démarrés!"

down:
	@echo "Arrêt de tous les services..."
	docker compose down 
	@echo "Services arrêtés!"

restart: down up

logs:
	docker compose logs -f

clean:
	@echo "Nettoyage complet..."
	docker compose down -v
	@echo "Nettoyage terminé!"

dbt-prepare:
	@echo "Préparation des données DBT..."
	docker compose run --rm dbt_prepare
	@echo "Préparation terminée!"

dbt-seed:
	@echo "Chargement des seeds DBT..."
	docker compose run --rm dbt seed --profiles-dir /app --full-refresh
	@echo "Seeds chargés!"

dbt-run:
	@echo "Exécution des transformations DBT..."
	docker compose run --rm dbt run --profiles-dir /app --full-refresh
	@echo "Transformations terminées!"

dbt-all: dbt-prepare dbt-seed dbt-run

all:
	@echo "=== Démarrage du projet complet ==="
	@$(MAKE) up
	@echo ""
	@echo "=== Attente du démarrage de PostgreSQL ==="
	@timeout /t 20 /nobreak > nul
	@echo ""
	@echo "=== Pipeline DBT ==="
	@$(MAKE) dbt-all
	@echo ""
	@echo "=== Projet complet démarré! ==="
	@echo "PostgreSQL: localhost:5432"
	@echo "MongoDB: localhost:27017"
	@echo "pgAdmin: http://localhost:5050"
