#!/usr/bin/env python3
"""
Script de réinitialisation rapide (sans confirmation)
Pour les tests et développement
"""

import sys
import os
import psycopg2
from datetime import datetime

# Ajouter le répertoire du projet au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.collection_config import CollectionConfig
from utils.mongodb_manager import MongoDBManager


def quick_reset():
    """Reset rapide sans confirmation"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Reset rapide en cours...")
    
    config = CollectionConfig()
    config.database_name = "dst_airlines_test5"  # Assurez-vous d'utiliser la bonne DB
    config.postgresql_uri = "postgresql://postgres:cdps%40973@localhost:5433/dst3"

    # MongoDB
    try:
        mongo_manager = MongoDBManager(config.mongodb_uri, config.database_name)
        if mongo_manager.connect():
            # Vérifier si la base existe et la supprimer
            if config.database_name in mongo_manager.client.list_database_names():
                mongo_manager.client.drop_database(config.database_name)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ MongoDB '{config.database_name}' supprimée")
            mongo_manager.disconnect()
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  Impossible de se connecter à MongoDB")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  MongoDB: {e}")
    
    # PostgreSQL
    if hasattr(config, 'postgresql_uri') and config.postgresql_uri:
        try:
            conn = psycopg2.connect(config.postgresql_uri)
            cursor = conn.cursor()
            
            tables = ['sky_condition', 'flight', 'taf', 'metar']
            for table in tables:
                try:
                    cursor.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Table '{table}' vidée")
                except:
                    pass  # Table n'existe peut-être pas
            
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  PostgreSQL: {e}")
    
    # effacer les logs
    

    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Reset rapide terminé")


if __name__ == "__main__":
    quick_reset()
