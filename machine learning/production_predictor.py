#!/usr/bin/env python3
"""
Classe de production pour l'utilisation simplifiée du modèle de prédiction de retards
"""

from typing import Dict
import pandas as pd
from pathlib import Path

# Import de la classe principale
from flight_delay_predictor import FlightDelayPredictor


class FlightDelayProductionPredictor:
    """
    Classe simplifiée pour utiliser un modèle FlightDelayPredictor en production
    
    Cette classe fournit une interface simplifiée pour charger et utiliser
    un modèle pré-entraîné de prédiction de retards de vols.
    
    Exemple d'utilisation:
        # Charger le modèle
        predictor = FlightDelayProductionPredictor("model/production_config_20251104_084632.json")
        
        # Prédire à partir d'un CSV
        results = predictor.predict_from_csv("flights_to_predict.csv", "airports_ref.csv")
        
        # Prédire un vol unique
        flight = {
            'airline_code': 'AF',
            'from_airport': 'CDG',
            'to_airport': 'JFK',
            'wind_speed_kt': 15,
            # ... autres données
        }
        result = predictor.predict_flight(flight)
    """
    
    def __init__(self, config_path: str):
        """
        Initialise le prédicteur de production
        
        Args:
            config_path: Chemin vers le fichier de configuration du modèle
                        (fichier production_config_*.json généré lors de la sauvegarde)
        
        Raises:
            FileNotFoundError: Si le fichier de configuration n'existe pas
            ValueError: Si le fichier de configuration est invalide
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Fichier de configuration introuvable: {config_path}")
        
        print(f"📂 Chargement du modèle depuis: {config_path}")
        self.predictor = FlightDelayPredictor.load_model(config_path)
        self.config_path = config_path
        print("🚀 Prédicteur de production initialisé et prêt à l'usage!")
    
    def predict_from_csv(self, 
                        csv_path: str, 
                        airports_ref_path: str = "airports_ref.csv", 
                        output_path: str = None,
                        include_probability: bool = True) -> pd.DataFrame:
        """
        Prédit les retards à partir d'un fichier CSV
        
        Args:
            csv_path: Chemin vers le fichier CSV contenant les vols à prédire
            airports_ref_path: Chemin vers le fichier de référence des aéroports
            output_path: Chemin de sortie pour sauvegarder les résultats (optionnel)
            include_probability: Inclure la probabilité numérique dans le résultat
        
        Returns:
            DataFrame avec les colonnes:
                - id/f_id: Identifiant du vol
                - prediction: 0 (pas de retard) ou 1 (retard)
                - risk_level: "Faible", "Modéré" ou "Élevé"
                - delay_probability: Probabilité de retard (0-1) si include_probability=True
        
        Example:
            results = predictor.predict_from_csv(
                "data/flights_tomorrow.csv",
                "data/airports_ref.csv",
                "results/predictions.csv"
            )
            print(results.head())
        """
        return self.predictor.predict_from_csv(
            csv_path, 
            airports_ref_path, 
            output_path,
            include_probability
        )
    
    def predict_flight(self, flight_data: Dict) -> Dict:
        """
        Prédit le retard pour un vol unique
        
        Args:
            flight_data: Dictionnaire contenant les données du vol
                        Doit inclure les features nécessaires au modèle
        
        Returns:
            Dictionnaire avec:
                - prediction: 0 (pas de retard) ou 1 (retard)
                - delay_probability: Probabilité de retard (0-1)
                - risk_level: "Faible", "Modéré" ou "Élevé"
                - delay_expected: True si retard prédit, False sinon
        
        Example:
            flight = {
                'airline_code': 'AF',
                'from_airport': 'CDG',
                'to_airport': 'JFK',
                'wind_speed_kt': 15,
                'visibility_statute_mi': 10,
                # ... autres données météo et temporelles
            }
            result = predictor.predict_flight(flight)
            print(f"Probabilité de retard: {result['delay_probability']:.2%}")
        """
        return self.predictor.predict_single_flight(flight_data)
    
    def get_model_info(self) -> Dict:
        """
        Retourne les informations sur le modèle chargé
        
        Returns:
            Dictionnaire avec:
                - delay_threshold: Seuil de retard en minutes utilisé pour l'entraînement
                - optimal_threshold: Seuil de probabilité optimal pour la classification
                - training_metrics: Métriques d'entraînement du modèle
                - model_type: Type de modèle (XGBoost, RandomForest, etc.)
        
        Example:
            info = predictor.get_model_info()
            print(f"Type de modèle: {info['model_type']}")
            print(f"ROC-AUC: {info['training_metrics']['roc_auc']:.3f}")
        """
        return {
            'delay_threshold': self.predictor.delay_threshold,
            'optimal_threshold': self.predictor.optimal_threshold,
            'training_metrics': self.predictor.training_metrics,
            'model_type': type(self.predictor.model).__name__,
            'config_path': self.config_path
        }
    
    def display_model_summary(self):
        """
        Affiche un résumé formaté des informations du modèle
        """
        info = self.get_model_info()
        
        print("\n" + "=" * 60)
        print("📊 INFORMATIONS DU MODÈLE")
        print("=" * 60)
        print(f"Type de modèle: {info['model_type']}")
        print(f"Fichier de config: {info['config_path']}")
        print(f"Seuil de retard: {info['delay_threshold']} minutes")
        print(f"Seuil optimal: {info['optimal_threshold']:.3f}")
        
        if 'training_metrics' in info and info['training_metrics']:
            metrics = info['training_metrics']
            print(f"\n📈 MÉTRIQUES D'ENTRAÎNEMENT:")
            print(f"  ROC-AUC: {metrics.get('roc_auc', 'N/A'):.3f}")
            print(f"  PR-AUC: {metrics.get('pr_auc', 'N/A'):.3f}")
            print(f"  F1-Score: {metrics.get('f1_score', 'N/A'):.3f}")
            print(f"  Précision: {metrics.get('precision', 'N/A'):.3f}")
            print(f"  Rappel: {metrics.get('recall', 'N/A'):.3f}")
            
            if 'overfitting_analysis' in metrics:
                overfitting = metrics['overfitting_analysis']
                print(f"\n🔍 ANALYSE OVERFITTING:")
                print(f"  Statut: {overfitting.get('overfitting_status', 'N/A')}")
                print(f"  Écart moyen: {overfitting.get('average_gap_percent', 0):.1f}%")
        
        print("=" * 60)


# Exemple d'utilisation
if __name__ == "__main__":
    import sys
    
    print("🚀 DÉMO - FlightDelayProductionPredictor")
    print("=" * 60)
    
    # Vérifier si un fichier de configuration est fourni
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        # Chercher le fichier de config le plus récent dans le dossier model
        model_dir = Path(__file__).parent / "model"
        if model_dir.exists():
            config_files = list(model_dir.glob("production_config_*.json"))
            if config_files:
                config_path = str(max(config_files, key=lambda p: p.stat().st_mtime))
                print(f"📁 Utilisation du fichier de config le plus récent: {config_path}")
            else:
                print("❌ Aucun fichier de configuration trouvé dans ./model/")
                print("   Veuillez spécifier le chemin: python production_predictor.py <config_path>")
                sys.exit(1)
        else:
            print("❌ Dossier model/ introuvable")
            print("   Veuillez spécifier le chemin: python production_predictor.py <config_path>")
            sys.exit(1)
    
    try:
        # Charger le modèle
        predictor = FlightDelayProductionPredictor(config_path)
        
        # Afficher les informations du modèle
        predictor.display_model_summary()
        
        print("\n✅ Prédicteur prêt à l'utilisation!")
        print("\nExemples d'utilisation:")
        print("  1. Prédire à partir d'un CSV:")
        print("     results = predictor.predict_from_csv('data.csv', 'airports_ref.csv')")
        print("\n  2. Prédire un vol unique:")
        print("     result = predictor.predict_flight({...})")
        
    except Exception as e:
        print(f"❌ Erreur lors du chargement: {e}")
        sys.exit(1)
