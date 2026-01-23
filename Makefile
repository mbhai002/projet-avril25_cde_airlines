.PHONY: help up down restart logs clean all dbt-prepare dbt-seed dbt-run dbt-all build web-build web-up web-down web-logs

help:
	@echo "Commandes disponibles:"
	@echo "  make build           - Reconstruit les images Docker DBT"
	@echo "  make up              - Démarre tous les services"
	@echo "  make down            - Arrête tous les services"
	@echo "  make restart         - Redémarre tous les services"
	@echo "  make logs            - Affiche les logs de tous les services"
	@echo "  make clean           - Supprime tous les conteneurs et volumes"
	@echo "  make dbt-prepare     - Prépare les données pour DBT"
	@echo "  make dbt-seed        - Charge les seeds DBT"
	@echo "  make dbt-run         - Exécute les transformations DBT"
	@echo "  make dbt-all         - Pipeline complet DBT (prepare + seed + run)"
	@echo "  make web-build       - Reconstruit les images FastAPI et Dash"
	@echo "  make web-up          - Démarre FastAPI et Dash"
	@echo "  make web-down        - Arrête FastAPI et Dash"
	@echo "  make web-logs        - Affiche les logs FastAPI et Dash"
	@echo "  make all             - Démarre tout (services + pipeline DBT)"

build:
	@echo "Reconstruction des images Docker..."
	docker compose build --no-cache dbt dbt_prepare
	@echo "Images reconstruites!"

up:
	@echo "Démarrage de tous les services..."
	@mkdir -p flight-collector/data/metar flight-collector/data/taf flight-collector/logs
	@chmod -R 775 flight-collector/data flight-collector/logs 2>/dev/null || true
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

web-build:
	@echo "Reconstruction des images Web..."
	docker compose build --no-cache fastapi dash
	@echo "Images Web reconstruites!"

web-up:
	@echo "Démarrage des services Web..."
	docker compose up -d fastapi dash
	@echo "FastAPI: http://localhost:8000"
	@echo "Docs API: http://localhost:8000/docs"
	@echo "Dashboard: http://localhost:8050"

web-down:
	@echo "Arrêt des services Web..."
	docker compose stop fastapi dash
	@echo "Services Web arrêtés!"

web-logs:
	docker compose logs -f fastapi dash

all:
	@echo "=== Démarrage du projet complet ==="
	@$(MAKE) up
	@echo ""
	@echo "=== Attente du démarrage de PostgreSQL ==="
	@until docker exec airlines_postgresql pg_isready -h localhost -U postgres >/dev/null 2>&1; do \
		echo "PostgreSQL n'est pas encore prêt (initialisation en cours)..."; \
		sleep 5; \
	done
	@echo "PostgreSQL est prêt !"
	@echo ""
	@echo "=== Configuration Airflow ==="
	@echo "Attente d'Airflow (initialisation base de données)..."
	@until docker exec airlines_airflow airflow db check >/dev/null 2>&1; do \
		echo "Airflow : initialisation de la base en cours..."; \
		sleep 5; \
	done
	@echo "Attente de la création de l'utilisateur par Airflow standalone..."
	@until docker exec airlines_airflow airflow users list 2>/dev/null | grep admin >/dev/null 2>&1; do \
		echo "Airflow : création de l'utilisateur admin en cours..."; \
		sleep 5; \
	done
	@echo "Configuration du compte admin (admin/admin)..."
	@docker exec airlines_airflow airflow users delete --username admin >/dev/null 2>&1 || true
	@docker exec airlines_airflow airflow users create \
		--username admin --password admin \
		--firstname Admin --lastname Admin \
		--role Admin --email admin@example.com >/dev/null 2>&1
	@echo "Airflow est prêt sur http://localhost:8081 (admin/admin)"
	@echo ""
	@echo "=== Pipeline DBT ==="
	@$(MAKE) dbt-all
	@echo ""
	@echo "=== Projet complet démarré! ==="
	@echo "PostgreSQL: localhost:5432"
	@echo "MongoDB: localhost:27017"
	@echo "pgAdmin: http://localhost:5050"
	@echo "FastAPI: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"
	@echo "Dashboard: http://localhost:8050"
	@echo "MongoDB: localhost:27017"
	@echo "pgAdmin: http://localhost:5050"
