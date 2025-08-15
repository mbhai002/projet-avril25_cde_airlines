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
    database_name: str = "dst_airlines3"
    collection_name: str = "flights"
    
    # Collecte
    num_airports: int = 200
    delay: float = 1.5
    batch_size: int = 500
    enable_xml_weather: bool = True
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
    metar_xml_collected: int = 0
    metar_xml_inserted: int = 0
    taf_xml_collected: int = 0
    taf_xml_inserted: int = 0
    mongodb_connected: bool = False
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def get_default_config() -> CollectionConfig:
    """Retourne la configuration par défaut"""
    return CollectionConfig()
