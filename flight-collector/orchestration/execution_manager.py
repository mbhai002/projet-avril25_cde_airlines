#!/usr/bin/env python3
"""
Gestionnaire des modes d'exécution basé sur la configuration
"""

import sys
import os
from datetime import datetime, timedelta
import time

# Ajouter le répertoire du projet au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.collection_config import CollectionConfig
from config.simple_logger import get_logger
from orchestration.flight_orchestrator import FlightOrchestrator


class ExecutionManager:
    """
    Gestionnaire des modes d'exécution basé sur la configuration
    Responsabilité : Exécuter selon la configuration (une fois ou en boucle)
    """
    
    # Constante pour la pause entre les étapes
    STEP_PAUSE_SECONDS = 2
    
    def __init__(self, config: CollectionConfig):
        """
        Initialise le gestionnaire d'exécution
        
        Args:
            config: Configuration contenant tous les paramètres
        """
        self.config = config
        self.logger = get_logger(__name__)
        
        self.logger.info("ExecutionManager initialized")
    
    def run(self):
        """Point d'entrée principal pour l'exécution"""
        print("=== COLLECTE - Workflow complet ===")
        self._execute_complete_workflow()
    
    def _execute_complete_workflow(self):
        """Exécute une collecte combinée - LES 8 ÉTAPES AVEC SESSION_ID GLOBAL"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Début de collecte COMPLÈTE (jusqu'à 8 étapes selon config)...")
        start_time = datetime.now()
        
        # Générer un session_id global unique pour toutes les étapes
        global_session_id = f"{start_time.strftime('%Y%m%d_%H%M%S')}_{start_time.microsecond // 1000:03d}"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Session ID global: {global_session_id}")
        
        orchestrator = FlightOrchestrator(self.config)
        
        # Initialisation des résultats pour toutes les étapes
        results_realtime = results_weather = results_past = None
        results_association_metar = results_association_taf = results_postgres = results_ml = results_update = None
        
        # ÉTAPE 1: Collecte vols temps réel
        print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 1: Collecte vols temps réel...")
        try:
            results_realtime = orchestrator.collect_and_store_realtime_flights(global_session_id)
            print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✓ Étape 1 {'réussie' if results_realtime.success else 'échouée'}")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✗ Erreur étape 1: {e}")
        
        time.sleep(self.STEP_PAUSE_SECONDS)
        # ÉTAPE 2: Collecte données météo
        print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 2: Collecte données météorologiques...")
        try:
            results_weather = orchestrator.collect_and_store_weather_data()
            print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✓ Étape 2 {'réussie' if results_weather.success else 'échouée'}")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✗ Erreur étape 2: {e}")
        
        time.sleep(self.STEP_PAUSE_SECONDS)
        
        # ÉTAPE 3: Collecte vols passés
        print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 3: Collecte vols passés...")
        try:
            # Passer le global_session_id pour lier les vols passés aux vols temps réel
            results_past = orchestrator.collect_and_store_past_flights(global_session_id)
            print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✓ Étape 3 {'réussie' if results_past.success else 'échouée'}")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✗ Erreur étape 3: {e}")
        
        time.sleep(self.STEP_PAUSE_SECONDS)
        
        # ÉTAPE 4: Association vols-METAR
        if results_realtime and results_realtime.success and global_session_id:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 4: Association vols-METAR...")
            try:
                results_association_metar = orchestrator.associate_flights_with_metar(global_session_id)
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✓ Étape 4 {'réussie' if results_association_metar.success else 'échouée'}")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✗ Erreur étape 4: {e}")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 4: Ignorée (pas de vols temps réel collectés)")
        
        time.sleep(self.STEP_PAUSE_SECONDS)
        
        # ÉTAPE 5: Association vols-TAF
        if results_realtime and results_realtime.success and global_session_id:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 5: Association vols-TAF...")
            try:
                results_association_taf = orchestrator.associate_flights_with_taf(global_session_id)
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✓ Étape 5 {'réussie' if results_association_taf.success else 'échouée'}")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✗ Erreur étape 5: {e}")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 5: Ignorée (pas de vols temps réel collectés)")
            
        time.sleep(self.STEP_PAUSE_SECONDS)

        # ÉTAPE 6: Insertion des données météo et des vols dans PostgreSQL
        if global_session_id and ((results_association_metar and results_association_metar.success) or (results_association_taf and results_association_taf.success)):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 6: Insertion données météo et vols dans PostgreSQL...")
            try:
                results_postgres = orchestrator.insert_weather_and_flight_data_to_postgres(global_session_id)
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✓ Étape 6 {'réussie' if results_postgres.success else 'échouée'}")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✗ Erreur étape 6: {e}")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 6: Ignorée (pas de session de vols ou d'association réussie)")

        time.sleep(self.STEP_PAUSE_SECONDS)

        # ÉTAPE 7: Prédiction ML sur les vols nouvellement insérés
        if results_postgres and results_postgres.success and results_postgres.details and 'inserted_flight_ids' in results_postgres.details:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 7: Prédiction ML sur vols insérés...")
            try:
                inserted_ids = results_postgres.details['inserted_flight_ids']
                results_ml = orchestrator.predict_flights_ml(inserted_ids)
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✓ Étape 7 {'réussie' if results_ml.success else 'échouée'}")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✗ Erreur étape 7: {e}")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 7: Ignorée (pas de vols insérés)")

        time.sleep(self.STEP_PAUSE_SECONDS)

        # ÉTAPE 8: Mise à jour des vols dans PostgreSQL avec les données passées
        if global_session_id and results_past and results_past.success:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 8: Mise à jour vols PostgreSQL avec données passées...")
            try:
                results_update = orchestrator.update_flights_data_to_postgres(global_session_id)
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✓ Étape 8 {'réussie' if results_update.success else 'échouée'}")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✗ Erreur étape 8: {e}")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 8: Ignorée (pas de session de vols ou pas de vols passés collectés)")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Résumé global
        etapes_reussies = []
        if results_realtime and results_realtime.success: etapes_reussies.append("temps réel")
        if results_weather and results_weather.success: etapes_reussies.append("météo")
        if results_past and results_past.success: etapes_reussies.append("vols passés")
        if results_association_metar and results_association_metar.success: etapes_reussies.append("association-METAR")
        if results_association_taf and results_association_taf.success: etapes_reussies.append("association-TAF")
        if results_postgres and results_postgres.success: etapes_reussies.append("insertion-PostgreSQL")
        if results_ml and results_ml.success: etapes_reussies.append("prédiction-ML")
        if results_update and results_update.success: etapes_reussies.append("mise à jour vols passés-PostgreSQL")

        total_etapes = 8  # Toutes les étapes sont désormais obligatoires/tentées
        
        if len(etapes_reussies) == total_etapes:
            status = f"✓ succès complet ({len(etapes_reussies)}/{total_etapes} étapes)"
        elif len(etapes_reussies) > 0:
            status = f"⚠ succès partiel ({len(etapes_reussies)}/{total_etapes} étapes: {', '.join(etapes_reussies)})"
        else:
            status = f"✗ échec complet (0/{total_etapes} étapes)"
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Collecte complète terminée avec {status} ({duration:.1f}s)")
        print("=" * 80 + "\n")
