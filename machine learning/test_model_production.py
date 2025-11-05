#!/usr/bin/env python3
"""
Script de test du modèle de prédiction en production
Récupère les 1000 dernières lignes de la view "all", 
applique le modèle et sauvegarde les probabilités dans PostgreSQL
"""

import sys
import os
from pathlib import Path
from typing import Dict
import pandas as pd
from datetime import datetime

# Ajouter le répertoire du projet au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from production_predictor import FlightDelayProductionPredictor
from utils.postgresql_manager import PostgreSQLManager
from config.simple_logger import get_logger


class ModelProductionTester:
    """
    Classe pour tester le modèle en production avec les données PostgreSQL
    """
    
    def __init__(self, db_uri: str, config_path: str):
        """
        Initialise le testeur
        
        Args:
            db_uri: URI de connexion PostgreSQL
            config_path: Chemin vers le fichier de configuration du modèle
        """
        self.logger = get_logger(__name__)
        
        # Utiliser le PostgreSQLManager existant
        self.pg_manager = PostgreSQLManager(db_uri)
        
        # Charger le modèle
        self.logger.info(f"🚀 Chargement du modèle depuis: {config_path}")
        self.predictor = FlightDelayProductionPredictor(config_path)
        self.predictor.display_model_summary()
    
    def fetch_last_n_flights(self, n: int = 1000) -> pd.DataFrame:
        """
        Récupère les N dernières lignes de la view "all"
        
        Args:
            n: Nombre de lignes à récupérer (défaut: 1000)
        
        Returns:
            DataFrame avec les données des vols
        """
        if not self.pg_manager.test_connection():
            raise Exception("Pas de connexion PostgreSQL")
        
        self.logger.info(f"📊 Récupération des {n} derniers vols depuis la view 'all'...")
        
        query = f"""
            SELECT * FROM public."all"
            ORDER BY f_id DESC
            LIMIT {n}
        """
        
        try:
            df = pd.read_sql_query(query, self.pg_manager.connection)
            self.logger.info(f"✅ {len(df)} lignes récupérées")
            
            return df
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la récupération des données: {e}")
            raise
    
    def predict_and_save(self, df: pd.DataFrame) -> int:
        """
        Applique le modèle sur les données et sauvegarde les résultats dans PostgreSQL
        
        Args:
            df: DataFrame avec les données des vols
        
        Returns:
            int: Nombre de lignes mises à jour
        """
        if not self.pg_manager.test_connection():
            raise Exception("Pas de connexion PostgreSQL")
        
        self.logger.info("🤖 Application du modèle de prédiction...")
        
        temp_csv = Path(__file__).parent / "temp_flights.csv"
        airports_ref = Path(__file__).parent.parent / "utils" / "airports_ref.csv"
        
        try:
            df.to_csv(temp_csv, index=False)
            
            predictions = self.predictor.predict_from_csv(
                str(temp_csv),
                str(airports_ref),
                include_probability=True
            )
            
            self.logger.info(f"✅ Prédictions: {len(predictions)} lignes")
            self.logger.info(f"   Retards prédits: {predictions['prediction'].sum()}")
            
            if 'delay_probability' in predictions.columns:
                self.logger.info(f"   Probabilité moyenne: {predictions['delay_probability'].mean():.2%}")
            
            updated_count = self._update_delay_probabilities(predictions)
            
            return updated_count
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la prédiction: {e}")
            raise
        finally:
            if temp_csv.exists():
                temp_csv.unlink()
    
    def _update_delay_probabilities(self, predictions: pd.DataFrame) -> int:
        """
        Met à jour les probabilités de retard et les niveaux de risque dans la table flight
        
        Args:
            predictions: DataFrame avec les colonnes f_id, delay_probability et risk_level
        
        Returns:
            int: Nombre de lignes mises à jour
        """
        self.logger.info("💾 Mise à jour des probabilités et niveaux de risque dans PostgreSQL...")
        
        cursor = None
        updated_count = 0
        
        try:
            cursor = self.pg_manager.connection.cursor()
            
            id_col = 'f_id' if 'f_id' in predictions.columns else 'id'
            prob_col = 'delay_probability' if 'delay_probability' in predictions.columns else 'probability'
            risk_col = 'risk_level'
            
            # Requête UPDATE pour probabilité ET niveau de risque
            update_query = "UPDATE flight SET delay_prob = %s, delay_risk_level = %s WHERE id = %s"
            
            for idx, row in predictions.iterrows():
                try:
                    flight_id = row[id_col]
                    delay_prob = row[prob_col]
                    risk_level = row.get(risk_col, None)
                    
                    if pd.notna(delay_prob):
                        cursor.execute(update_query, (
                            float(delay_prob), 
                            risk_level if pd.notna(risk_level) else None,
                            int(flight_id)
                        ))
                        if cursor.rowcount > 0:
                            updated_count += 1
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ Erreur vol {flight_id}: {e}")
                    continue
            
            self.pg_manager.connection.commit()
            self.logger.info(f"✅ {updated_count} lignes mises à jour (delay_prob + delay_risk_level)")
            
        except Exception as e:
            if self.pg_manager.connection:
                self.pg_manager.connection.rollback()
            self.logger.error(f"❌ Erreur lors de la mise à jour: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
        
        return updated_count
    
    def run_test(self, n_flights: int = 1000) -> Dict:
        """
        Lance le test complet
        
        Args:
            n_flights: Nombre de vols à traiter (défaut: 1000)
        
        Returns:
            Dict avec les statistiques du test
        """
        start_time = datetime.now()
        self.logger.info("\n" + "=" * 70)
        self.logger.info("🧪 TEST DU MODÈLE EN PRODUCTION")
        self.logger.info("=" * 70)
        
        stats = {'n_flights': n_flights, 'fetched': 0, 'updated': 0, 'success': False, 'error': None}
        
        try:
            if not self.pg_manager.connect():
                raise Exception("Impossible de se connecter à PostgreSQL")
            
            df = self.fetch_last_n_flights(n_flights)
            stats['fetched'] = len(df)
            
            if len(df) == 0:
                raise Exception("Aucune donnée récupérée")
            
            # predict_and_save s'occupe de la préparation ET de la prédiction (DRY!)
            updated_count = self.predict_and_save(df)
            stats['updated'] = updated_count
            stats['success'] = True
            
            duration = (datetime.now() - start_time).total_seconds()
            
            self.logger.info("\n" + "=" * 70)
            self.logger.info("✅ TEST TERMINÉ AVEC SUCCÈS")
            self.logger.info("=" * 70)
            self.logger.info(f"   Vols récupérés: {stats['fetched']}")
            self.logger.info(f"   Vols mis à jour: {stats['updated']}")
            self.logger.info(f"   Durée: {duration:.2f}s")
            self.logger.info("=" * 70 + "\n")
            
        except Exception as e:
            self.logger.error(f"\n❌ ERREUR: {e}")
            stats['error'] = str(e)
            stats['success'] = False
        
        finally:
            self.pg_manager.disconnect()
        
        return stats


def main():
    """Point d'entrée principal"""
    
    # Configuration - Import depuis le dossier machine learning
    script_dir = Path(__file__).parent
    config_file = script_dir / "config_test.py"
    
    if not config_file.exists():
        print(f"❌ Fichier config_test.py introuvable dans {script_dir}")
        sys.exit(1)
    
    # Charger la configuration
    import importlib.util
    spec = importlib.util.spec_from_file_location("config_test", config_file)
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
    
    POSTGRESQL_URI = config.POSTGRESQL_URI
    N_FLIGHTS_TO_TEST = config.N_FLIGHTS_TO_TEST
    MODEL_CONFIG_PATH = config.MODEL_CONFIG_PATH
    
    # Trouver le modèle
    if MODEL_CONFIG_PATH:
        config_path = MODEL_CONFIG_PATH
    else:
        model_dir = script_dir / "model_output"
        config_files = list(model_dir.glob("production_config_*.json"))
        if not config_files:
            print("❌ Aucun modèle trouvé dans ./model_output/")
            sys.exit(1)
        config_path = str(max(config_files, key=lambda p: p.stat().st_mtime))
    
    # Lancer le test
    tester = ModelProductionTester(POSTGRESQL_URI, config_path)
    stats = tester.run_test(n_flights=N_FLIGHTS_TO_TEST)
    
    sys.exit(0 if stats['success'] else 1)


if __name__ == "__main__":
    main()
