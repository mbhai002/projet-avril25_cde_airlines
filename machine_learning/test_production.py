#!/usr/bin/env python3
"""
Script simplifié de test du modèle ML en production
Récupère les N derniers vols, applique le modèle et sauvegarde les prédictions
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire du projet au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.collection_config import get_default_config
from config.simple_logger import get_logger
from utils.postgresql_manager import PostgreSQLManager
from flight_delay_predictor import FlightDelayPredictor


def find_latest_model_config(model_dir: str) -> str:
    """
    Trouve le fichier de configuration du modèle le plus récent
    
    Args:
        model_dir: Répertoire contenant les modèles
    
    Returns:
        str: Chemin vers le fichier de config le plus récent
    
    Raises:
        FileNotFoundError: Si aucun fichier de config trouvé
    """
    model_path = Path(model_dir)
    if not model_path.exists():
        raise FileNotFoundError(f"Répertoire modèle introuvable: {model_dir}")
    
    config_files = list(model_path.glob("production_config_*.json"))
    if not config_files:
        raise FileNotFoundError(f"Aucun fichier de configuration trouvé dans {model_dir}")
    
    # Retourner le plus récent
    latest = max(config_files, key=lambda p: p.stat().st_mtime)
    return str(latest)


def main():
    """
    Pipeline complet de test en production
    """
    logger = get_logger(__name__)
    config = get_default_config()
    
    logger.info("\n" + "=" * 70)
    logger.info("🧪 TEST DU MODÈLE ML EN PRODUCTION")
    logger.info("=" * 70)
    
    start_time = datetime.now()
    
    try:
        # 1. Déterminer le chemin du modèle
        if config.ml_model_config_path:
            model_config = config.ml_model_config_path
            logger.info(f"📂 Utilisation du modèle spécifié: {model_config}")
        else:
            model_config = find_latest_model_config(config.ml_model_dir)
            logger.info(f"📂 Utilisation du modèle le plus récent: {model_config}")
        
        # 2. Charger le modèle
        logger.info("🤖 Chargement du modèle ML...")
        predictor = FlightDelayPredictor.load_model(model_config)
        predictor.display_model_summary()
        
        # 3. Connexion PostgreSQL
        logger.info(f"🔌 Connexion à PostgreSQL ({config.postgresql_uri})...")
        pg = PostgreSQLManager(config.postgresql_uri)
        if not pg.connect():
            raise Exception("Impossible de se connecter à PostgreSQL")
        
        # 4. Récupérer les données
        logger.info(f"📊 Récupération des {config.ml_test_n_flights} derniers vols...")
        df = pg.fetch_last_n_flights(config.ml_test_n_flights)
        logger.info(f"✅ {len(df)} vols récupérés")
        
        # 5. Sauvegarder temporairement en CSV
        temp_csv = Path(__file__).parent / "temp_flights_for_prediction.csv"
        airports_ref = Path(__file__).parent.parent / "utils" / "airports_ref.csv"
        
        logger.info("💾 Préparation des données pour prédiction...")
        df.to_csv(temp_csv, index=False)
        
        # 6. Prédire
        logger.info("🔮 Application du modèle de prédiction...")
        predictions = predictor.predict_from_csv(
            str(temp_csv),
            str(airports_ref),
            include_probability=True
        )
        
        logger.info(f"✅ {len(predictions)} prédictions générées")
        logger.info(f"   Retards prédits: {predictions['prediction'].sum()}")
        if 'delay_probability' in predictions.columns:
            logger.info(f"   Probabilité moyenne: {predictions['delay_probability'].mean():.2%}")
        
        # Afficher distribution des niveaux de risque
        if 'risk_level' in predictions.columns:
            risk_counts = predictions['risk_level'].value_counts()
            logger.info(f"\n📊 Distribution des niveaux de risque:")
            for level, count in risk_counts.items():
                pct = (count / len(predictions)) * 100
                logger.info(f"   {level}: {count} ({pct:.1f}%)")
        
        # 7. Sauvegarder dans PostgreSQL
        logger.info("\n💾 Sauvegarde des prédictions dans PostgreSQL...")
        updated_count = pg.update_flight_predictions(predictions)
        
        # 8. Nettoyage
        if temp_csv.exists():
            temp_csv.unlink()
        
        # 9. Statistiques finales
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ TEST TERMINÉ AVEC SUCCÈS")
        logger.info("=" * 70)
        logger.info(f"Vols récupérés: {len(df)}")
        logger.info(f"Prédictions générées: {len(predictions)}")
        logger.info(f"Mises à jour PostgreSQL: {updated_count}")
        logger.info(f"Durée totale: {duration:.1f}s")
        logger.info("=" * 70)
        
        # Fermer la connexion
        pg.disconnect()
        
        return {
            'success': True,
            'flights_processed': len(df),
            'predictions_made': len(predictions),
            'database_updates': updated_count,
            'duration_seconds': duration
        }
        
    except Exception as e:
        logger.error(f"\n❌ ERREUR: {e}")
        logger.error("=" * 70)
        
        # Nettoyage en cas d'erreur
        temp_csv = Path(__file__).parent / "temp_flights_for_prediction.csv"
        if temp_csv.exists():
            temp_csv.unlink()
        
        return {
            'success': False,
            'error': str(e)
        }


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result['success'] else 1)
