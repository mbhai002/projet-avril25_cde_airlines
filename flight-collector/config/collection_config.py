#!/usr/bin/env python3
"""
Configuration enrichie pour le collecteur de vols
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import List
from dotenv import load_dotenv

load_dotenv()


def str_to_bool(value: str) -> bool:
    """Convertit une chaîne en booléen"""
    return value.lower() in ('true', '1', 'yes', 'on')


class CollectionType(Enum):
    """Types de collecte disponibles"""
    REALTIME = "realtime_departures"
    PAST = "past_departures"


@dataclass
class CollectionConfig:
    """Configuration complète pour une collecte"""
    # Base de données MongoDB (Docker)
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://admin:admin123@localhost:27017/")
    database_name: str = os.getenv("MONGODB_DATABASE", "airlines_db")

    # PostgreSQL (Docker)
    enable_postgresql_insertion: bool = str_to_bool(os.getenv("ENABLE_POSTGRESQL_INSERTION", "true"))
    postgresql_uri: str = os.getenv("POSTGRESQL_URI", "postgresql://postgres:postgres@localhost:5432/airlines_db")
    
    # Machine Learning
    ml_model_dir: str = os.getenv("ML_MODEL_DIR", "machine_learning/model_output")
    ml_model_config_path: str = None
    enable_ml_prediction: bool = str_to_bool(os.getenv("ENABLE_ML_PREDICTION", "true"))
    
    # Collecte
    num_airports: int = int(os.getenv("NUM_AIRPORTS", "200"))
    delay: float = float(os.getenv("DELAY", "1.5"))
    batch_size: int = int(os.getenv("BATCH_SIZE", "500"))
    enable_weather: bool = str_to_bool(os.getenv("ENABLE_WEATHER", "true"))
    hour_offset: int = int(os.getenv("HOUR_OFFSET", "1"))
    past_hour_offset: int = int(os.getenv("PAST_HOUR_OFFSET", "-20"))
    
    # Comportement d'exécution
    run_once: bool = str_to_bool(os.getenv("RUN_ONCE", "true"))
    collect_realtime: bool = str_to_bool(os.getenv("COLLECT_REALTIME", "true"))
    collect_past: bool = str_to_bool(os.getenv("COLLECT_PAST", "false"))
    
    # Scheduling pour les boucles (si run_once = False)
    schedule_minute: int = int(os.getenv("SCHEDULE_MINUTE", "5"))
    loop_interval_minutes: int = int(os.getenv("LOOP_INTERVAL_MINUTES", "60"))
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_to_console: bool = str_to_bool(os.getenv("LOG_TO_CONSOLE", "true"))
    log_to_file: bool = str_to_bool(os.getenv("LOG_TO_FILE", "true"))
    
    # FTP Upload
    enable_ftp_upload: bool = str_to_bool(os.getenv("ENABLE_FTP_UPLOAD", "true"))
    ftp_host: str = os.getenv("FTP_HOST", "")
    ftp_port: int = int(os.getenv("FTP_PORT", "21"))
    ftp_username: str = os.getenv("FTP_USERNAME", "")
    ftp_password: str = os.getenv("FTP_PASSWORD", "")
    ftp_use_tls: bool = str_to_bool(os.getenv("FTP_USE_TLS", "false"))
    ftp_remote_directory: str = os.getenv("FTP_REMOTE_DIRECTORY", "/data")
    
    # Cache Server (pour contourner Cloudflare)
    use_cache_server: bool = str_to_bool(os.getenv("USE_CACHE_SERVER", "false"))
    cache_server_url: str = os.getenv("CACHE_SERVER_URL", "https://dst.devlab.app/index.php")
    
    # Métadonnées
    script_version: str = os.getenv("SCRIPT_VERSION", "2.0")
    source: str = os.getenv("SOURCE", "airportinfo.live")


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


def get_ftp_config_from_collection_config(config: CollectionConfig) -> dict:
    """Extrait et retourne la configuration FTP depuis CollectionConfig"""
    if not config.enable_ftp_upload:
        return None
    
    return {
        'host': config.ftp_host,
        'port': config.ftp_port,
        'username': config.ftp_username,
        'password': config.ftp_password,
        'use_tls': config.ftp_use_tls,
        'remote_directory': config.ftp_remote_directory
    }
