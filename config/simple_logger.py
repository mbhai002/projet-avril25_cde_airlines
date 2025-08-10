#!/usr/bin/env python3
"""
Configuration simplifiée du logging pour le projet DST Airlines
Version allégée et plus facile à maintenir
"""

import logging
import os
from datetime import datetime


def setup_simple_logger(name: str = __name__, level: str = "INFO") -> logging.Logger:
    """
    Configure un logger simple avec console et fichier
    
    Args:
        name: Nom du logger
        level: Niveau de log (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Logger configuré
    """
    # Créer le répertoire logs s'il n'existe pas
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Créer le logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Éviter la duplication des handlers
    if logger.handlers:
        return logger
    
    # Format simple et lisible
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, level.upper()))
    logger.addHandler(console_handler)
    
    # Handler fichier simple
    log_filename = os.path.join(logs_dir, "application.log")
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)  # Tout sauvegarder dans le fichier
    logger.addHandler(file_handler)
    
    # Empêcher la propagation
    logger.propagate = False
    
    return logger


def log_operation_time(logger: logging.Logger, operation: str, start_time: float):
    """
    Helper pour logger le temps d'une opération
    
    Args:
        logger: Logger à utiliser
        operation: Nom de l'opération
        start_time: Temps de début (time.time())
    """
    import time
    duration = (time.time() - start_time) * 1000  # en ms
    logger.info(f"{operation} completed in {duration:.1f}ms")


def log_database_operation(logger: logging.Logger, operation: str, collection: str, count: int, duration_ms: float):
    """
    Helper pour logger une opération base de données
    
    Args:
        logger: Logger à utiliser
        operation: Type d'opération (insert, update, etc.)
        collection: Nom de la collection
        count: Nombre d'enregistrements
        duration_ms: Durée en millisecondes
    """
    logger.info(f"Database {operation}: {count} records in '{collection}' ({duration_ms:.1f}ms)")


# Raccourci pour obtenir un logger configuré
def get_logger(name: str = __name__) -> logging.Logger:
    """Raccourci simple pour obtenir un logger"""
    return setup_simple_logger(name)
