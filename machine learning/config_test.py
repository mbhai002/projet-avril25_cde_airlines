#!/usr/bin/env python3
"""Configuration pour le test du modèle en production"""

# PostgreSQL URI (même format que main.py)
POSTGRESQL_URI = "postgresql://postgres:cdps%40973@localhost:5433/dst_ml"

# Nombre de vols à tester
N_FLIGHTS_TO_TEST = 1000

# Chemin du modèle (None = le plus récent)
MODEL_CONFIG_PATH = None
