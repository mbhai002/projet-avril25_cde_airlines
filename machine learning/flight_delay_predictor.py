"""
Flight Delay Predictor - Classe complète pour la prédiction des retards de vol
Refactorisé à partir du notebook machine_learning4.ipynb
Date: 27 septembre 2025
"""

import pandas as pd
import numpy as np
import warnings
import joblib
import json
from datetime import datetime, timedelta
from typing import Tuple, Dict, List, Optional, Union
from pathlib import Path

# Sklearn - Modèles
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler, RobustScaler, OneHotEncoder, OrdinalEncoder
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score, 
    precision_recall_curve, roc_curve, average_precision_score,
    f1_score, precision_score, recall_score
)

# Modèles de Machine Learning
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier

# Imbalanced-learn
from imblearn.combine import SMOTEENN
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import EditedNearestNeighbours

# XGBoost et LightGBM
import xgboost as xgb
from xgboost import XGBClassifier

# LightGBM (optionnel)
try:
    import lightgbm as lgb
    from lightgbm import LGBMClassifier
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    print("⚠️ LightGBM non installé. Utilisez: pip install lightgbm")

# Visualization
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings('ignore')


class FlightDelayPredictor:
    """
    Classe complète pour prédire les retards de vol en utilisant des données météorologiques
    et temporelles optimisées.
    
    Modèles supportés:
    - decision_tree: Arbre de décision
    - random_forest: Forêt aléatoire  
    - logistic_regression: Régression logistique
    - svm: Machine à vecteurs de support
    - knn: K plus proches voisins
    - xgboost: XGBoost standard
    - xgboost_tuned: XGBoost optimisé (recommandé)
    - lightgbm: LightGBM (si installé)
    """
    
    def __init__(self, 
                 delay_threshold: int = 15,
                 sample_size: Optional[int] = None,
                 random_state: int = 42,
                 output_dir: str = "machine learning/model_output"):
        """
        Initialise le prédicteur de retards de vol.
        
        Args:
            delay_threshold: Seuil en minutes pour considérer un vol en retard
            sample_size: Taille d'échantillon pour l'entraînement (None = toutes les données)
            random_state: Graine aléatoire pour la reproductibilité
            output_dir: Répertoire de sortie pour sauvegarder les modèles
        """
        self.delay_threshold = delay_threshold
        self.sample_size = sample_size
        self.random_state = random_state
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Configuration des caractéristiques
        self.numeric_features = [
            # Météo de base (vent, directions)
            'wind_speed_kt', 'wind_dir_degrees', 'wind_gust_kt', 
            't_wind_speed_kt', 't_wind_dir_degrees', 't_wind_gust_kt', 

            'departure_delay_minutes',
            'flight_duration_minutes',
            'airport_flight_count',
            'airline_flight_count',
            
            # Scores météo calculés
            'weather_severity_dep', 'weather_severity_arr',
            
            # Temps et durée
            'flight_duration_hours',
            
            # Caractéristiques temporelles
            'departure_hour_local', 'arrival_hour_local',
            'departure_dayofweek', 'arrival_dayofweek',
            'departure_month', 'departure_quarter', 'departure_day',
            
            # Indicateurs binaires temporels
            'is_rush_hour_dep', 'is_rush_hour_arr', 'is_weekend',
            'is_month_end', 'is_month_start',
            
            # Indicateurs météo binaires (optimisés)
            'dep_has_convective', 'dep_has_icing', 'dep_visibility_affected', 'dep_wind_affected',
            'arr_has_convective', 'arr_has_icing', 'arr_visibility_affected', 'arr_wind_affected'
        ]
        
        self.categorical_features = [
            # Aéroports et compagnies
            # 'airline_code', 'from_airport', 'to_airport',
            
            # Codes météo simplifiés (optimisés)
            'dep_weather_simplified', 'arr_weather_simplified',
            
            # Niveaux d'impact météo
            'dep_weather_impact', 'arr_weather_impact', 'overall_weather_impact'
        ]
        
        self.ordered_features = [
            'visibility_statute_mi', 't_visibility_statute_mi',     
            'msc_sky_cover', 'tsc_sky_cover'
        ]
        
        # Ordres pour l'encodage ordinal
        self.visibility_order = ['<1', '<2', '<3', '<4', '<5', '>=5']
        self.sky_cover_order = ['SKC', 'CAVOK', 'CLR', 'OVX', 'FEW', 'SCT', 'BKN', 'OVC']
        
        # Attributs initialisés lors de l'entraînement
        self.preprocessor = None
        self.model = None
        self.optimal_threshold = None
        self.class_weights = None
        self.feature_importance = None
        self.training_metrics = {}
    
    @staticmethod
    def get_available_models() -> Dict[str, str]:
        """
        Retourne la liste des modèles disponibles avec leurs descriptions
        
        Returns:
            Dictionnaire {nom_modele: description}
        """
        base_models = {
            'decision_tree': 'Arbre de décision - Simple et interprétable',
            'random_forest': 'Forêt aléatoire - Robuste, bon par défaut',
            'logistic_regression': 'Régression logistique - Rapide et linéaire',
            'svm': 'Machine à vecteurs de support - Puissant pour données complexes',
            'knn': 'K plus proches voisins - Simple, basé sur la similarité',
            'xgboost': 'XGBoost standard - Gradient boosting performant',
            'xgboost_tuned': 'XGBoost optimisé - Recommandé pour classes déséquilibrées'
        }
        
        if LIGHTGBM_AVAILABLE:
            base_models['lightgbm'] = 'LightGBM - Alternative rapide à XGBoost'
        
        return base_models
    
    @staticmethod
    def print_available_models():
        """Affiche la liste des modèles disponibles"""
        models = FlightDelayPredictor.get_available_models()
        
        print("🤖 MODÈLES DE ML DISPONIBLES:")
        print("=" * 50)
        
        for model_name, description in models.items():
            status = "✅" if model_name != 'lightgbm' or LIGHTGBM_AVAILABLE else "❌"
            print(f"{status} {model_name:18} : {description}")
        
        if not LIGHTGBM_AVAILABLE:
            print(f"\n💡 Pour activer LightGBM: pip install lightgbm")
        
        print(f"\n🎯 Recommandé: 'xgboost_tuned' pour classes déséquilibrées")
        
    def load_and_prepare_data(self, data_path: str, airports_ref_path: str, 
                              for_training: bool = True) -> pd.DataFrame:
        """
        Charge et prépare les données avec toutes les transformations nécessaires.
        
        Args:
            data_path: Chemin vers le fichier de données principal
            airports_ref_path: Chemin vers le fichier de référence des aéroports
            for_training: Si True, applique les filtres d'entraînement (nettoyage, filtrage temporel)
                         Si False, mode production sans filtres
            
        Returns:
            DataFrame préparé avec toutes les caractéristiques
        """
        
        # Chargement des données
        df = pd.read_csv(data_path)
        airports_ref = pd.read_csv(airports_ref_path, sep=';')[['code_iata', 'timezone']]
        
        print(f"✅ Données chargées: {len(df):,} lignes")
        
        # Nettoyage des trous uniquement pour l'entraînement
        if for_training:
            df = self._remove_data_gaps(df)
            print(f"✅ Données après nettoyage des trous: {len(df):,} lignes")
        
        # Préparation des données avec ou sans filtres selon le mode
        df = self._prepare_base_features(df, airports_ref, for_training=for_training)
        df = self._create_weather_features(df)
        df = self._create_temporal_features(df)
        
        # Création de la variable cible uniquement pour l'entraînement
        if for_training:
            df = self._create_target_variable(df)
            
            # Échantillonnage si nécessaire
            if self.sample_size and len(df) > self.sample_size:
                df = df.sample(n=self.sample_size, random_state=self.random_state)
                print(f"📊 Échantillonnage: {len(df):,} lignes conservées")
        
        print("✅ Préparation des données terminée")
        return df
    
    def _remove_data_gaps(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Supprime les vols d'une heure complète si TOUS les vols de cette heure
        ont un status_final manquant (NaN, vide, ou null).
        
        Args:
            df: DataFrame avec les données de vol
            
        Returns:
            DataFrame nettoyé sans les heures où tous les status_final sont manquants
        """
        if 'departure_scheduled_utc' not in df.columns:
            print("⚠️ Colonne departure_scheduled_utc non trouvée, pas de nettoyage")
            return df
            
        if 'status_final' not in df.columns:
            print("⚠️ Colonne status_final non trouvée, pas de nettoyage")
            return df
        
        # Convertir en datetime et trier
        df = df.copy()
        df['departure_scheduled_utc'] = pd.to_datetime(df['departure_scheduled_utc'], errors='coerce')
        
        # Supprimer les lignes avec des dates invalides
        initial_count = len(df)
        df = df.dropna(subset=['departure_scheduled_utc'])
        if len(df) < initial_count:
            print(f"⚠️ {initial_count - len(df)} lignes supprimées (dates invalides)")
        
        # Créer une colonne d'heure pour grouper
        df['departure_hour'] = df['departure_scheduled_utc'].dt.floor('H')
        
        # Analyser chaque heure
        hours_to_remove = []
        total_flights_to_remove = 0
        
        for hour, group in df.groupby('departure_hour'):
            # Vérifier si tous les status_final de cette heure sont manquants
            status_series = group['status_final']
            
            # Compter les status_final valides (non NaN, non vides, non null)
            valid_status = status_series.dropna()  # Supprime les NaN
            valid_status = valid_status[valid_status.astype(str).str.strip() != '']  # Supprime les vides
            valid_status = valid_status[valid_status.astype(str).str.lower() != 'null']  # Supprime les 'null'
            
            total_flights_in_hour = len(group)
            valid_status_count = len(valid_status)
            
            if valid_status_count == 0:
                # TOUS les status_final sont manquants pour cette heure
                hours_to_remove.append(hour)
                total_flights_to_remove += total_flights_in_hour
                print(f"  �️ Heure {hour}: {total_flights_in_hour} vols - TOUS status_final manquants")
            else:
                print(f"  ✅ Heure {hour}: {total_flights_in_hour} vols - {valid_status_count} status_final valides")
        
        # Supprimer les heures identifiées
        if hours_to_remove:
            print(f"🧹 Suppression de {len(hours_to_remove)} heures complètes avec status_final manquants:")
            for hour in hours_to_remove:
                flights_in_hour = len(df[df['departure_hour'] == hour])
                print(f"  📅 {hour} - {flights_in_hour} vols supprimés")
            
            # Créer le masque pour garder les lignes
            mask_to_keep = ~df['departure_hour'].isin(hours_to_remove)
            df_cleaned = df[mask_to_keep].reset_index(drop=True)
            
            print(f"📊 Total: {total_flights_to_remove} vols supprimés")
        else:
            df_cleaned = df
        
        # Nettoyer la colonne temporaire
        return df_cleaned.drop('departure_hour', axis=1)
    
    def _prepare_base_features(self, df: pd.DataFrame, airports_ref: pd.DataFrame, 
                               for_training: bool = True) -> pd.DataFrame:
        """
        Prépare les caractéristiques de base (colonnes, fuseaux horaires, etc.)
        
        Args:
            df: DataFrame avec les données brutes
            airports_ref: DataFrame de référence des aéroports
            for_training: Si True, applique les filtres d'entraînement
        """
        
        # Sélection des colonnes essentielles
        colonnes_a_garder = [
            'airline_code', 
            'from_airport', 
            'to_airport', 
            'status',
            'status_final', 
            'delay_min',
            'departure_scheduled_utc', 
            'departure_actual_utc',
            'arrival_scheduled_utc',
            'wind_speed_kt', 
            'wind_dir_degrees', 
            'wind_gust_kt',
            'visibility_statute_mi', 
            'msc_sky_cover', 'wx_string',
            't_wind_speed_kt', 
            't_wind_dir_degrees', 
            't_wind_gust_kt',
            't_visibility_statute_mi', 
            'tsc_sky_cover', 
            't_wx_string'
        ]
        
        df = df[colonnes_a_garder].copy()
        
        # Conversion de TOUTES les colonnes datetime
        datetime_columns = ['departure_scheduled_utc', 'departure_actual_utc', 'arrival_scheduled_utc']
        for col in datetime_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Conversion des colonnes numériques (pour éviter les erreurs de type)
        numeric_cols = ['visibility_statute_mi', 't_visibility_statute_mi', 
                       'wind_speed_kt', 'wind_gust_kt', 't_wind_speed_kt', 't_wind_gust_kt']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Filtrage temporel UNIQUEMENT pour l'entraînement. 
        # On n'entraine pas le modèle sur des données dont on a pas encore récupéré le statut final.
        if for_training:
            date_max = df['departure_scheduled_utc'].max()
            date_seuil = date_max - pd.Timedelta(hours=24)
            df = df[df['departure_scheduled_utc'] < date_seuil]
            print(f"✅ Filtrage temporel: {len(df):,} lignes conservées (< {date_seuil})")
        
        # Ajout des fuseaux horaires
        timezone_dict = airports_ref.set_index('code_iata')['timezone'].to_dict()
        df['departure_timezone'] = df['from_airport'].map(timezone_dict)
        df['arrival_timezone'] = df['to_airport'].map(timezone_dict)

        # Ajout du nombre de minute de retard au départ
        df['departure_delay_minutes'] = (df['departure_actual_utc'] - df['departure_scheduled_utc']).dt.total_seconds() / 60
        
        # Ajout de la durée du vol
        df['flight_duration_minutes'] = (df['arrival_scheduled_utc'] - df['departure_scheduled_utc']).dt.total_seconds() / 60

        # Ajout de l'importance de l'aéroport basée sur le nombre de vols
        df['airport_flight_count'] = df['from_airport'].map(df['from_airport'].value_counts(normalize=True))

        # Ajout de l'importance de la compagnie aérienne basée sur le nombre de vols
        df['airline_flight_count'] = df['airline_code'].map(df['airline_code'].value_counts(normalize=True))

        # Suppression des status CANCELLED UNIQUEMENT pour l'entraînement
        if for_training:
            df = df[df['status'] != 'CANCELLED']
            print(f"✅ Status CANCELLED exclus: {len(df):,} lignes conservées")

        return df
    
    def _create_weather_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Crée les caractéristiques météorologiques optimisées"""
        
        # Gestion des valeurs manquantes
        weather_cols = ['wind_speed_kt', 't_wind_speed_kt', 'wind_gust_kt', 't_wind_gust_kt']
        for col in weather_cols:
            if col in df.columns:
                df[col] = df[col].fillna(0)
        
        # Classification de la visibilité
        def visibility_to_class(vis):
            if pd.isna(vis):
                return np.nan
            elif vis < 1: return '<1'
            elif vis < 2: return '<2'
            elif vis < 3: return '<3'
            elif vis < 4: return '<4'
            elif vis < 5: return '<5'
            else: return '>=5'
        
        df['visibility_statute_mi'] = df['visibility_statute_mi'].apply(visibility_to_class)
        df['t_visibility_statute_mi'] = df['t_visibility_statute_mi'].apply(visibility_to_class)
        
        # Scores de sévérité météo
        df['weather_severity_dep'] = (
            (df['wind_speed_kt'] > 20).astype(int) + 
            (df['wind_gust_kt'] > 30).astype(int) +
            (df['visibility_statute_mi'].isin(['<1', '<2'])).astype(int)
        )
        
        df['weather_severity_arr'] = (
            (df['t_wind_speed_kt'] > 20).astype(int) + 
            (df['t_wind_gust_kt'] > 30).astype(int) +
            (df['t_visibility_statute_mi'].isin(['<1', '<2'])).astype(int)
        )
        
        # Traitement intelligent des codes wx_string
        df = self._process_weather_codes(df)
        
        return df
    
    def _process_weather_codes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Traite les codes météorologiques METAR en catégories optimisées"""
        
        def extract_impactful_weather_codes(wx_string):
            """Extrait les codes météo ayant un impact sur les retards"""
            if pd.isna(wx_string) or wx_string == '' or wx_string == 'nan':
                return {
                    'impact_level': 'none',
                    'simplified_code': 'CLEAR',
                    'convective': False,
                    'icing': False,
                    'visibility_impact': False,
                    'wind_impact': False
                }
            
            wx_str = str(wx_string).upper().strip()
            
            # Détection des phénomènes critiques
            thunderstorms = 'TS' in wx_str
            hail = 'GR' in wx_str
            fog = 'FG' in wx_str
            freezing = 'FZ' in wx_str
            snow = 'SN' in wx_str
            rain = 'RA' in wx_str
            squalls = 'SQ' in wx_str
            dust_storm = any(x in wx_str for x in ['SS', 'DS'])
            
            # Classification par impact
            if thunderstorms or hail or squalls or dust_storm:
                impact_level = 'high'
                if thunderstorms: simplified_code = 'THUNDERSTORM'
                elif hail: simplified_code = 'HAIL'
                elif dust_storm: simplified_code = 'DUST_STORM'
                else: simplified_code = 'THUNDERSTORM'
            elif fog or (freezing and (rain or snow)):
                impact_level = 'high' if fog else 'medium'
                simplified_code = 'FOG' if fog else 'ICING'
            elif snow or (rain and ('HVY' in wx_str or '+' in wx_str)):
                impact_level = 'medium'
                simplified_code = 'SNOW' if snow else 'RAIN'
            elif rain or 'DZ' in wx_str or 'BR' in wx_str:
                impact_level = 'low'
                simplified_code = 'LIGHT_WEATHER'
            else:
                impact_level = 'none'
                simplified_code = 'CLEAR'
            
            return {
                'impact_level': impact_level,
                'simplified_code': simplified_code,
                'convective': thunderstorms or squalls or hail,
                'icing': freezing or 'IC' in wx_str or 'PE' in wx_str,
                'visibility_impact': fog or 'BR' in wx_str,
                'wind_impact': thunderstorms or squalls
            }
        
        # Application aux colonnes météo
        for prefix, col in [('dep', 'wx_string'), ('arr', 't_wx_string')]:
            if col in df.columns:
                weather_info = df[col].apply(extract_impactful_weather_codes)
                
                df[f'{prefix}_weather_impact'] = [w['impact_level'] for w in weather_info]
                df[f'{prefix}_weather_simplified'] = [w['simplified_code'] for w in weather_info]
                df[f'{prefix}_has_convective'] = [w['convective'] for w in weather_info]
                df[f'{prefix}_has_icing'] = [w['icing'] for w in weather_info]
                df[f'{prefix}_visibility_affected'] = [w['visibility_impact'] for w in weather_info]
                df[f'{prefix}_wind_affected'] = [w['wind_impact'] for w in weather_info]
        
        # Impact météorologique global
        df['overall_weather_impact'] = 'none'
        high_mask = (df['dep_weather_impact'] == 'high') | (df['arr_weather_impact'] == 'high')
        medium_mask = ((df['dep_weather_impact'] == 'medium') | (df['arr_weather_impact'] == 'medium')) & (~high_mask)
        low_mask = ((df['dep_weather_impact'] == 'low') | (df['arr_weather_impact'] == 'low')) & (~high_mask) & (~medium_mask)
        
        df.loc[high_mask, 'overall_weather_impact'] = 'high'
        df.loc[medium_mask, 'overall_weather_impact'] = 'medium'
        df.loc[low_mask, 'overall_weather_impact'] = 'low'
        
        return df
    
    def _create_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Crée les caractéristiques temporelles avancées"""
        
        # Conversion UTC vers heure locale
        dep_utc = pd.to_datetime(df['departure_scheduled_utc'], utc=True, errors='coerce')
        arr_utc = pd.to_datetime(df['arrival_scheduled_utc'], utc=True, errors='coerce')
        
        def convert_utc_grouped(utc_series, tz_series):
            """Conversion vectorisée UTC -> local par groupes de fuseaux"""
            out = pd.Series(pd.NaT, index=utc_series.index, dtype='datetime64[ns]')
            for tz in tz_series.dropna().unique():
                mask = tz_series == tz
                try:
                    out.loc[mask] = utc_series.loc[mask].dt.tz_convert(tz).dt.tz_localize(None)
                except Exception:
                    pass
            return out
        
        df['departure_scheduled_local'] = convert_utc_grouped(dep_utc, df['departure_timezone'])
        df['arrival_scheduled_local'] = convert_utc_grouped(arr_utc, df['arrival_timezone'])
        
        # Caractéristiques temporelles de base
        df['departure_hour_local'] = df['departure_scheduled_local'].dt.hour
        df['arrival_hour_local'] = df['arrival_scheduled_local'].dt.hour
        df['departure_dayofweek'] = df['departure_scheduled_local'].dt.dayofweek
        df['arrival_dayofweek'] = df['arrival_scheduled_local'].dt.dayofweek
        
        # Caractéristiques temporelles avancées
        df['departure_month'] = df['departure_scheduled_local'].dt.month
        df['departure_quarter'] = df['departure_scheduled_local'].dt.quarter
        df['departure_day'] = df['departure_scheduled_local'].dt.day
        
        # Durée du vol (utilise les colonnes déjà converties)
        duration_seconds = (df['arrival_scheduled_utc'] - df['departure_scheduled_utc']).dt.total_seconds()
        df['flight_duration_hours'] = (duration_seconds / 3600).round(1)
        
        # Indicateurs temporels
        df['is_rush_hour_dep'] = df['departure_hour_local'].isin([7, 8, 17, 18, 19]).astype(int)
        df['is_rush_hour_arr'] = df['arrival_hour_local'].isin([7, 8, 17, 18, 19]).astype(int)
        df['is_weekend'] = (df['departure_dayofweek'] >= 5).astype(int)
        df['is_month_end'] = (df['departure_day'] > 25).astype(int)
        df['is_month_start'] = (df['departure_day'] <= 5).astype(int)
        
        return df
    
    def _create_target_variable(self, df: pd.DataFrame) -> pd.DataFrame:
        """Crée la variable cible (retard/pas de retard)"""

        # Remplacer les Na par 0 (si on a pas l'info on part du principe qu'il n'y a pas de retard)
        df['delay_min'] = df['delay_min'].fillna(0)

        # Créer la variable binaire de retard
        df['delay'] = (df['delay_min'] > self.delay_threshold).astype(int)
        
        print(f"📊 Distribution des retards (seuil {self.delay_threshold}min):")
        print(f"  Pas de retard: {(df['delay'] == 0).sum():,} ({(df['delay'] == 0).mean()*100:.1f}%)")
        print(f"  Retard: {(df['delay'] == 1).sum():,} ({(df['delay'] == 1).mean()*100:.1f}%)")
        
        return df
    
    def create_preprocessor(self) -> ColumnTransformer:
        """Crée le pipeline de preprocessing optimisé"""
        
        # Pipeline numérique
        numeric_transformer = Pipeline([
            ("imputer", SimpleImputer(missing_values=np.nan, strategy="median")),
            ("scaler", RobustScaler())
        ])
        
        # Pipeline catégoriel
        categorical_transformer = OneHotEncoder(
            drop="first", 
            handle_unknown="ignore", 
            sparse_output=False,
            max_categories=20
        )
        
        # Pipeline ordinal
        ordered_transformer = OrdinalEncoder(
            categories=[
                self.visibility_order, self.visibility_order,
                self.sky_cover_order, self.sky_cover_order
            ], 
            handle_unknown='use_encoded_value', 
            unknown_value=-1
        )
        
        # Assemblage du preprocesseur
        preprocessor = ColumnTransformer([
            ("num", numeric_transformer, self.numeric_features),
            ("cat", categorical_transformer, self.categorical_features),
            ("ord", ordered_transformer, self.ordered_features)
        ], 
        remainder='drop',
        n_jobs=-1
        )
        
        return preprocessor
    
    def balance_classes(self, X_train: np.ndarray, y_train: pd.Series) -> Tuple[np.ndarray, pd.Series]:
        """
        Applique SMOTEENN pour gérer le déséquilibre des classes
        
        Returns:
            Tuple des données rééquilibrées (X_train_balanced, y_train_balanced)
        """
        print("🔄 Rééquilibrage des classes avec SMOTEENN...")
        
        try:
            # Application de SMOTEENN (SMOTE + EditedNearestNeighbours)
            smoteenn = SMOTEENN(
                random_state=self.random_state,
                smote=SMOTE(random_state=self.random_state, k_neighbors=3),
                enn=EditedNearestNeighbours()
            )
            
            print(f"  Distribution avant: {dict(pd.Series(y_train).value_counts())}")
            X_balanced, y_balanced = smoteenn.fit_resample(X_train, y_train)
            print(f"  Distribution après: {dict(pd.Series(y_balanced).value_counts())}")
            print("  ✅ SMOTEENN appliqué avec succès")
            
            return X_balanced, y_balanced
            
        except Exception as e:
            print(f"  ❌ SMOTEENN échoué: {e}")
            print("  ⚠️ Utilisation des données originales")
            return X_train, y_train
    
    def train(self, df: pd.DataFrame, model_type: str = 'xgboost_tuned') -> Dict:
        """
        Entraîne le modèle de prédiction des retards
        
        Args:
            df: DataFrame préparé avec toutes les caractéristiques
            model_type: Type de modèle à utiliser
            
        Returns:
            Dictionnaire avec les métriques d'entraînement
        """
        print(f"🚀 Début de l'entraînement du modèle {model_type}...")
        
        # Préparation des données
        feature_cols = self.numeric_features + self.categorical_features + self.ordered_features
        existing_cols = [col for col in feature_cols if col in df.columns]
        
        X = df[existing_cols]
        y = df['delay']
        
        # Division train/test avec stratification
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=self.random_state, stratify=y
        )
        
        # Preprocessing
        self.preprocessor = self.create_preprocessor()
        
        # Mise à jour des listes de caractéristiques avec les colonnes existantes
        self.numeric_features = [col for col in self.numeric_features if col in existing_cols]
        self.categorical_features = [col for col in self.categorical_features if col in existing_cols]
        self.ordered_features = [col for col in self.ordered_features if col in existing_cols]
        
        # Recréer le preprocesseur avec les colonnes existantes
        self.preprocessor = ColumnTransformer([
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", RobustScaler())]), 
             self.numeric_features),
            ("cat", OneHotEncoder(drop="first", handle_unknown="ignore", sparse_output=False, max_categories=20), 
             self.categorical_features),
            ("ord", OrdinalEncoder(categories=[self.visibility_order, self.visibility_order, 
                                             self.sky_cover_order, self.sky_cover_order], 
                                 handle_unknown='use_encoded_value', unknown_value=-1), 
             self.ordered_features)
        ], remainder='drop', n_jobs=-1)
        
        X_train_trans = self.preprocessor.fit_transform(X_train)
        X_test_trans = self.preprocessor.transform(X_test)
        
        # Rééquilibrage des classes
        X_train_balanced, y_train_balanced = self.balance_classes(X_train_trans, y_train)
        
        # Calcul des poids de classe
        class_counts = np.bincount(y_train)
        self.class_weights = len(y_train) / (len(class_counts) * class_counts)
        
        # Création du modèle selon le type choisi
        self.model = self._create_model(model_type, y_train)
        
        # Entraînement
        print("  Entraînement du modèle...")
        self.model.fit(X_train_balanced, y_train_balanced)
        
        # Prédictions
        y_pred_proba = self.model.predict_proba(X_test_trans)[:, 1]
        
        # Optimisation du seuil
        self._optimize_threshold(y_test, y_pred_proba)
        
        # Calcul des seuils de risque automatiques basés sur la distribution
        self._calculate_risk_thresholds(y_test, y_pred_proba)
        
        # Calcul des métriques
        metrics = self._calculate_metrics(y_test, y_pred_proba, X_test_trans)
        
        # Stocker les dernières prédictions pour les graphiques
        self.last_y_true = y_test
        self.last_y_pred_proba = y_pred_proba
        
        # Importance des caractéristiques
        if hasattr(self.model, 'feature_importances_'):
            # Utiliser les vrais noms de features du preprocessor
            try:
                feature_names = self.preprocessor.get_feature_names_out()
                # Nettoyer les noms pour une meilleure lisibilité
                cleaned_names = []
                for name in feature_names:
                    if name.startswith('cat__'):
                        # Transformer cat__airline_code__AA en airline_code=AA
                        parts = name.split('__')
                        if len(parts) >= 3:
                            cleaned_name = f"{parts[1]}={parts[2]}"
                        else:
                            cleaned_name = name
                    elif name.startswith('num__'):
                        # Retirer le préfixe num__
                        cleaned_name = name.replace('num__', '')
                    elif name.startswith('ord__'):
                        # Retirer le préfixe ord__
                        cleaned_name = name.replace('ord__', '')
                    else:
                        cleaned_name = name
                    cleaned_names.append(cleaned_name)
                feature_names = cleaned_names
            except:
                # Fallback vers les noms génériques si erreur
                feature_names = (self.numeric_features + 
                               [f"cat_{i}" for i in range(len(self.categorical_features) * 10)] + 
                               self.ordered_features)
            
            # Ajuster la longueur des noms de caractéristiques
            n_features = len(self.model.feature_importances_)
            if len(feature_names) > n_features:
                feature_names = feature_names[:n_features]
            elif len(feature_names) < n_features:
                feature_names.extend([f"feature_{i}" for i in range(len(feature_names), n_features)])
            
            self.feature_importance = pd.DataFrame({
                'feature': feature_names[:n_features],
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
        
        self.training_metrics = metrics
        
        # 🔍 DÉTECTION AUTOMATIQUE DE L'OVERFITTING
        overfitting_analysis = self.detect_overfitting(
            X_train_balanced, y_train_balanced, 
            X_test_trans, y_test
        )
        
        # Ajouter les résultats d'overfitting aux métriques
        self.training_metrics['overfitting_analysis'] = overfitting_analysis
        
        print("✅ Entraînement terminé!")
        
        return metrics
    
    def get_detailed_feature_names(self) -> Dict[str, str]:
        """
        Retourne un mapping entre les noms de features génériques (cat_X) 
        et les vrais noms de colonnes après OneHot encoding.
        
        Returns:
            Dict[str, str]: Mapping feature_name -> real_column_name
        """
        if not hasattr(self, 'preprocessor') or self.preprocessor is None:
            print("❌ Le modèle doit être entraîné avant de pouvoir obtenir les noms de features détaillés")
            return {}
        
        try:
            # Obtenir les noms de features du ColumnTransformer
            feature_names = self.preprocessor.get_feature_names_out()
            
            # Créer un mapping détaillé
            mapping = {}
            for i, name in enumerate(feature_names):
                generic_name = f"feature_{i}" if i >= len(self.numeric_features) + len(self.categorical_features) * 10 + len(self.ordered_features) else None
                
                if i < len(self.numeric_features):
                    # Features numériques
                    mapping[self.numeric_features[i]] = name
                elif i < len(self.numeric_features) + len(feature_names[len(self.numeric_features):]):
                    # Features catégorielles et ordinales
                    cat_index = i - len(self.numeric_features)
                    generic_cat_name = f"cat_{cat_index}"
                    mapping[generic_cat_name] = name
            
            return mapping
            
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des noms de features: {e}")
            return {}
    
    def explain_feature_importance(self, top_n: int = 20) -> pd.DataFrame:
        """
        Affiche l'importance des features avec leurs vrais noms de colonnes.
        
        Args:
            top_n: Nombre de features les plus importantes à afficher
            
        Returns:
            DataFrame avec l'importance des features et leurs vrais noms
        """
        if not hasattr(self, 'feature_importance') or self.feature_importance is None:
            print("❌ Le modèle doit être entraîné avant de pouvoir expliquer l'importance des features")
            return pd.DataFrame()
        
        # Obtenir le mapping des noms
        feature_mapping = self.get_detailed_feature_names()
        
        # Créer une version enrichie du DataFrame d'importance
        detailed_importance = self.feature_importance.copy()
        detailed_importance['real_feature_name'] = detailed_importance['feature'].map(
            lambda x: feature_mapping.get(x, x)
        )
        
        # Afficher le top N
        top_features = detailed_importance.head(top_n)
        
        print(f"\n🎯 Top {top_n} des features les plus importantes:")
        print("=" * 80)
        for idx, row in top_features.iterrows():
            print(f"{row['feature']:15} -> {row['real_feature_name']:40} | Importance: {row['importance']:.4f}")
        
        return detailed_importance
    
    def show_readable_feature_importance(self, top_n: int = 20) -> None:
        """
        Affiche l'importance des features avec des descriptions en français compréhensibles.
        
        Args:
            top_n: Nombre de features les plus importantes à afficher
        """
        if not hasattr(self, 'feature_importance') or self.feature_importance is None:
            print("❌ Le modèle doit être entraîné avant de pouvoir afficher l'importance des features")
            return
        
        # Dictionnaire de traduction pour rendre les noms plus compréhensibles
        descriptions = {
            # Features numériques - météo
            'wind_speed_kt': '🌪️ Vitesse du vent au départ (nœuds)',
            'wind_gust_kt': '💨 Rafales de vent au départ (nœuds)',
            't_wind_speed_kt': '🌪️ Vitesse du vent à l\'arrivée (nœuds)',
            't_wind_gust_kt': '💨 Rafales de vent à l\'arrivée (nœuds)',
            'temperature_c': '🌡️ Température au départ (°C)',
            't_temperature_c': '🌡️ Température à l\'arrivée (°C)',
            'humidity_percent': '💧 Humidité au départ (%)',
            'pressure_altimeter_hg': '📊 Pression atmosphérique départ',
            'visibility_statute_mi': '👁️ Visibilité au départ',
            't_visibility_statute_mi': '👁️ Visibilité à l\'arrivée',
            
            # Features calculées
            'heat_index': '🔥 Indice de chaleur',
            'wind_chill': '❄️ Refroidissement éolien',
            'temp_diff': '🌡️ Différence de température départ-arrivée',
            'pressure_diff': '📊 Différence de pression départ-arrivée',
            'wind_speed_diff': '🌪️ Différence vitesse vent départ-arrivée',
            
            # Compagnies aériennes
            'airline_code=AA': '✈️ American Airlines',
            'airline_code=DL': '✈️ Delta Airlines', 
            'airline_code=UA': '✈️ United Airlines',
            'airline_code=WN': '✈️ Southwest Airlines',
            'airline_code=B6': '✈️ JetBlue Airways',
            'airline_code=AS': '✈️ Alaska Airlines',
            
            # Météo simplifiée
            'dep_weather_simplified=Rain': '🌧️ Pluie au départ',
            'dep_weather_simplified=Snow': '❄️ Neige au départ',
            'dep_weather_simplified=Fog': '🌫️ Brouillard au départ',
            'dep_weather_simplified=Clear': '☀️ Temps clair au départ',
            'arr_weather_simplified=Rain': '🌧️ Pluie à l\'arrivée',
            'arr_weather_simplified=Snow': '❄️ Neige à l\'arrivée',
            'arr_weather_simplified=Fog': '🌫️ Brouillard à l\'arrivée',
            'arr_weather_simplified=Clear': '☀️ Temps clair à l\'arrivée',
            
            # Impact météo
            'dep_weather_impact=High': '⚠️ Impact météo élevé au départ',
            'dep_weather_impact=Medium': '⚡ Impact météo moyen au départ',
            'dep_weather_impact=Low': '✅ Impact météo faible au départ',
            'arr_weather_impact=High': '⚠️ Impact météo élevé à l\'arrivée',
            'arr_weather_impact=Medium': '⚡ Impact météo moyen à l\'arrivée',
            'arr_weather_impact=Low': '✅ Impact météo faible à l\'arrivée',
            'overall_weather_impact=High': '🚨 Impact météo global élevé',
            'overall_weather_impact=Medium': '⚡ Impact météo global moyen',
            'overall_weather_impact=Low': '✅ Impact météo global faible',
        }
        
        print(f"\n🎯 TOP {top_n} - IMPORTANCE DES FACTEURS DE RETARD")
        print("=" * 80)
        
        for i, (_, row) in enumerate(self.feature_importance.head(top_n).iterrows(), 1):
            feature_name = row['feature']
            importance = row['importance']
            
            # Obtenir la description
            description = descriptions.get(feature_name, feature_name)
            
            # Calculer le pourcentage d'importance
            total_importance = self.feature_importance['importance'].sum()
            percentage = (importance / total_importance * 100) if total_importance > 0 else 0
            
            # Affichage formaté
            bar_length = int(importance * 50 / self.feature_importance['importance'].max())
            bar = "█" * bar_length + "▒" * (50 - bar_length)
            
            print(f"{i:2d}. {description}")
            print(f"    {bar} {importance:.4f} ({percentage:.1f}%)")
            print()
    
    def _create_model(self, model_type: str, y_train: pd.Series):
        """
        Crée le modèle de machine learning selon le type spécifié
        
        Args:
            model_type: Type de modèle à créer
            y_train: Labels d'entraînement pour calculer les poids
            
        Returns:
            Modèle initialisé
        """
        # Calcul du ratio de déséquilibre pour les modèles qui le supportent
        ratio = len(y_train[y_train == 0]) / len(y_train[y_train == 1])
        class_weight_dict = {0: 1, 1: ratio}
        
        print(f"  Création du modèle: {model_type}")
        print(f"  Ratio de déséquilibre: {ratio:.1f}:1")
        
        if model_type == 'decision_tree':
            return DecisionTreeClassifier(
                max_depth=10,
                min_samples_split=20,
                min_samples_leaf=10,
                class_weight='balanced',
                random_state=self.random_state
            )
            
        elif model_type == 'random_forest':
            return RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=20,
                min_samples_leaf=10,
                class_weight='balanced',
                random_state=self.random_state,
                n_jobs=-1
            )
            
        elif model_type == 'logistic_regression':
            return LogisticRegression(
                class_weight='balanced',
                random_state=self.random_state,
                max_iter=1000,
                solver='liblinear'
            )
            
        elif model_type == 'svm':
            return SVC(
                kernel='rbf',
                class_weight='balanced',
                probability=True,  # Important pour predict_proba
                random_state=self.random_state,
                C=1.0
            )
            
        elif model_type == 'knn':
            return KNeighborsClassifier(
                n_neighbors=5,
                weights='distance',  # Pondération par distance
                n_jobs=-1
            )
            
        elif model_type == 'lightgbm':
            if not LIGHTGBM_AVAILABLE:
                raise ValueError("LightGBM n'est pas installé. Utilisez: pip install lightgbm")
            
            return LGBMClassifier(
                objective='binary',
                metric='binary_logloss',
                boosting_type='gbdt',
                n_estimators=100,
                max_depth=4,
                learning_rate=0.1,
                class_weight='balanced',
                random_state=self.random_state,
                verbose=-1
            )
            
        elif model_type == 'xgboost':
            return XGBClassifier(
                objective="binary:logistic",
                eval_metric=["aucpr","logloss"],
                tree_method="hist",
                n_estimators=2000,          # gros, mais on stoppe tôt
                learning_rate=0.05,         # plus doux
                max_depth=4,                # ↓ complexité
                min_child_weight=10,        # ↑ taille min des feuilles
                gamma=2,                    # pénalise les splits faibles
                reg_alpha=4,                # L1
                reg_lambda=6,               # L2
                subsample=0.7,              # bagging
                colsample_bytree=0.7,       # feature subsampling
                max_delta_step=2,           # stabilise updates classe rare
                scale_pos_weight=ratio,     # neg/pos sur le TRAIN COURANT
                random_state=42,
                n_jobs=-1
            )
            
        elif model_type == 'xgboost_tuned':
            return XGBClassifier(
                objective='binary:logistic',
                eval_metric='aucpr',  # Optimisé pour les classes déséquilibrées
                n_estimators=300,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                scale_pos_weight=ratio,
                reg_alpha=0.1,
                reg_lambda=0.1,
                random_state=self.random_state
            )
            
        else:
            available_models = [
                'decision_tree', 'random_forest', 'logistic_regression', 
                'svm', 'knn', 'xgboost', 'xgboost_tuned'
            ]
            if LIGHTGBM_AVAILABLE:
                available_models.append('lightgbm')
                
            raise ValueError(
                f"Type de modèle '{model_type}' non supporté.\n"
                f"Modèles disponibles: {available_models}"
            )
    
    def _optimize_threshold(self, y_true: pd.Series, y_pred_proba: np.ndarray):
        """Optimise le seuil de décision basé sur le F1-score"""
        
        precision, recall, thresholds = precision_recall_curve(y_true, y_pred_proba)
        f1_scores = 2 * (precision * recall) / (precision + recall)
        f1_scores = np.nan_to_num(f1_scores)
        
        optimal_idx = np.argmax(f1_scores)
        self.optimal_threshold = thresholds[optimal_idx]
        
        print(f"  🎯 Seuil optimal: {self.optimal_threshold:.3f} (F1: {f1_scores[optimal_idx]:.3f})")
    
    def _calculate_risk_thresholds(self, y_true: pd.Series, y_pred_proba: np.ndarray):
        """
        Calcule automatiquement les seuils de classification de risque
        basés sur la distribution des probabilités
        
        Méthode: Utilise les percentiles de la distribution pour définir 3 zones équilibrées
        """
        # Séparer les probabilités selon la classe réelle
        probs_no_delay = y_pred_proba[y_true == 0]
        probs_delay = y_pred_proba[y_true == 1]
        
        # Méthode 1: Point de séparation entre les deux distributions
        # On cherche où les deux distributions se chevauchent le moins
        median_no_delay = np.median(probs_no_delay)
        median_delay = np.median(probs_delay)
        
        # Seuil bas: médiane de la classe "pas de retard" (zone sûre)
        self.risk_threshold_low = median_no_delay
        
        # Seuil haut: le seuil optimal de décision (déjà calculé)
        self.risk_threshold_high = self.optimal_threshold
        
        print(f"  📊 Seuils de risque calculés automatiquement:")
        print(f"     • Faible/Modéré: {self.risk_threshold_low:.3f}")
        print(f"     • Modéré/Élevé:  {self.risk_threshold_high:.3f}")
        print(f"     → Basés sur: médiane(pas retard)={median_no_delay:.3f}, médiane(retard)={median_delay:.3f}")
    
    def _calculate_metrics(self, y_true: pd.Series, y_pred_proba: np.ndarray, X_test: np.ndarray) -> Dict:
        """Calcule les métriques de performance avec détection d'overfitting"""
        
        y_pred = (y_pred_proba >= self.optimal_threshold).astype(int)
        
        metrics = {
            'roc_auc': roc_auc_score(y_true, y_pred_proba),
            'pr_auc': average_precision_score(y_true, y_pred_proba),
            'f1_score': f1_score(y_true, y_pred),
            'precision': precision_score(y_true, y_pred),
            'recall': recall_score(y_true, y_pred),
            'optimal_threshold': float(self.optimal_threshold),
            'confusion_matrix': confusion_matrix(y_true, y_pred).tolist(),
            'n_test_samples': len(y_true),
            'test_class_distribution': y_true.value_counts().to_dict()
        }
        
        # Affichage des résultats
        print(f"\n📊 MÉTRIQUES DE PERFORMANCE:")
        print(f"  ROC-AUC: {metrics['roc_auc']:.3f}")
        print(f"  PR-AUC: {metrics['pr_auc']:.3f}")
        print(f"  F1-Score: {metrics['f1_score']:.3f}")
        print(f"  Précision: {metrics['precision']:.3f}")
        print(f"  Rappel: {metrics['recall']:.3f}")
        
        return metrics
    
    def detect_overfitting(self, X_train: np.ndarray, y_train: pd.Series, 
                          X_test: np.ndarray, y_test: pd.Series) -> Dict:
        """
        Détecte l'overfitting en comparant les performances sur les données d'entraînement et de test
        
        Args:
            X_train: Données d'entraînement préprocessées
            y_train: Labels d'entraînement 
            X_test: Données de test préprocessées
            y_test: Labels de test
            
        Returns:
            Dictionnaire avec les indicateurs d'overfitting
        """
        print(f"\n🔍 ANALYSE DE L'OVERFITTING")
        print("=" * 60)
        
        # Prédictions sur les données d'entraînement et de test
        train_proba = self.model.predict_proba(X_train)[:, 1]
        test_proba = self.model.predict_proba(X_test)[:, 1]
        
        train_pred = (train_proba >= self.optimal_threshold).astype(int)
        test_pred = (test_proba >= self.optimal_threshold).astype(int)
        
        # Calcul des métriques sur l'entraînement et le test
        train_metrics = {
            'roc_auc': roc_auc_score(y_train, train_proba),
            'pr_auc': average_precision_score(y_train, train_proba),
            'f1_score': f1_score(y_train, train_pred),
            'precision': precision_score(y_train, train_pred),
            'recall': recall_score(y_train, train_pred)
        }
        
        test_metrics = {
            'roc_auc': roc_auc_score(y_test, test_proba),
            'pr_auc': average_precision_score(y_test, test_proba),
            'f1_score': f1_score(y_test, test_pred),
            'precision': precision_score(y_test, test_pred),
            'recall': recall_score(y_test, test_pred)
        }
        
        # Calcul des écarts (indicateurs d'overfitting)
        overfitting_indicators = {}
        metric_names = ['roc_auc', 'pr_auc', 'f1_score', 'precision', 'recall']
        
        print("📈 COMPARAISON TRAIN vs TEST:")
        print("-" * 40)
        
        for metric in metric_names:
            train_val = train_metrics[metric]
            test_val = test_metrics[metric]
            gap = train_val - test_val
            gap_percent = (gap / train_val * 100) if train_val > 0 else 0
            
            overfitting_indicators[f'{metric}_gap'] = gap
            overfitting_indicators[f'{metric}_gap_percent'] = gap_percent
            overfitting_indicators[f'train_{metric}'] = train_val
            overfitting_indicators[f'test_{metric}'] = test_val
            
            # Interprétation de l'écart
            status = "🟢" if abs(gap_percent) < 5 else "🟡" if abs(gap_percent) < 10 else "🔴"
            print(f"{status} {metric.upper():>12}: Train={train_val:.3f} | Test={test_val:.3f} | Écart={gap:+.3f} ({gap_percent:+.1f}%)")
        
        # Validation croisée pour une évaluation plus robuste
        cv_scores = self._cross_validation_analysis(X_train, y_train)
        overfitting_indicators.update(cv_scores)
        
        # Évaluation globale de l'overfitting
        avg_gap_percent = np.mean([abs(overfitting_indicators[f'{m}_gap_percent']) for m in metric_names])
        overfitting_indicators['average_gap_percent'] = avg_gap_percent
        
        print(f"\n🎯 ÉVALUATION GLOBALE:")
        print(f"   Écart moyen: {avg_gap_percent:.1f}%")
        
        if avg_gap_percent < 5:
            overfitting_status = "Excellent"
            print(f"   ✅ Status: {overfitting_status} - Pas d'overfitting détecté")
        elif avg_gap_percent < 10:
            overfitting_status = "Bon"
            print(f"   🟡 Status: {overfitting_status} - Léger overfitting, acceptable")
        elif avg_gap_percent < 20:
            overfitting_status = "Moyen"
            print(f"   🟠 Status: {overfitting_status} - Overfitting modéré, à surveiller")
        else:
            overfitting_status = "Problématique"
            print(f"   🔴 Status: {overfitting_status} - Overfitting important détecté!")
        
        overfitting_indicators['overfitting_status'] = overfitting_status
        
        # Recommandations
        self._provide_overfitting_recommendations(overfitting_indicators)
        
        return overfitting_indicators
    
    def _cross_validation_analysis(self, X: np.ndarray, y: pd.Series) -> Dict:
        """
        Effectue une validation croisée pour détecter la stabilité du modèle
        
        Returns:
            Dictionnaire avec les résultats de validation croisée
        """
        print(f"\n🔄 VALIDATION CROISÉE (K-Fold=5):")
        print("-" * 40)
        
        # Configuration de la validation croisée stratifiée
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=self.random_state)
        
        # Métriques à évaluer
        scoring_metrics = ['roc_auc', 'f1', 'precision', 'recall']
        cv_results = {}
        
        for metric in scoring_metrics:
            scores = cross_val_score(self.model, X, y, cv=cv, scoring=metric, n_jobs=-1)
            
            cv_results[f'cv_{metric}_scores'] = scores.tolist()
            cv_results[f'cv_{metric}_mean'] = float(np.mean(scores))
            cv_results[f'cv_{metric}_std'] = float(np.std(scores))
            cv_results[f'cv_{metric}_min'] = float(np.min(scores))
            cv_results[f'cv_{metric}_max'] = float(np.max(scores))
            
            # Coefficient de variation (stabilité)
            cv_coeff = (np.std(scores) / np.mean(scores)) * 100 if np.mean(scores) > 0 else 0
            cv_results[f'cv_{metric}_stability'] = cv_coeff
            
            # Affichage
            stability_status = "🟢" if cv_coeff < 10 else "🟡" if cv_coeff < 20 else "🔴"
            print(f"{stability_status} {metric.upper():>12}: {np.mean(scores):.3f} ±{np.std(scores):.3f} | Stabilité: {cv_coeff:.1f}%")
        
        return cv_results
    
    def _provide_overfitting_recommendations(self, indicators: Dict):
        """
        Fournit des recommandations basées sur l'analyse d'overfitting
        """
        print(f"\n💡 RECOMMANDATIONS:")
        print("-" * 40)
        
        avg_gap = indicators['average_gap_percent']
        status = indicators['overfitting_status']
        
        if status == "Excellent":
            print("✅ Votre modèle est bien équilibré!")
            print("   • Les performances sont stables entre train et test")
            print("   • Aucune action corrective nécessaire")
            
        elif status == "Bon":
            print("🟡 Légère tendance à l'overfitting, mais acceptable:")
            print("   • Surveillez les performances sur de nouvelles données")
            print("   • Considérez l'arrêt précoce si disponible")
            
        elif status == "Moyen":
            print("🟠 Overfitting modéré détecté. Actions recommandées:")
            print("   • Augmentez la régularisation du modèle")
            print("   • Réduisez la complexité (max_depth, n_estimators)")
            print("   • Augmentez la taille des données d'entraînement")
            print("   • Utilisez plus de données de validation")
            
        else:  # Problématique
            print("🔴 Overfitting important! Actions urgentes:")
            print("   • Réduisez drastiquement la complexité du modèle")
            print("   • Augmentez fortement la régularisation")
            print("   • Collectez plus de données d'entraînement")
            print("   • Simplifiez les features (feature selection)")
            print("   • Utilisez l'arrêt précoce avec validation stricte")
        
        # Recommandations spécifiques par métrique
        if indicators.get('roc_auc_gap_percent', 0) > 15:
            print("   ⚠️ Écart ROC-AUC important: le modèle surapprend les patterns")
        
        if indicators.get('f1_score_gap_percent', 0) > 15:
            print("   ⚠️ Écart F1-Score important: réviser le seuil de décision")
        
        # Recommandations pour la validation croisée
        high_variance_metrics = []
        for metric in ['roc_auc', 'f1', 'precision', 'recall']:
            stability = indicators.get(f'cv_{metric}_stability', 0)
            if stability > 20:
                high_variance_metrics.append(metric)
        
        if high_variance_metrics:
            print(f"   📊 Variance élevée détectée sur: {', '.join(high_variance_metrics)}")
            print("   • Le modèle manque de stabilité - augmentez les données")

    def plot_learning_curves(self, X: np.ndarray, y: pd.Series, 
                           cv_folds: int = 5, figsize: tuple = (15, 10)) -> plt.Figure:
        """
        Trace les courbes d'apprentissage pour détecter visuellement l'overfitting
        
        Args:
            X: Données d'entraînement préprocessées
            y: Labels d'entraînement
            cv_folds: Nombre de folds pour la validation croisée
            figsize: Taille de la figure
            
        Returns:
            Figure matplotlib avec les courbes d'apprentissage
        """
        from sklearn.model_selection import learning_curve, validation_curve
        
        print(f"\n📈 GÉNÉRATION DES COURBES D'APPRENTISSAGE...")
        
        fig, axes = plt.subplots(2, 2, figsize=figsize)
        fig.suptitle("Analyse de l'Overfitting - Courbes d'Apprentissage", fontsize=16, fontweight='bold')
        
        # 1. Courbe d'apprentissage principale (taille d'entraînement vs performance)
        train_sizes = np.linspace(0.1, 1.0, 10)
        train_sizes_abs, train_scores, val_scores = learning_curve(
            self.model, X, y, 
            train_sizes=train_sizes,
            cv=cv_folds, 
            scoring='roc_auc',
            n_jobs=-1,
            random_state=self.random_state
        )
        
        # Calcul des moyennes et écarts-types
        train_mean = np.mean(train_scores, axis=1)
        train_std = np.std(train_scores, axis=1)
        val_mean = np.mean(val_scores, axis=1)
        val_std = np.std(val_scores, axis=1)
        
        axes[0, 0].plot(train_sizes_abs, train_mean, 'o-', color='blue', label='Score d\'entraînement')
        axes[0, 0].fill_between(train_sizes_abs, train_mean - train_std, train_mean + train_std, alpha=0.1, color='blue')
        axes[0, 0].plot(train_sizes_abs, val_mean, 'o-', color='red', label='Score de validation')
        axes[0, 0].fill_between(train_sizes_abs, val_mean - val_std, val_mean + val_std, alpha=0.1, color='red')
        
        axes[0, 0].set_xlabel('Taille de l\'échantillon d\'entraînement')
        axes[0, 0].set_ylabel('Score ROC-AUC')
        axes[0, 0].set_title('Courbe d\'Apprentissage (ROC-AUC)')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # Analyse de l'écart
        final_gap = train_mean[-1] - val_mean[-1]
        gap_text = f"Écart final: {final_gap:.3f}"
        gap_color = 'green' if abs(final_gap) < 0.05 else 'orange' if abs(final_gap) < 0.1 else 'red'
        axes[0, 0].text(0.02, 0.98, gap_text, transform=axes[0, 0].transAxes, 
                       verticalalignment='top', bbox=dict(boxstyle='round', facecolor=gap_color, alpha=0.3))
        
        # 2. Courbe de validation - Complexité du modèle
        if hasattr(self.model, 'n_estimators'):
            # Pour les modèles basés sur les arbres (RandomForest, XGBoost, etc.)
            param_name = 'n_estimators'
            param_range = [50, 100, 200, 300, 500, 800]
        elif hasattr(self.model, 'max_depth'):
            param_name = 'max_depth'
            param_range = [3, 5, 7, 10, 15, 20]
        elif hasattr(self.model, 'C'):
            param_name = 'C'
            param_range = [0.01, 0.1, 1, 10, 100, 1000]
        else:
            param_name = 'n_neighbors'
            param_range = [3, 5, 7, 10, 15, 20]
        
        try:
            train_scores_val, val_scores_val = validation_curve(
                self.model, X, y, param_name=param_name, param_range=param_range,
                cv=cv_folds, scoring='roc_auc', n_jobs=-1
            )
            
            train_mean_val = np.mean(train_scores_val, axis=1)
            train_std_val = np.std(train_scores_val, axis=1)
            val_mean_val = np.mean(val_scores_val, axis=1)
            val_std_val = np.std(val_scores_val, axis=1)
            
            axes[0, 1].plot(param_range, train_mean_val, 'o-', color='blue', label='Score d\'entraînement')
            axes[0, 1].fill_between(param_range, train_mean_val - train_std_val, train_mean_val + train_std_val, alpha=0.1, color='blue')
            axes[0, 1].plot(param_range, val_mean_val, 'o-', color='red', label='Score de validation')
            axes[0, 1].fill_between(param_range, val_mean_val - val_std_val, val_mean_val + val_std_val, alpha=0.1, color='red')
            
            axes[0, 1].set_xlabel(f'Paramètre: {param_name}')
            axes[0, 1].set_ylabel('Score ROC-AUC')
            axes[0, 1].set_title(f'Courbe de Validation - {param_name}')
            axes[0, 1].legend()
            axes[0, 1].grid(True, alpha=0.3)
            
            if param_name in ['C', 'n_estimators'] and len(param_range) > 3:
                axes[0, 1].set_xscale('log')
        except Exception as e:
            axes[0, 1].text(0.5, 0.5, f'Erreur courbe de validation:\n{str(e)}', 
                           transform=axes[0, 1].transAxes, ha='center', va='center')
            axes[0, 1].set_title('Courbe de Validation - Indisponible')
        
        # 3. Histogramme des résidus (pour détecter le biais)
        if hasattr(self, 'last_y_true') and hasattr(self, 'last_y_pred_proba'):
            residuals = self.last_y_true - self.last_y_pred_proba
            
            axes[1, 0].hist(residuals, bins=30, alpha=0.7, color='purple', edgecolor='black')
            axes[1, 0].axvline(np.mean(residuals), color='red', linestyle='--', 
                              label=f'Moyenne: {np.mean(residuals):.3f}')
            axes[1, 0].set_xlabel('Résidus (Réel - Prédit)')
            axes[1, 0].set_ylabel('Fréquence')
            axes[1, 0].set_title('Distribution des Résidus')
            axes[1, 0].legend()
            axes[1, 0].grid(True, alpha=0.3)
        else:
            axes[1, 0].text(0.5, 0.5, 'Résidus non disponibles\n(Entraînez d\'abord le modèle)', 
                           transform=axes[1, 0].transAxes, ha='center', va='center')
            axes[1, 0].set_title('Distribution des Résidus - Indisponible')
        
        # 4. Évolution des métriques par fold (stabilité)
        try:
            cv_roc_scores = cross_val_score(self.model, X, y, cv=cv_folds, scoring='roc_auc')
            cv_f1_scores = cross_val_score(self.model, X, y, cv=cv_folds, scoring='f1')
            
            folds = range(1, cv_folds + 1)
            axes[1, 1].plot(folds, cv_roc_scores, 'o-', label='ROC-AUC', linewidth=2, markersize=8)
            axes[1, 1].plot(folds, cv_f1_scores, 's-', label='F1-Score', linewidth=2, markersize=8)
            
            # Ligne de moyenne
            axes[1, 1].axhline(np.mean(cv_roc_scores), color='blue', linestyle=':', alpha=0.7, 
                              label=f'ROC-AUC moyen: {np.mean(cv_roc_scores):.3f}')
            axes[1, 1].axhline(np.mean(cv_f1_scores), color='orange', linestyle=':', alpha=0.7, 
                              label=f'F1 moyen: {np.mean(cv_f1_scores):.3f}')
            
            axes[1, 1].set_xlabel('Fold de Validation Croisée')
            axes[1, 1].set_ylabel('Score')
            axes[1, 1].set_title('Stabilité par Fold (Validation Croisée)')
            axes[1, 1].legend()
            axes[1, 1].grid(True, alpha=0.3)
            axes[1, 1].set_ylim(0, 1)
            
        except Exception as e:
            axes[1, 1].text(0.5, 0.5, f'Erreur validation croisée:\n{str(e)}', 
                           transform=axes[1, 1].transAxes, ha='center', va='center')
            axes[1, 1].set_title('Stabilité par Fold - Indisponible')
        
        plt.tight_layout()
        return fig

    def comprehensive_overfitting_report(self, X: np.ndarray, y: pd.Series, 
                                       save_plots: bool = True) -> Dict:
        """
        Génère un rapport complet d'analyse d'overfitting avec graphiques
        
        Args:
            X: Données préprocessées
            y: Labels
            save_plots: Si True, sauvegarde les graphiques
            
        Returns:
            Dictionnaire avec toutes les métriques d'overfitting
        """
        print(f"\n🔬 RAPPORT COMPLET D'ANALYSE D'OVERFITTING")
        print("=" * 80)
        
        # Division train/test pour l'analyse
        X_train_analysis, X_test_analysis, y_train_analysis, y_test_analysis = train_test_split(
            X, y, test_size=0.3, random_state=self.random_state, stratify=y
        )
        
        # Analyse d'overfitting détaillée
        overfitting_metrics = self.detect_overfitting(
            X_train_analysis, y_train_analysis, 
            X_test_analysis, y_test_analysis
        )
        
        # Génération des courbes d'apprentissage
        if len(X) > 1000:  # Seulement si suffisamment de données
            learning_curves_fig = self.plot_learning_curves(X, y)
            
            if save_plots:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                curves_path = self.output_dir / f"learning_curves_{timestamp}.png"
                learning_curves_fig.savefig(curves_path, dpi=300, bbox_inches='tight')
                print(f"📊 Courbes d'apprentissage sauvegardées: {curves_path}")
                overfitting_metrics['learning_curves_path'] = str(curves_path)
        
        # Rapport textuel détaillé
        report_path = self.output_dir / f"overfitting_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        self._save_overfitting_report(overfitting_metrics, report_path)
        
        return overfitting_metrics
    
    def _save_overfitting_report(self, metrics: Dict, report_path: Path):
        """Sauvegarde un rapport textuel détaillé de l'analyse d'overfitting"""
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("RAPPORT D'ANALYSE D'OVERFITTING\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Modèle: {type(self.model).__name__}\n")
            f.write(f"Seuil de retard: {self.delay_threshold} minutes\n\n")
            
            f.write("MÉTRIQUES TRAIN vs TEST:\n")
            f.write("-" * 30 + "\n")
            for metric in ['roc_auc', 'f1_score', 'precision', 'recall']:
                train_val = metrics.get(f'train_{metric}', 0)
                test_val = metrics.get(f'test_{metric}', 0)
                gap = metrics.get(f'{metric}_gap', 0)
                gap_percent = metrics.get(f'{metric}_gap_percent', 0)
                f.write(f"{metric.upper():>12}: Train={train_val:.3f} | Test={test_val:.3f} | Écart={gap:+.3f} ({gap_percent:+.1f}%)\n")
            
            f.write(f"\nÉCART MOYEN: {metrics.get('average_gap_percent', 0):.1f}%\n")
            f.write(f"STATUT: {metrics.get('overfitting_status', 'Inconnu')}\n\n")
            
            f.write("VALIDATION CROISÉE:\n")
            f.write("-" * 20 + "\n")
            for metric in ['roc_auc', 'f1', 'precision', 'recall']:
                mean_val = metrics.get(f'cv_{metric}_mean', 0)
                std_val = metrics.get(f'cv_{metric}_std', 0)
                stability = metrics.get(f'cv_{metric}_stability', 0)
                f.write(f"{metric.upper():>12}: {mean_val:.3f} ±{std_val:.3f} | Stabilité: {stability:.1f}%\n")
        
        print(f"📄 Rapport détaillé sauvegardé: {report_path}")

    def predict(self, X: Union[pd.DataFrame, np.ndarray], 
                threshold: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Effectue des prédictions sur de nouvelles données
        
        Args:
            X: Données à prédire
            threshold: Seuil de décision (utilise le seuil optimal si None)
            
        Returns:
            Tuple (probabilités, prédictions_binaires)
        """
        if self.model is None or self.preprocessor is None:
            raise ValueError("Le modèle doit être entraîné avant de faire des prédictions")
        
        if threshold is None:
            threshold = self.optimal_threshold
        
        # Preprocessing
        if isinstance(X, pd.DataFrame):
            X_processed = self.preprocessor.transform(X)
        else:
            X_processed = X
        
        # Prédictions
        probabilities = self.model.predict_proba(X_processed)[:, 1]
        predictions = (probabilities >= threshold).astype(int)
        
        return probabilities, predictions
    
    def save_model(self, timestamp: Optional[str] = None) -> Dict[str, str]:
        """
        Sauvegarde le modèle et ses composants
        
        Returns:
            Dictionnaire avec les chemins de sauvegarde
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        paths = {}
        
        # Sauvegarde du modèle
        model_path = self.output_dir / f"flight_delay_model_{timestamp}.joblib"
        joblib.dump(self.model, model_path)
        paths['model'] = str(model_path)
        
        # Sauvegarde du preprocesseur
        preprocessor_path = self.output_dir / f"preprocessor_{timestamp}.joblib"
        joblib.dump(self.preprocessor, preprocessor_path)
        paths['preprocessor'] = str(preprocessor_path)
        
        # Sauvegarde des métriques
        metrics_path = self.output_dir / f"model_metrics_{timestamp}.json"
        with open(metrics_path, 'w') as f:
            json.dump(self.training_metrics, f, indent=2)
        paths['metrics'] = str(metrics_path)
        
        # Sauvegarde de l'importance des caractéristiques
        if self.feature_importance is not None:
            importance_path = self.output_dir / f"feature_importance_{timestamp}.csv"
            self.feature_importance.to_csv(importance_path, index=False)
            paths['feature_importance'] = str(importance_path)
        
        # Configuration de production
        config = {
            'model_path': str(model_path),
            'preprocessor_path': str(preprocessor_path),
            'optimal_threshold': float(self.optimal_threshold),
            'delay_threshold': self.delay_threshold,
            'risk_threshold_low': float(getattr(self, 'risk_threshold_low', self.optimal_threshold * 0.67)),
            'risk_threshold_high': float(getattr(self, 'risk_threshold_high', self.optimal_threshold)),
            'feature_columns': {
                'numeric': self.numeric_features,
                'categorical': self.categorical_features,
                'ordered': self.ordered_features
            },
            'training_metrics': self.training_metrics
        }
        
        config_path = self.output_dir / f"production_config_{timestamp}.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        paths['config'] = str(config_path)
        
        print(f"✅ Modèle sauvegardé dans {self.output_dir}")
        for key, path in paths.items():
            print(f"  {key}: {Path(path).name}")
        
        return paths
    
    @classmethod
    def load_model(cls, config_path: str) -> 'FlightDelayPredictor':
        """
        Charge un modèle sauvegardé à partir de sa configuration
        
        Args:
            config_path: Chemin vers le fichier de configuration
            
        Returns:
            Instance de FlightDelayPredictor avec le modèle chargé
        """
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Créer une instance
        predictor = cls(
            delay_threshold=config['delay_threshold']
        )
        
        # Charger les composants
        predictor.model = joblib.load(config['model_path'])
        predictor.preprocessor = joblib.load(config['preprocessor_path'])
        predictor.optimal_threshold = config['optimal_threshold']
        predictor.training_metrics = config['training_metrics']
        
        # Charger les seuils de risque (avec fallback pour anciens modèles)
        predictor.risk_threshold_low = config.get('risk_threshold_low', predictor.optimal_threshold * 0.67)
        predictor.risk_threshold_high = config.get('risk_threshold_high', predictor.optimal_threshold)
        
        # Restaurer la configuration des caractéristiques
        predictor.numeric_features = config['feature_columns']['numeric']
        predictor.categorical_features = config['feature_columns']['categorical']
        predictor.ordered_features = config['feature_columns']['ordered']
        
        print(f"✅ Modèle chargé depuis {config_path}")
        return predictor
    
    def plot_performance_metrics(self, y_true: pd.Series, y_pred_proba: np.ndarray):
        """Génère les graphiques de performance du modèle"""
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. Courbe ROC
        fpr, tpr, _ = roc_curve(y_true, y_pred_proba)
        ax1.plot(fpr, tpr, color='blue', lw=2, label=f'ROC (AUC = {roc_auc_score(y_true, y_pred_proba):.3f})')
        ax1.plot([0, 1], [0, 1], color='red', lw=2, linestyle='--', label='Aléatoire')
        ax1.set_xlabel('Taux de Faux Positifs')
        ax1.set_ylabel('Taux de Vrais Positifs')
        ax1.set_title('Courbe ROC')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. Courbe Precision-Recall
        precision, recall, _ = precision_recall_curve(y_true, y_pred_proba)
        baseline = y_true.mean()
        ax2.plot(recall, precision, color='blue', lw=2, label=f'PR (AUC = {average_precision_score(y_true, y_pred_proba):.3f})')
        ax2.axhline(y=baseline, color='red', linestyle='--', label=f'Baseline ({baseline:.3f})')
        ax2.set_xlabel('Rappel')
        ax2.set_ylabel('Précision')
        ax2.set_title('Courbe Precision-Recall')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. Matrice de confusion
        y_pred = (y_pred_proba >= self.optimal_threshold).astype(int)
        cm = confusion_matrix(y_true, y_pred)
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax3)
        ax3.set_xlabel('Prédictions')
        ax3.set_ylabel('Valeurs Réelles')
        ax3.set_title(f'Matrice de Confusion (seuil = {self.optimal_threshold:.3f})')
        
        # 4. Distribution des probabilités
        ax4.hist(y_pred_proba[y_true == 0], bins=30, alpha=0.7, label='Pas de retard', color='green', density=True)
        ax4.hist(y_pred_proba[y_true == 1], bins=30, alpha=0.7, label='Retard', color='red', density=True)
        ax4.axvline(self.optimal_threshold, color='black', linestyle='--', label=f'Seuil optimal ({self.optimal_threshold:.3f})')
        ax4.set_xlabel('Probabilité de Retard')
        ax4.set_ylabel('Densité')
        ax4.set_title('Distribution des Probabilités')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def plot_last_performance(self):
        """
        Génère les graphiques de performance avec les dernières prédictions
        Version simplifiée pour utilisation après l'entraînement
        """
        if not hasattr(self, 'last_y_true') or not hasattr(self, 'last_y_pred_proba'):
            print("❌ Aucune prédiction disponible. Entraînez d'abord le modèle.")
            return None
            
        return self.plot_performance_metrics(self.last_y_true, self.last_y_pred_proba)

    def plot_feature_importance(self, top_n: int = 15, figsize: tuple = (12, 8)):
        """
        Affiche l'analyse de l'importance des features avec graphique et tableau
        
        Args:
            top_n: Nombre de features les plus importantes à afficher (défaut: 15)
            figsize: Taille de la figure (largeur, hauteur)
        """
        if self.feature_importance is None:
            print("❌ Aucune analyse d'importance disponible.")
            print("   L'importance des features n'est disponible que pour certains modèles")
            print("   (Random Forest, XGBoost, LightGBM, Decision Tree)")
            return
        
        print("=" * 60)
        print("📊 ANALYSE DE L'IMPORTANCE DES FEATURES")
        print("=" * 60)
        
        # Affichage du tableau des top features
        top_features = self.feature_importance.head(top_n)
        print(f"\n🔝 TOP {top_n} DES FEATURES LES PLUS IMPORTANTES:")
        print("-" * 50)
        print(top_features.to_string(index=False, 
                                   float_format=lambda x: f"{x:.4f}"))
        
        # Création du graphique horizontal
        plt.figure(figsize=figsize)
        
        # Graphique en barres horizontales (inversé pour avoir le plus important en haut)
        y_pos = range(len(top_features))
        plt.barh(y_pos, top_features['importance'], 
                color='steelblue', alpha=0.7, edgecolor='navy', linewidth=0.5)
        
        # Configuration des axes
        plt.yticks(y_pos, top_features['feature'])
        plt.xlabel('Importance', fontsize=12, fontweight='bold')
        plt.ylabel('Features', fontsize=12, fontweight='bold')
        plt.title(f'Top {top_n} - Importance des Features\n({self.model.__class__.__name__})', 
                 fontsize=14, fontweight='bold', pad=20)
        
        # Inversion de l'axe Y pour avoir le plus important en haut
        plt.gca().invert_yaxis()
        
        # Ajout des valeurs sur les barres
        for i, v in enumerate(top_features['importance']):
            plt.text(v + max(top_features['importance']) * 0.01, i, 
                    f'{v:.4f}', va='center', fontweight='bold')
        
        # Amélioration de l'apparence
        plt.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        plt.show()
        
        # Statistiques supplémentaires
        total_importance = self.feature_importance['importance'].sum()
        cumulative_top = top_features['importance'].sum()
        percentage_covered = (cumulative_top / total_importance) * 100
        
        print(f"\n📈 STATISTIQUES:")
        print(f"   • Total features: {len(self.feature_importance)}")
        print(f"   • Top {top_n} couvrent {percentage_covered:.1f}% de l'importance totale")
        print(f"   • Feature la plus importante: {top_features.iloc[0]['feature']} ({top_features.iloc[0]['importance']:.4f})")
        
        return top_features

    def quick_overfitting_check(self) -> str:
        """
        Vérification rapide du statut d'overfitting du modèle entraîné
        
        Returns:
            Statut d'overfitting sous forme de chaîne
        """
        if not hasattr(self, 'training_metrics') or 'overfitting_analysis' not in self.training_metrics:
            return "❌ Analyse d'overfitting non disponible. Entraînez d'abord le modèle."
        
        analysis = self.training_metrics['overfitting_analysis']
        status = analysis.get('overfitting_status', 'Inconnu')
        avg_gap = analysis.get('average_gap_percent', 0)
        
        status_icons = {
            'Excellent': '✅',
            'Bon': '🟡', 
            'Moyen': '🟠',
            'Problématique': '🔴'
        }
        
        icon = status_icons.get(status, '❓')
        
        return f"{icon} Overfitting: {status} (Écart moyen: {avg_gap:.1f}%)"
    
    def display_overfitting_summary(self):
        """
        Affiche un résumé compact de l'analyse d'overfitting
        """
        if not hasattr(self, 'training_metrics') or 'overfitting_analysis' not in self.training_metrics:
            print("❌ Analyse d'overfitting non disponible. Entraînez d'abord le modèle.")
            return
        
        analysis = self.training_metrics['overfitting_analysis']
        
        print(f"\n🔍 RÉSUMÉ OVERFITTING")
        print("=" * 40)
        print(f"Statut: {self.quick_overfitting_check()}")
        print(f"Écart ROC-AUC: {analysis.get('roc_auc_gap_percent', 0):+.1f}%")
        print(f"Écart F1-Score: {analysis.get('f1_score_gap_percent', 0):+.1f}%")
        print(f"Stabilité CV (ROC): {analysis.get('cv_roc_auc_stability', 0):.1f}%")
        
        # Conseil rapide
        avg_gap = analysis.get('average_gap_percent', 0)
        if avg_gap < 5:
            print("💡 Conseil: Modèle bien équilibré, vous pouvez l'utiliser en production")
        elif avg_gap < 15:
            print("💡 Conseil: Surveillez les performances sur de nouvelles données")
        else:
            print("💡 Conseil: Réduisez la complexité ou augmentez les données")

    def display_feature_importance(self, top_n: int = 15):
        """
        Alias pour plot_feature_importance (compatibilité)
        """
        return self.plot_feature_importance(top_n)

    def predict_from_csv(self, 
                        csv_path: str, 
                        airports_ref_path: str = "airports_ref.csv",
                        output_path: Optional[str] = None,
                        include_probability: bool = True) -> pd.DataFrame:
        """
        Prédit les retards avec classification de risque à partir d'un fichier CSV
        
        Args:
            csv_path: Chemin vers le fichier CSV à prédire
            airports_ref_path: Chemin vers le fichier de référence des aéroports
            output_path: Chemin de sortie pour sauvegarder les résultats (optionnel)
            include_probability: Inclure la probabilité numérique dans le résultat
            
        Returns:
            DataFrame avec les prédictions et classifications de risque
        """
        if self.model is None or self.preprocessor is None:
            raise ValueError("Le modèle doit être chargé avant de faire des prédictions")
        
        print(f"🔄 Chargement des données depuis {csv_path}...")
        
        # Charger les données brutes pour sauvegarder les IDs
        df_raw = pd.read_csv(csv_path)
        
        # Sauvegarder f_id si présent
        f_id_column = None
        if 'f_id' in df_raw.columns:
            f_id_values = df_raw['f_id'].copy()
            f_id_column = 'f_id'
        elif 'id' in df_raw.columns:
            f_id_values = df_raw['id'].copy()
            f_id_column = 'id'
        else:
            # Créer un ID temporaire basé sur l'index
            f_id_values = pd.Series(range(len(df_raw)), name='row_id')
            f_id_column = 'row_id'
            
        print(f"✅ {len(df_raw):,} lignes chargées, colonne d'identifiant: {f_id_column}")
        
        # Préparation des données avec load_and_prepare_data (mode production, DRY!)
        print("🔄 Préparation des caractéristiques (mode production)...")
        df = self.load_and_prepare_data(csv_path, airports_ref_path, for_training=False)
        
        # Sélection des colonnes pour la prédiction
        feature_cols = self.numeric_features + self.categorical_features + self.ordered_features
        existing_cols = [col for col in feature_cols if col in df.columns]
        
        if len(existing_cols) != len(feature_cols):
            missing_cols = set(feature_cols) - set(existing_cols)
            print(f"⚠️ Colonnes manquantes: {missing_cols}")
            print("   Les colonnes manquantes seront imputées automatiquement.")
        
        X = df[existing_cols]
        
        # Prédictions
        print("🔄 Génération des prédictions...")
        probabilities, predictions = self.predict(X)
        
        # Classification des risques
        risk_levels = self._classify_risk_levels(probabilities)
        
        # Construction du DataFrame de résultats
        results = pd.DataFrame({
            f_id_column: f_id_values[:len(probabilities)],
            'prediction': predictions,
            'risk_level': risk_levels
        })
        
        if include_probability:
            results['delay_probability'] = probabilities
            
        # Ajout de statistiques descriptives
        self._print_prediction_summary(results, probabilities)
        
        # Sauvegarde si demandée
        if output_path:
            results.to_csv(output_path, index=False)
            print(f"✅ Résultats sauvegardés dans {output_path}")
            
        return results
    
    def _classify_risk_levels(self, probabilities: np.ndarray) -> List[str]:
        """
        Classifie les probabilités en niveaux de risque en utilisant les seuils
        calculés automatiquement lors de l'entraînement.
        
        Args:
            probabilities: Probabilités de retard (0-1)
            
        Returns:
            Liste des niveaux de risque
        
        Logique de classification adaptative:
        
        Les seuils sont calculés automatiquement dans _calculate_risk_thresholds():
        
        - Faible: prob < risk_threshold_low
          → En dessous de la médiane des "pas de retard"
          → Zone de confiance élevée (pas de retard attendu)
        
        - Modéré: risk_threshold_low <= prob < risk_threshold_high (optimal_threshold)
          → Zone d'incertitude entre les deux distributions
          → Le modèle hésite, surveillance recommandée
        
        - Élevé: prob >= risk_threshold_high (optimal_threshold)
          → Au-delà du seuil de décision optimal
          → Retard prédit avec forte confiance
        
        Cette approche s'adapte automatiquement à chaque modèle entraîné
        sans valeurs en dur dans le code.
        """
        risk_levels = []
        
        # Utiliser les seuils calculés automatiquement lors de l'entraînement
        # Fallback sur des valeurs par défaut si pas encore calculés (chargement de modèle)
        low_threshold = getattr(self, 'risk_threshold_low', self.optimal_threshold * 0.67)
        high_threshold = getattr(self, 'risk_threshold_high', self.optimal_threshold)
        
        for prob in probabilities:
            if prob < low_threshold:
                risk_levels.append("low")
            elif prob < high_threshold:
                risk_levels.append("medium")
            else:
                risk_levels.append("high")

        return risk_levels
    
    def _print_prediction_summary(self, results: pd.DataFrame, probabilities: np.ndarray):
        """Affiche un résumé des prédictions"""
        
        total = len(results)
        nb_retards = (results['prediction'] == 1).sum()
        nb_pas_retards = (results['prediction'] == 0).sum()
        
        # Distribution par niveau de risque
        risk_counts = results['risk_level'].value_counts()
        
        print(f"\n📊 RÉSUMÉ DES PRÉDICTIONS ({total:,} vols analysés):")
        print("=" * 60)
        print(f"🔴 Retards prédits: {nb_retards:,} ({nb_retards/total*100:.1f}%)")
        print(f"🟢 Pas de retard: {nb_pas_retards:,} ({nb_pas_retards/total*100:.1f}%)")
        print()
        print("📈 DISTRIBUTION DES RISQUES:")
        for risk_level in ["Faible", "Modéré", "Élevé"]:
            count = risk_counts.get(risk_level, 0)
            print(f"  {risk_level:>8}: {count:>6,} vols ({count/total*100:>5.1f}%)")
        
        print(f"\n🎯 STATISTIQUES DES PROBABILITÉS:")
        print(f"  Probabilité moyenne: {np.mean(probabilities):.3f}")
        print(f"  Probabilité médiane: {np.median(probabilities):.3f}")
        print(f"  Probabilité min/max: {np.min(probabilities):.3f} / {np.max(probabilities):.3f}")
        print(f"  Seuil de décision: {self.optimal_threshold:.3f}")

    def predict_single_flight(self, flight_data: Dict) -> Dict[str, Union[str, float, int]]:
        """
        Prédit le retard pour un seul vol
        
        Args:
            flight_data: Dictionnaire avec les données du vol
            
        Returns:
            Dictionnaire avec la prédiction et le niveau de risque
        """
        if self.model is None or self.preprocessor is None:
            raise ValueError("Le modèle doit être chargé avant de faire des prédictions")
        
        # Convertir en DataFrame
        df = pd.DataFrame([flight_data])
        
        # Appliquer le même pipeline de préparation
        # Note: Cette version simplifiée assume que les données sont déjà formatées
        feature_cols = self.numeric_features + self.categorical_features + self.ordered_features
        existing_cols = [col for col in feature_cols if col in df.columns]
        
        X = df[existing_cols]
        
        # Faire la prédiction
        probability, prediction = self.predict(X)
        
        # Classer le niveau de risque
        risk_level = self._classify_risk_levels(probability)[0]
        
        return {
            'prediction': int(prediction[0]),
            'delay_probability': float(probability[0]),
            'risk_level': risk_level,
            'delay_expected': prediction[0] == 1
        }


# Exemple d'utilisation
if __name__ == "__main__":
    # Exemple d'utilisation de la classe
    predictor = FlightDelayPredictor(
        delay_threshold=15,
        sample_size=200000,  # Pour test rapide
        random_state=42
    )
    
    # Chargement et préparation des données
    df = predictor.load_and_prepare_data("C:/Temp/data-all 2025-11-04.csv", "utils/airports_ref.csv")
    
    # Entraînement
    metrics = predictor.train(df, model_type='xgboost_tuned')
    
    # Sauvegarde
    paths = predictor.save_model()
    
    print("✅ Classe FlightDelayPredictor prête à l'utilisation!")