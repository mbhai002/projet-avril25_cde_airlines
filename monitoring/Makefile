# ========================
# Makefile - Observability
# ========================

# ---------
# Réseau
# ---------
NETWORK ?= observability_network

.PHONY: all network start stop clean

all: network start

network:
	docker network inspect $(NETWORK) >/dev/null 2>&1 || docker network create $(NETWORK)

setup:
	@echo "Création des dossiers nécessaires..."
	mkdir -p grafana/data grafana/plugins
	touch grafana/data/.gitkeep
	touch grafana/plugins/.gitkeep
	@echo "Dossiers créés avec succès."

start: network setup
	docker compose up -d
	@echo "Observability lancée sur le réseau $(NETWORK)"

stop:
	docker compose down

clean: 
	docker compose down -v --remove-orphans
	docker volume prune -f
