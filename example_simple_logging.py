#!/usr/bin/env python3
"""
Exemple d'utilisation du système de logging simplifié
"""

import time
from config.simple_logger import get_logger, log_operation_time, log_database_operation

# Exemple simple
def example_basic_logging():
    """Exemple basique d'utilisation du logger"""
    logger = get_logger(__name__)
    
    logger.info("Début du traitement")
    logger.warning("Ceci est un avertissement")
    logger.error("Ceci est une erreur")
    
    # Simuler une opération avec timing
    start_time = time.time()
    time.sleep(0.1)  # Simuler du travail
    log_operation_time(logger, "data_processing", start_time)

def example_database_logging():
    """Exemple de logging d'opérations base de données"""
    logger = get_logger(__name__)
    
    # Simuler une insertion base de données
    start_time = time.time()
    time.sleep(0.05)  # Simuler l'insertion
    duration_ms = (time.time() - start_time) * 1000
    
    log_database_operation(
        logger, 
        "insert", 
        "flights", 
        150,  # nombre d'enregistrements
        duration_ms
    )

def example_error_handling():
    """Exemple de gestion d'erreurs avec logging"""
    logger = get_logger(__name__)
    
    try:
        # Simuler une erreur
        result = 1 / 0
    except ZeroDivisionError as e:
        logger.error(f"Erreur de division: {e}", exc_info=True)

if __name__ == "__main__":
    print("=== EXEMPLES DE LOGGING SIMPLIFIÉ ===")
    
    example_basic_logging()
    example_database_logging()
    example_error_handling()
    
    print("\nVérifiez le fichier logs/application.log pour voir tous les logs")
