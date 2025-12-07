#!/usr/bin/env python3
"""
Configuration du logging pour le projet DST Airlines
"""

import logging
import os
import atexit
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler, QueueHandler, QueueListener
from queue import Queue


_queue_listener = None


def setup_simple_logger(name: str = __name__, level: str = "INFO") -> logging.Logger:
    """
    Configure un logger simple avec console et fichier (thread-safe pour Windows)
    
    Args:
        name: Nom du logger
        level: Niveau de log (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Logger configuré
    """
    global _queue_listener
    
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
    
    # Handler fichier avec rotation journalière (évite les problèmes de verrouillage Windows)
    log_filename = os.path.join(logs_dir, "application.log")
    file_handler = TimedRotatingFileHandler(
        log_filename,
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8',
        delay=False
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Utiliser une queue pour thread-safety (solution recommandée pour Windows multi-thread)
    if _queue_listener is None:
        log_queue = Queue(-1)
        queue_handler = QueueHandler(log_queue)
        
        _queue_listener = QueueListener(log_queue, console_handler, file_handler, respect_handler_level=True)
        _queue_listener.start()
        
        # Arrêter proprement le listener à la fin
        atexit.register(_queue_listener.stop)
        
        logger.addHandler(queue_handler)
    else:
        queue_handler = QueueHandler(_queue_listener.queue)
        logger.addHandler(queue_handler)
    
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
