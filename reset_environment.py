#!/usr/bin/env python3
"""
Script de réinitialisation de l'environnement
Supprime la base MongoDB et truncate les tables PostgreSQL
"""

import sys
import os
import psycopg2
from datetime import datetime

# Ajouter le répertoire du projet au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.collection_config import CollectionConfig
from utils.mongodb_manager import MongoDBManager


def reset_mongodb(config: CollectionConfig):
    """Supprime la base MongoDB dst_airlines_test"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🗑️  Réinitialisation MongoDB...")
    
    try:
        # Connexion MongoDB avec le manager
        mongo_manager = MongoDBManager(config.mongodb_uri, config.database_name)
        
        if not mongo_manager.connect():
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Impossible de se connecter à MongoDB")
            return False
        
        # Lister les bases existantes
        databases = mongo_manager.client.list_database_names()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Bases MongoDB existantes: {databases}")
        
        if config.database_name in databases:
            # Supprimer la base complète
            mongo_manager.client.drop_database(config.database_name)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Base '{config.database_name}' supprimée avec succès")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ℹ️  Base '{config.database_name}' n'existe pas")
        
        mongo_manager.disconnect()
        
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Erreur MongoDB: {e}")
        return False
    
    return True


def reset_postgresql(config: CollectionConfig):
    """Truncate les tables PostgreSQL"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🗑️  Réinitialisation PostgreSQL...")
    
    if not hasattr(config, 'postgresql_uri') or not config.postgresql_uri:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  Configuration PostgreSQL manquante")
        return True
    
    try:
        # Connexion PostgreSQL
        conn = psycopg2.connect(config.postgresql_uri)
        cursor = conn.cursor()
        
        # Tables à vider (dans l'ordre pour respecter les contraintes FK)
        tables_to_truncate = [
            'sky_condition',
            'flight',  # Table principale avec FK vers metar et taf
            'taf',     # Tables météo
            'metar'
            
        ]
        
        # Vérifier quelles tables existent
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Tables PostgreSQL existantes: {existing_tables}")
        
        # Truncate les tables existantes
        truncated_count = 0
        for table in tables_to_truncate:
            if table in existing_tables:
                try:
                    # Utiliser CASCADE pour gérer les contraintes FK
                    cursor.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")
                    truncated_count += 1
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Table '{table}' vidée")
                except Exception as e:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  Erreur lors du truncate de '{table}': {e}")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ℹ️  Table '{table}' n'existe pas")
        
        # Valider les changements
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {truncated_count} tables PostgreSQL vidées avec succès")
        
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Erreur PostgreSQL: {e}")
        return False
    
    return True


def main():
    """Point d'entrée principal"""
    print("=" * 60)
    print("🔄 SCRIPT DE RÉINITIALISATION DE L'ENVIRONNEMENT")
    print("=" * 60)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Début de la réinitialisation...")
    
    # Charger la configuration
    try:
        config = CollectionConfig()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Configuration chargée:")
        print(f"  - MongoDB: {config.database_name}")
        print(f"  - PostgreSQL: {'Activé' if hasattr(config, 'postgresql_uri') and config.postgresql_uri else 'Désactivé'}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Erreur lors du chargement de la configuration: {e}")
        return 1
    
    # Demander confirmation
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ⚠️  ATTENTION: Cette opération va:")
    print(f"  1. Supprimer TOUTE la base MongoDB '{config.database_name}'")
    print(f"  2. Vider TOUTES les tables PostgreSQL (metar, taf, flight)")
    print(f"  3. TOUTES LES DONNÉES SERONT PERDUES DÉFINITIVEMENT")
    
    confirmation = input(f"\n[{datetime.now().strftime('%H:%M:%S')}] Êtes-vous sûr de vouloir continuer? (tapez 'OUI' pour confirmer): ")
    
    if confirmation.upper() != 'OUI':
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏹️  Opération annulée par l'utilisateur")
        return 0
    
    success_mongodb = success_postgresql = True
    
    # Réinitialiser MongoDB
    success_mongodb = reset_mongodb(config)
    
    # Réinitialiser PostgreSQL
    if hasattr(config, 'postgresql_uri') and config.postgresql_uri:
        success_postgresql = reset_postgresql(config)
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏭️  PostgreSQL ignoré (non configuré)")
    
    # Résumé final
    print("\n" + "=" * 60)
    if success_mongodb and success_postgresql:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Réinitialisation terminée avec SUCCÈS")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎯 L'environnement est maintenant propre et prêt")
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  Réinitialisation terminée avec des ERREURS")
        print(f"  - MongoDB: {'✅' if success_mongodb else '❌'}")
        print(f"  - PostgreSQL: {'✅' if success_postgresql else '❌'}")
    
    print("=" * 60)
    return 0 if (success_mongodb and success_postgresql) else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ⏹️  Opération interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ❌ Erreur inattendue: {e}")
        sys.exit(1)
