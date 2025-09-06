#!/usr/bin/env python3
"""
Point d'entrée simplifié pour le collecteur de vols
Configuration-driven, sans arguments CLI complexes
"""

import sys
import os
from datetime import datetime

# Ajouter le répertoire du projet au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.collection_config import CollectionConfig
from config.simple_logger import get_logger
from orchestration.execution_manager import ExecutionManager


def create_my_config() -> CollectionConfig:
       
    # === VOTRE CONFIGURATION ICI ===
    return CollectionConfig(
        # Base de données
        mongodb_uri="mongodb://localhost:27017/",
        database_name="dst_airlines_test5",

        # PostgreSQL
        enable_postgresql_insertion = True,
        postgresql_uri = "postgresql://postgres:cdps%40973@localhost:5433/dst3",

        # Collecte
        num_airports=2,
        delay=1.5,
        batch_size=500,
        enable_weather=True,  
        hour_offset=1,          # Décalage pour vols temps réel
        past_hour_offset=-20,   # Décalage pour vols passés
        
        # Comportement - Modifiez selon vos besoins
        run_once=True,              # True = une fois, False = en boucle
        collect_realtime=True,      # Collecte vols temps réel
        collect_past=True,          # Collecte vols passés
        
        # Scheduling (si run_once=False)
        schedule_minute=6,          # XX:05
        loop_interval_minutes=60,   # Toutes les heures
        
        # Logging
        log_level="INFO",
        log_to_console=True,
        log_to_file=True
    )


def main():
    """Point d'entrée principal"""
    print("=== COLLECTEUR DE VOLS ===")
    print(f"Démarrage à {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Créer la configuration
        config = create_my_config()
        
        # Afficher la configuration
        print("\nConfiguration active :")
        print(f"  - Run once: {config.run_once}")
        print(f"  - Collect realtime: {config.collect_realtime}")
        print(f"  - Collect past: {config.collect_past}")
        if not config.run_once:
            print(f"  - Schedule: XX:{config.schedule_minute:02d} toutes les {config.loop_interval_minutes} minutes")
        print(f"  - Database: {config.database_name}")
        print(f"  - Airports: {config.num_airports}")
        print(f"  - Weather: {config.enable_weather}")
        print("")
        
        # Exécuter
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
