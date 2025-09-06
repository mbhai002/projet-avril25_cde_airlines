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
        """Point d'entrée principal pour l'exécution selon la configuration"""
        if self.config.run_once:
            self._run_single()
        else:
            self._run_loop()
    
    def _run_single(self):
        """Exécute une collecte unique complète (7 étapes)"""
        print("=== COLLECTE UNIQUE - Workflow complet (7 étapes) ===")
        self._execute_complete_workflow()
    
    def _run_loop(self):
        """Exécute en boucle le workflow complet (7 étapes)"""
        print("=== MODE BOUCLE - Collecte complète (7 étapes) ===")
        print(f"Exécution toutes les {self.config.loop_interval_minutes} minutes à XX:{self.config.schedule_minute:02d}")
        print("Collecte les vols temps réel ET les vols passés à chaque exécution")
        print("Appuyez sur Ctrl+C pour arrêter\n")
        
        try:
            while True:
                # Calculer la prochaine exécution
                next_run = self._calculate_next_run(self.config.schedule_minute, self.config.loop_interval_minutes)
                wait_seconds = (next_run - datetime.now()).total_seconds()
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Prochaine exécution prévue à {next_run.strftime('%H:%M:%S')}")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Attente de {wait_seconds/60:.1f} minutes...")
                time.sleep(wait_seconds)
                
                # Exécuter le workflow complet
                self._execute_complete_workflow()
                
        except KeyboardInterrupt:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Arrêt demandé par l'utilisateur")
            print("Collecteur arrêté.")
    
    def _execute_complete_workflow(self):
        """Exécute une collecte combinée - LES 7 ÉTAPES AVEC SESSION_ID GLOBAL"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Début de collecte COMPLÈTE (7 étapes)...")
        start_time = datetime.now()
        
        # Générer un session_id global unique pour toutes les étapes
        global_session_id = f"{start_time.strftime('%Y%m%d_%H%M%S')}_{start_time.microsecond // 1000:03d}"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Session ID global: {global_session_id}")
        
        orchestrator = FlightOrchestrator(self.config)
        
        results_realtime = results_weather = results_past =  None
        results_association_metar = results_association_taf = results_postgres = results_update = None
        
        # ÉTAPE 1: Collecte vols temps réel
        if self.config.collect_realtime:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 1: Collecte vols temps réel...")
            try:
                results_realtime = orchestrator.collect_and_store_realtime_flights(global_session_id)
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✓ Étape 1 {'réussie' if results_realtime.success else 'échouée'}")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✗ Erreur étape 1: {e}")
            
            time.sleep(2)  # Pause entre les étapes
        
        # ÉTAPE 2: Collecte données météo
        if self.config.enable_weather:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 2: Collecte données météorologiques...")
            try:
                results_weather = orchestrator.collect_and_store_weather_data()
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✓ Étape 2 {'réussie' if results_weather.success else 'échouée'}")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✗ Erreur étape 2: {e}")
            
            time.sleep(2)  # Pause entre les étapes
        
        # ÉTAPE 3: Collecte vols passés
        if self.config.collect_past:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 3: Collecte vols passés...")
            try:
                # Passer le global_session_id pour lier les vols passés aux vols temps réel
                results_past = orchestrator.collect_and_store_past_flights(global_session_id)
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✓ Étape 3 {'réussie' if results_past.success else 'échouée'}")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✗ Erreur étape 3: {e}")
        
        time.sleep(2)  # Pause entre les étapes
        
        # ÉTAPE 4: Association vols-METAR
        if self.config.enable_weather and results_realtime and results_realtime.success and global_session_id:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 4: Association vols-METAR...")
            try:
                results_association_metar = orchestrator.associate_flights_with_metar(global_session_id)
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✓ Étape 4 {'réussie' if results_association_metar.success else 'échouée'}")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✗ Erreur étape 4: {e}")
        elif self.config.enable_weather and not global_session_id:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 4: Ignorée (pas de vols temps réel collectés)")
        
        time.sleep(2)  # Pause entre les étapes
        
        # ÉTAPE 5: Association vols-TAF
        if self.config.enable_weather and results_realtime and results_realtime.success and global_session_id:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 5: Association vols-TAF...")
            try:
                results_association_taf = orchestrator.associate_flights_with_taf(global_session_id)
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✓ Étape 5 {'réussie' if results_association_taf.success else 'échouée'}")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✗ Erreur étape 5: {e}")
        elif self.config.enable_weather and not global_session_id:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 5: Ignorée (pas de vols temps réel collectés)")
            
        time.sleep(2)

        # ÉTAPE 6: Insertion des données météo et des vols dans PostgreSQL
        if self.config.enable_postgresql_insertion and global_session_id and ((results_association_metar and results_association_metar.success) or (results_association_taf and results_association_taf.success)):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 6: Insertion données météo et vols dans PostgreSQL...")
            try:
                results_postgres = orchestrator.insert_weather_and_flight_data_to_postgres(global_session_id)
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✓ Étape 6 {'réussie' if results_postgres.success else 'échouée'}")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✗ Erreur étape 6: {e}")
        elif self.config.enable_postgresql_insertion:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 6: Ignorée (pas de session de vols ou d'association réussie)")

        time.sleep(2)

        # ÉTAPE 7: Mise à jour des vols dans PostgreSQL avec les données passées
        if self.config.enable_postgresql_insertion and global_session_id and results_past and results_past.success:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 7: Mise à jour vols PostgreSQL avec données passées...")
            try:
                results_update = orchestrator.update_flights_data_to_postgres(global_session_id)
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✓ Étape 7 {'réussie' if results_update.success else 'échouée'}")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}]   ✗ Erreur étape 7: {e}")
        elif self.config.enable_postgresql_insertion:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → ÉTAPE 7: Ignorée (pas de session de vols ou pas de vols passés collectés)")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Résumé global des 7 étapes
        etapes_reussies = []
        if results_realtime and results_realtime.success: etapes_reussies.append("temps réel")
        if results_weather and results_weather.success: etapes_reussies.append("météo")
        if results_past and results_past.success: etapes_reussies.append("vols passés")
        if results_association_metar and results_association_metar.success and self.config.enable_weather: etapes_reussies.append("association-METAR")
        if results_association_taf and results_association_taf.success and self.config.enable_weather: etapes_reussies.append("association-TAF")
        if results_postgres and results_postgres.success and self.config.enable_postgresql_insertion: etapes_reussies.append("insertion-PostgreSQL")
        if results_update and results_update.success and self.config.enable_postgresql_insertion: etapes_reussies.append("mise à jour des vols passés-PostgreSQL")

        total_etapes = 3  # Étapes de base (temps réel, météo, vols passés)
        if self.config.enable_weather:
            total_etapes += 2  # +2 pour associations METAR et TAF
        if self.config.enable_postgresql_insertion:
            total_etapes += 2  # +2 pour insertion et mise à jour PostgreSQL
        
        if len(etapes_reussies) == total_etapes:
            status = f"✓ succès complet ({len(etapes_reussies)}/{total_etapes} étapes)"
        elif len(etapes_reussies) > 0:
            status = f"⚠ succès partiel ({len(etapes_reussies)}/{total_etapes} étapes: {', '.join(etapes_reussies)})"
        else:
            status = f"✗ échec complet (0/{total_etapes} étapes)"
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Collecte complète terminée avec {status} ({duration:.1f}s)")
        print("=" * 80 + "\n")
    
    def _calculate_next_run(self, target_minute: int, interval_minutes: int) -> datetime:
        """
        Calcule la prochaine heure d'exécution
        
        Args:
            target_minute: Minute cible (ex: 5 pour XX:05)
            interval_minutes: Intervalle en minutes
            
        Returns:
            Prochaine heure d'exécution
        """
        now = datetime.now()
        next_run = now.replace(minute=target_minute, second=0, microsecond=0)
        
        if next_run <= now:
            next_run += timedelta(minutes=interval_minutes)
        
        return next_run
