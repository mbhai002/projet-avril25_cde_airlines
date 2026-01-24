#!/usr/bin/env python3
"""
Point d'entrée simplifié pour le collecteur de vols
Configuration chargée depuis .env
"""

import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.collection_config import get_default_config
from config.simple_logger import get_logger
from orchestration.execution_manager import ExecutionManager


def main():
    """Point d'entrée principal"""
    print("=== COLLECTEUR DE VOLS ===")
    print(f"Démarrage à {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        config = get_default_config()
        
        # L'orchestration est maintenant gérée par Airflow
        print("\nNote: L'orchestration est gérée par Airflow.")
        print("Lancement d'une collecte unique...\n")
        
        manager = ExecutionManager(config)
        manager.run()
        
    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Arrêt demandé par l'utilisateur")
        sys.exit(0)
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Erreur fatale: {e}")
        print(f"ERREUR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
