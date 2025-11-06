#!/usr/bin/env python3
"""
Configuration enrichie pour le collecteur de vols
"""

from dataclasses import dataclass
from enum import Enum
from typing import List


class CollectionType(Enum):
    """Types de collecte disponibles"""
    REALTIME = "realtime_departures"
    PAST = "past_departures"


@dataclass
class CollectionConfig:
    """Configuration complète pour une collecte"""
    # Base de données
    mongodb_uri: str = "mongodb://localhost:27017/"
    database_name: str = "dst_airlines_test"
    
    # PostgreSQL
    enable_postgresql_insertion: bool = True
    postgresql_uri: str = "postgresql://postgres:cdps%40973@localhost:5433/dst"
    
    # Machine Learning
    ml_model_dir: str = "machine_learning/model_output"
    ml_model_config_path: str = None  # None = utiliser le modèle le plus récent
    ml_test_n_flights: int = 1000  # Nombre de vols pour test en production
    enable_ml_prediction: bool = True  # Active la prédiction ML automatique après insertion PostgreSQL
    
    # Collecte
    num_airports: int = 200
    delay: float = 1.5
    batch_size: int = 500
    enable_weather: bool = True
    hour_offset: int = 1  # Décalage pour vols temps réel (1 = prochaine heure)
    past_hour_offset: int = -20  # Décalage pour vols passés (négatif = heures passées)
    
    # Comportement d'exécution
    run_once: bool = True  # Si False, exécute en boucle
    collect_realtime: bool = True  # Si True, collecte vols temps réel
    collect_past: bool = False  # Si True, collecte vols passés
    
    # Scheduling pour les boucles (si run_once = False)
    schedule_minute: int = 5  # XX:05
    loop_interval_minutes: int = 60
    
    # Logging
    log_level: str = "INFO"
    log_to_console: bool = True
    log_to_file: bool = True
    
    # Métadonnées
    script_version: str = "2.0"
    source: str = "airportinfo.live"


@dataclass
class CollectionResults:
    """Résultats d'une collecte"""
    success: bool = False
    collection_session_id: str = ""
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0
    flights_collected: int = 0
    flights_inserted: int = 0
    metar_collected: int = 0
    metar_inserted: int = 0
    taf_collected: int = 0
    taf_inserted: int = 0
    mongodb_connected: bool = False
    
    # Machine Learning
    ml_predictions_generated: int = 0
    ml_predictions_saved: int = 0
    ml_avg_delay_probability: float = 0.0
    ml_risk_distribution: dict = None  # Distribution des niveaux de risque
    
    errors: List[str] = None
    details: dict = None  # Détails supplémentaires (ex: inserted_flight_ids)
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.details is None:
            self.details = {}
        if self.ml_risk_distribution is None:
            self.ml_risk_distribution = {}


def get_default_config() -> CollectionConfig:
    """Retourne la configuration par défaut"""
    return CollectionConfig()
