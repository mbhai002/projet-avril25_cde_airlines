#!/usr/bin/env python3
"""
Script principal pour récupérer les vols et les intégrer dans MongoDB
"""

import sys
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time

# Ajouter le répertoire du projet au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.flight_data_scrapper import FlightDataScraper
from data.metar_xml_collector import MetarXmlCollector
from data.taf_xml_collector import TafXmlCollector
from utils.mongodb_manager import MongoDBManager
from config.simple_logger import get_logger, log_operation_time, log_database_operation


class CollectionType(Enum):
    """Types de collecte disponibles"""
    REALTIME = "realtime_departures"
    PAST = "past_departures"


@dataclass
class CollectionConfig:
    """Configuration pour une collecte"""
    mongodb_uri: str = "mongodb://localhost:27017/"
    database_name: str = "dst_airlines2"
    collection_name: str = "flights_realtime"
    num_airports: int = 200
    delay: float = 1.5
    batch_size: int = 500
    enable_xml_weather: bool = True
    hour_offset: int = 1  # 1 pour futur, négatif pour passé


@dataclass
class CollectionResults:
    """Résultats d'une collecte"""
    success: bool = False
    collection_session_id: str = ""
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0
    flights_collected: int = 0
    flights_inserted: int = 0
    metar_xml_collected: int = 0
    metar_xml_inserted: int = 0
    taf_xml_collected: int = 0
    taf_xml_inserted: int = 0
    mongodb_connected: bool = False
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class FlightCollectorMain:
    """
    Classe principale pour orchestrer la collecte de vols et l'intégration MongoDB
    """
    
    def __init__(self, config: CollectionConfig):
        """
        Initialise le collecteur principal
        
        Args:
            config: Configuration de la collecte
        """
        self.config = config
        self.logger = get_logger(__name__)
        
        # Initialiser les composants
        self.scraper = FlightDataScraper(lang="en")
        self.mongo_manager = MongoDBManager(config.mongodb_uri, config.database_name)
        
        # Initialiser les collecteurs XML si activés
        if config.enable_xml_weather:
            self.metar_xml_collector = MetarXmlCollector()
            self.taf_xml_collector = TafXmlCollector()
        else:
            self.metar_xml_collector = None
            self.taf_xml_collector = None
        
        self.logger.info(f"FlightCollectorMain initialized - Database: {config.database_name}, "
                        f"Collection: {config.collection_name}, Weather: {config.enable_xml_weather}")
    
    def collect_and_store_flights(self, collection_type: CollectionType = CollectionType.REALTIME) -> CollectionResults:
        """
        Collecte et stocke les vols selon le type spécifié
        
        Args:
            collection_type: Type de collecte (temps réel ou passé)
            
        Returns:
            Résultats de l'opération
        """
        operation_start_time = datetime.now()
        
        # Déterminer les paramètres selon le type de collecte
        is_past_collection = collection_type == CollectionType.PAST
        hour_offset = self.config.hour_offset if not is_past_collection else -abs(self.config.hour_offset)
        session_prefix = "past_session" if is_past_collection else "session"
        
        # Générer un ID unique pour cette session de collecte
        session_id = f"{session_prefix}_{operation_start_time.strftime('%Y%m%d_%H%M%S')}_{operation_start_time.microsecond // 1000:03d}"
        
        # Initialiser les résultats
        results = CollectionResults(
            collection_session_id=session_id,
            start_time=operation_start_time.isoformat()
        )
        
        self._log_collection_start(collection_type, session_id, hour_offset)
        
        try:
            # Étape 1: Connexion MongoDB
            if not self._connect_to_mongodb(results):
                return results
            
            # Étape 2: Collecte des données météo (seulement pour temps réel)
            if self.config.enable_xml_weather and not is_past_collection:
                self._collect_weather_data(results, session_id)
            
            # Étape 3: Collecte des vols
            flights = self._collect_flights(results, hour_offset)
            if not flights:
                results.success = True  # Succès même sans vols si météo collectée
                return results
            
            # Étape 4: Insertion en base
            self._insert_flights(results, flights, session_id, collection_type, is_past_collection)
            
        except Exception as e:
            error_msg = f"Unexpected error during collection: {e}"
            self.logger.error(error_msg, exc_info=True)
            results.errors.append(error_msg)
            
        finally:
            self._finalize_collection(results, operation_start_time, collection_type)
            
            return results
    
    def _log_collection_start(self, collection_type: CollectionType, session_id: str, hour_offset: int):
        """Log le début de la collecte"""
        type_desc = "TEMPS RÉEL" if collection_type == CollectionType.REALTIME else "PASSÉS"
        self.logger.info(f"=== DÉBUT DE LA COLLECTE {type_desc} ===")
        self.logger.info(f"Session ID: {session_id}")
        self.logger.info(f"Paramètres: {self.config.num_airports} aéroports, offset {hour_offset}h")
    
    def _connect_to_mongodb(self, results: CollectionResults) -> bool:
        """Établit la connexion MongoDB"""
        self.logger.info("Connecting to MongoDB...")
        if not self.mongo_manager.connect():
            error_msg = "Failed to connect to MongoDB"
            self.logger.error(error_msg)
            results.errors.append(error_msg)
            return False
        
        results.mongodb_connected = True
        self.logger.info("✓ MongoDB connection successful")
        return True
    
    def _collect_weather_data(self, results: CollectionResults, session_id: str):
        """Collecte les données météo METAR/TAF"""
        self.logger.info("Starting XML weather data collection (METAR/TAF)...")
        
        # Collecte METAR
        if self.metar_xml_collector:
            try:
                start_time = time.time()
                metar_docs = self.metar_xml_collector.fetch_metar_data()
                duration_ms = (time.time() - start_time) * 1000
                
                if metar_docs:
                    for doc in metar_docs:
                        if '_metadata' not in doc:
                            doc['_metadata'] = {}
                        doc['_metadata']['collection_session_id'] = session_id
                    
                    inserted = self._insert_weather_xml_to_mongodb(metar_docs, "metar_xml")
                    results.metar_xml_collected = len(metar_docs)
                    results.metar_xml_inserted = inserted
                    
                    log_database_operation(self.logger, "insert", "weather_metar_xml", inserted, duration_ms)
                    self.logger.info(f"✓ {inserted} METAR XML documents inserted")
                else:
                    self.logger.warning("No METAR XML data collected")
                    
            except Exception as e:
                error_msg = f"Error during METAR XML collection: {e}"
                self.logger.error(error_msg, exc_info=True)
                results.errors.append(error_msg)
        
        # Collecte TAF
        if self.taf_xml_collector:
            try:
                start_time = time.time()
                taf_docs = self.taf_xml_collector.fetch_taf_data()
                duration_ms = (time.time() - start_time) * 1000
                
                if taf_docs:
                    for doc in taf_docs:
                        if '_metadata' not in doc:
                            doc['_metadata'] = {}
                        doc['_metadata']['collection_session_id'] = session_id
                    
                    inserted = self._insert_weather_xml_to_mongodb(taf_docs, "taf_xml")
                    results.taf_xml_collected = len(taf_docs)
                    results.taf_xml_inserted = inserted
                    
                    log_database_operation(self.logger, "insert", "weather_taf_xml", inserted, duration_ms)
                    self.logger.info(f"✓ {inserted} TAF XML documents inserted")
                else:
                    self.logger.warning("No TAF XML data collected")
                    
            except Exception as e:
                error_msg = f"Error during TAF XML collection: {e}"
                self.logger.error(error_msg, exc_info=True)
                results.errors.append(error_msg)
    
    def _collect_flights(self, results: CollectionResults, hour_offset: int) -> List[Dict]:
        """Collecte les vols"""
        start_time = time.time()
        offset_desc = "past" if hour_offset < 0 else "next hour"
        self.logger.info(f"Starting {offset_desc} flight collection for top {self.config.num_airports} airports...")
        
        flights = self.scraper.fetch_next_hour_departures_top_airports(
            num_airports=self.config.num_airports,
            delay=self.config.delay,
            hour_offset=hour_offset,
            auto_save=False
        )
        
        duration_ms = (time.time() - start_time) * 1000
        results.flights_collected = len(flights)
        
        log_operation_time(self.logger, f"{offset_desc}_flight_collection", start_time)
        self.logger.info(f"✓ {len(flights)} flights collected ({duration_ms:.1f}ms)")
        
        return flights
    
    def _insert_flights(self, results: CollectionResults, flights: List[Dict], 
                       session_id: str, collection_type: CollectionType, is_past: bool):
        """Insère les vols en base"""
        self.logger.info(f"Preparing flight data for MongoDB insertion...")
        prepared_flights = self._prepare_flights_for_mongodb(flights, session_id, collection_type)
        
        start_time = time.time()
        self.logger.info(f"Inserting {len(prepared_flights)} flights into MongoDB...")
        
        # Utiliser upsert pour les vols passés, insert normal pour temps réel
        if is_past:
            success = self._upsert_flights_to_mongodb(prepared_flights)
            operation = "upsert"
        else:
            success = self._insert_flights_to_mongodb(prepared_flights)
            operation = "insert"
        
        duration_ms = (time.time() - start_time) * 1000
        
        if success:
            results.flights_inserted = len(prepared_flights)
            log_database_operation(self.logger, operation, self.config.collection_name, 
                                 len(prepared_flights), duration_ms)
            self.logger.info(f"✓ {len(prepared_flights)} flights {operation}ed successfully")
            results.success = True
        else:
            error_msg = f"Error during flight {operation} into MongoDB"
            self.logger.error(error_msg)
            results.errors.append(error_msg)
            # Succès partiel si météo collectée
            if results.metar_xml_collected > 0 or results.taf_xml_collected > 0:
                results.success = True
                self.logger.info("Partial success: weather data collected despite flight insertion error")
    
    def _finalize_collection(self, results: CollectionResults, start_time: datetime, 
                           collection_type: CollectionType):
        """Finalise la collecte"""
        self.mongo_manager.disconnect()
        
        end_time = datetime.now()
        results.end_time = end_time.isoformat()
        results.duration_seconds = (end_time - start_time).total_seconds()
        
        # Log final
        type_desc = "TEMPS RÉEL" if collection_type == CollectionType.REALTIME else "PASSÉS"
        self.logger.info(f"=== COLLECTION {type_desc} COMPLETED ===")
        self.logger.info(f"Session: {results.collection_session_id}, Success: {results.success}, "
                        f"Duration: {results.duration_seconds:.1f}s")
        
        if collection_type == CollectionType.REALTIME:
            self.logger.info(f"Flights: {results.flights_collected}/{results.flights_inserted}, "
                           f"METAR: {results.metar_xml_collected}/{results.metar_xml_inserted}, "
                           f"TAF: {results.taf_xml_collected}/{results.taf_xml_inserted}")
        else:
            self.logger.info(f"Past Flights: {results.flights_collected}/{results.flights_inserted}")
        
        if results.errors:
            self.logger.warning(f"Collection completed with {len(results.errors)} errors")
            for error in results.errors[:3]:
                self.logger.warning(f"Error: {error}")
    
    def _prepare_flights_for_mongodb(self, flights: List[Dict], session_id: str, 
                                   collection_type: CollectionType) -> List[Dict]:
        """
        Prépare les données de vol pour l'insertion MongoDB
        
        Args:
            flights: Liste des vols bruts
            session_id: ID de session pour associer les données
            collection_type: Type de collecte
            
        Returns:
            Liste des vols préparés pour MongoDB
        """
        current_time = datetime.now(timezone.utc)
        prepared_flights = []
        
        for flight in flights:
            # Ajouter des métadonnées d'import
            flight_doc = flight.copy()
            flight_doc['_metadata'] = {
                'collection_type': collection_type.value,
                'collected_at': current_time.isoformat(),
                'source': 'airportinfo.live',
                'script_version': '1.0',
                'collection_session_id': session_id,
                'is_updated': False,  # Sera mis à True lors d'un upsert qui modifie un document existant
                'update_count': 0     # Nombre de fois que ce vol a été mis à jour
            }
            
            # Ajouter un ID unique basé sur le vol et l'heure de collecte
            flight_doc['_id'] = self._generate_flight_id(flight, current_time)
            
            prepared_flights.append(flight_doc)
            
        return prepared_flights
    
    def _generate_flight_id(self, flight: Dict, collection_time: datetime) -> str:
        """
        Génère un ID unique pour le vol
        
        Args:
            flight: Données du vol
            collection_time: Heure de collecte
            
        Returns:
            ID unique pour le vol
        """
        # Utiliser des champs clés pour créer un ID unique
        base_elements = [
            flight.get('flight_number', 'UNKNOWN'),
            flight.get('from_code', 'XXX'),
            flight.get('to_code', 'XXX'),
            flight.get('departure', {}).get('scheduled_utc', ''),
            collection_time.strftime('%Y%m%d_%H%M')
        ]
        
        return '_'.join(str(elem) for elem in base_elements if elem)
    
    def _insert_flights_to_mongodb(self, flights: List[Dict]) -> bool:
        """Insère les vols dans MongoDB par lots (insert normal)"""
        return self._insert_or_upsert_flights(flights, upsert=False)
    
    def _upsert_flights_to_mongodb(self, flights: List[Dict]) -> bool:
        """Insère/met à jour les vols dans MongoDB par lots (upsert)"""
        return self._insert_or_upsert_flights(flights, upsert=True)
    
    def _insert_or_upsert_flights(self, flights: List[Dict], upsert: bool = False) -> bool:
        """
        Insère ou met à jour les vols dans MongoDB par lots
        
        Args:
            flights: Liste des vols à insérer
            upsert: Si True, utilise upsert, sinon insert normal
            
        Returns:
            True si l'insertion réussit, False sinon
        """
        try:
            collection = self.mongo_manager.database[self.config.collection_name]
            total_processed = 0
            
            # Traitement par lots
            for i in range(0, len(flights), self.config.batch_size):
                batch = flights[i:i + self.config.batch_size]
                
                try:
                    if upsert:
                        # Upsert individuel pour chaque document avec gestion des métadonnées de mise à jour
                        batch_processed = 0
                        for flight in batch:
                            # Vérifier si le document existe déjà
                            existing_doc = collection.find_one({"_id": flight["_id"]})
                            
                            if existing_doc:
                                # Document existant - mettre à jour les métadonnées
                                flight["_metadata"]["is_updated"] = True
                                flight["_metadata"]["update_count"] = existing_doc.get("_metadata", {}).get("update_count", 0) + 1
                                flight["_metadata"]["last_updated_at"] = datetime.now(timezone.utc).isoformat()
                                flight["_metadata"]["previous_collection_session_id"] = existing_doc.get("_metadata", {}).get("collection_session_id")
                            else:
                                # Nouveau document - garder les métadonnées par défaut
                                flight["_metadata"]["is_updated"] = False
                                flight["_metadata"]["update_count"] = 0
                            
                            result = collection.replace_one(
                                {"_id": flight["_id"]},
                                flight,
                                upsert=True
                            )
                            if result.upserted_id or result.modified_count > 0:
                                batch_processed += 1
                    else:
                        # Insert en lot
                        result = collection.insert_many(batch, ordered=False)
                        batch_processed = len(result.inserted_ids)
                    
                    total_processed += batch_processed
                    operation = "upserted" if upsert else "inserted"
                    self.logger.info(f"Lot {i//self.config.batch_size + 1}: {batch_processed}/{len(batch)} vols {operation}")
                    
                except Exception as e:
                    # Gérer les erreurs de bulk write (doublons, etc.)
                    if not upsert and ("BulkWriteError" in str(type(e)) or hasattr(e, 'details')):
                        details = getattr(e, 'details', {})
                        n_inserted = details.get('nInserted', 0)
                        write_errors = details.get('writeErrors', [])
                        duplicate_errors = sum(1 for err in write_errors if err.get('code') == 11000)
                        
                        total_processed += n_inserted
                        
                        if duplicate_errors > 0:
                            self.logger.info(f"Lot {i//self.config.batch_size + 1}: {n_inserted}/{len(batch)} vols insérés ({duplicate_errors} doublons ignorés)")
                        else:
                            self.logger.warning(f"Lot {i//self.config.batch_size + 1}: {n_inserted}/{len(batch)} vols insérés (erreurs: {len(write_errors)})")
                    else:
                        self.logger.warning(f"Erreur dans le lot {i//self.config.batch_size + 1}: {str(e)[:100]}...")
                    
                    continue
            
            operation = "upserted" if upsert else "inserted"
            self.logger.info(f"Total {operation}: {total_processed}/{len(flights)} vols")
            
            # Créer des index si nécessaire
            self._ensure_indexes()
            
            return total_processed > 0
            
        except Exception as e:
            operation = "upsert" if upsert else "insertion"
            self.logger.error(f"Erreur lors de l'{operation} MongoDB: {e}")
            return False
    
    def _ensure_indexes(self):
        """Crée les index nécessaires pour optimiser les requêtes"""
        try:
            collection = self.mongo_manager.database[self.config.collection_name]
            
            # Index essentiels pour les requêtes
            indexes = [
                [("flight_number", 1)],
                [("from_code", 1)],
                [("to_code", 1)],
                [("departure.scheduled_utc", 1)],
                [("_metadata.collected_at", -1)],
                [("_metadata.collection_type", 1)],
                [("_metadata.collection_session_id", 1)],
                [("_metadata.is_updated", 1)],
                [("_metadata.update_count", 1)],
                [("from_code", 1), ("departure.scheduled_utc", 1)],
                [("_metadata.collected_at", -1), ("from_code", 1)],
                [("_metadata.collection_session_id", 1), ("from_code", 1)],
                [("_metadata.is_updated", 1), ("_metadata.collection_type", 1)]
            ]
            
            for index_spec in indexes:
                try:
                    collection.create_index(index_spec)
                except Exception:
                    # Index existe déjà ou autre erreur non critique
                    pass
                    
            self.logger.info("Index MongoDB vérifiés/créés")
            
        except Exception as e:
            self.logger.warning(f"Erreur lors de la création des index: {e}")
    
    def _insert_weather_xml_to_mongodb(self, documents: List[Dict], collection_suffix: str) -> int:
        """
        Insère les documents météorologiques XML dans MongoDB par lots
        
        Args:
            documents: Liste des documents à insérer
            collection_suffix: Suffixe pour le nom de la collection (metar_xml ou taf_xml)
            
        Returns:
            Nombre de documents insérés avec succès
        """
        try:
            collection_name = f"weather_{collection_suffix}"
            collection = self.mongo_manager.database[collection_name]
            total_inserted = 0
            
            # Insertion par lots
            for i in range(0, len(documents), self.config.batch_size):
                batch = documents[i:i + self.config.batch_size]
                
                try:
                    result = collection.insert_many(batch, ordered=False)
                    batch_inserted = len(result.inserted_ids)
                    total_inserted += batch_inserted
                    
                    self.logger.info(f"Lot {collection_suffix} {i//self.config.batch_size + 1}: {batch_inserted}/{len(batch)} documents insérés")
                    
                except Exception as e:
                    # Gérer les erreurs de bulk write (doublons, etc.)
                    if "BulkWriteError" in str(type(e)) or hasattr(e, 'details'):
                        details = getattr(e, 'details', {})
                        n_inserted = details.get('nInserted', 0)
                        write_errors = details.get('writeErrors', [])
                        duplicate_errors = sum(1 for err in write_errors if err.get('code') == 11000)
                        
                        total_inserted += n_inserted
                        
                        if duplicate_errors > 0:
                            self.logger.info(f"Lot {collection_suffix} {i//self.config.batch_size + 1}: {n_inserted}/{len(batch)} documents insérés ({duplicate_errors} doublons ignorés)")
                        else:
                            self.logger.warning(f"Lot {collection_suffix} {i//self.config.batch_size + 1}: {n_inserted}/{len(batch)} documents insérés (erreurs: {len(write_errors)})")
                    else:
                        self.logger.warning(f"Erreur dans le lot {collection_suffix} {i//self.config.batch_size + 1}: {str(e)[:100]}...")
                    
                    continue
            
            self.logger.info(f"Total {collection_suffix} inséré: {total_inserted}/{len(documents)} documents")
            
            # Créer des index spécifiques pour les données météorologiques
            self._ensure_weather_indexes(collection, collection_suffix)
            
            return total_inserted
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'insertion {collection_suffix} MongoDB: {e}")
            return 0
    
    def _ensure_weather_indexes(self, collection, data_type: str):
        """Crée les index nécessaires pour les collections météorologiques"""
        try:
            if data_type == "metar_xml":
                indexes = [
                    [("@station_id", 1)],
                    [("@observation_time", -1)],
                    [("_metadata.collection_session_id", 1)],
                    [("@station_id", 1), ("@observation_time", -1)],
                    [("_metadata.collection_session_id", 1), ("@station_id", 1)]
                ]
            elif data_type == "taf_xml":
                indexes = [
                    [("@station_id", 1)],
                    [("@issue_time", -1)],
                    [("_metadata.collection_session_id", 1)],
                    [("@station_id", 1), ("@issue_time", -1)],
                    [("_metadata.collection_session_id", 1), ("@station_id", 1)]
                ]
            else:
                indexes = []
            
            for index_spec in indexes:
                try:
                    collection.create_index(index_spec)
                except Exception:
                    pass
                    
            self.logger.info(f"Index {data_type} MongoDB vérifiés/créés")
            
        except Exception as e:
            self.logger.warning(f"Erreur lors de la création des index {data_type}: {e}")


# Fonctions utilitaires et configuration
def create_config(collection_type: CollectionType, hours_offset: int = None) -> CollectionConfig:
    """Crée une configuration selon le type de collecte"""
    config = CollectionConfig()
    
    if collection_type == CollectionType.PAST:
        config.enable_xml_weather = False
        config.hour_offset = hours_offset or -20  # Par défaut il y a 20h
    else:
        config.hour_offset = hours_offset or 1  # Par défaut prochaine heure
    
    return config


def main():
    """Fonction principale pour collecte temps réel"""
    print("=== COLLECTEUR DE VOLS EN TEMPS RÉEL ===")
    
    config = create_config(CollectionType.REALTIME)
    collector = FlightCollectorMain(config)
    results = collector.collect_and_store_flights(CollectionType.REALTIME)
    
    return _print_results_and_return_success(results, "TEMPS RÉEL", config)


def main_past_flights():
    """Fonction principale pour collecte vols passés"""
    print("=== COLLECTEUR DE VOLS PASSÉS ===")
    
    config = create_config(CollectionType.PAST, hours_offset=-20)
    collector = FlightCollectorMain(config)
    results = collector.collect_and_store_flights(CollectionType.PAST)
    
    return _print_results_and_return_success(results, "PASSÉS", config)


def _print_results_and_return_success(results: CollectionResults, type_desc: str, config: CollectionConfig) -> bool:
    """Affiche les résultats et retourne le statut de succès"""
    print(f"\n=== RÉSUMÉ {type_desc} ===")
    print(f"Succès: {'✓' if results.success else '✗'}")
    print(f"Durée: {results.duration_seconds:.1f} secondes")
    print(f"Vols collectés: {results.flights_collected}")
    print(f"Vols insérés: {results.flights_inserted}")
    
    if config.enable_xml_weather:
        print(f"METAR XML collectés: {results.metar_xml_collected}")
        print(f"METAR XML insérés: {results.metar_xml_inserted}")
        print(f"TAF XML collectés: {results.taf_xml_collected}")
        print(f"TAF XML insérés: {results.taf_xml_inserted}")
    
    if results.errors:
        print(f"Erreurs: {len(results.errors)}")
        for error in results.errors:
            print(f"  - {error}")
    
    return results.success


def run_loop(collect_past_flights: bool = False):
    """
    Exécute en boucle toutes les heures à XX:05
    
    Args:
        collect_past_flights: Si True, collecte les vols passés au lieu des vols temps réel
    """
    mode_desc = "VOLS PASSÉS" if collect_past_flights else "VOLS TEMPS RÉEL"
    print(f"=== MODE BOUCLE - {mode_desc} - Exécution toutes les heures à XX:05 ===")
    print("Appuyez sur Ctrl+C pour arrêter\n")
    
    try:
        while True:
            # Calculer la prochaine exécution à XX:05
            now = datetime.now()
            next_run = now.replace(minute=5, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(hours=1)
            
            wait_seconds = (next_run - datetime.now()).total_seconds()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Prochaine exécution prévue à {next_run.strftime('%H:%M:%S')}")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Attente de {wait_seconds/60:.1f} minutes...")
            time.sleep(wait_seconds)
            
            # Exécuter la collecte selon le mode
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Début de collecte {mode_desc.lower()}...")
            start_time = datetime.now()
            
            if collect_past_flights:
                success = main_past_flights()
            else:
                success = main()
                
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            status = "✓ succès" if success else "✗ erreurs"
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Collecte {mode_desc.lower()} terminée avec {status} ({duration:.1f}s)")
            print("=" * 60 + "\n")
            
    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Arrêt demandé par l'utilisateur")
        print("Collecteur arrêté.")


def run_combined_loop():
    """
    Exécute en boucle toutes les heures à XX:05 en collectant vols actuels ET passés
    """
    print("=== MODE BOUCLE COMBINÉ - Vols actuels + passés - Exécution toutes les heures à XX:05 ===")
    print("Collecte les vols temps réel ET les vols passés à chaque exécution")
    print("Appuyez sur Ctrl+C pour arrêter\n")
    
    try:
        while True:
            # Calculer la prochaine exécution à XX:05
            now = datetime.now()
            next_run = now.replace(minute=5, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(hours=1)
            
            wait_seconds = (next_run - datetime.now()).total_seconds()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Prochaine exécution combinée prévue à {next_run.strftime('%H:%M:%S')}")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Attente de {wait_seconds/60:.1f} minutes...")
            time.sleep(wait_seconds)
            
            # Exécuter les deux collectes
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Début de collecte COMBINÉE (temps réel + passés)...")
            start_time = datetime.now()
            
            # 1. Collecte temps réel (avec météo)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → Phase 1: Collecte vols temps réel...")
            success_realtime = main()
            
            # Petite pause entre les deux collectes
            time.sleep(2)
            
            # 2. Collecte vols passés
            print(f"[{datetime.now().strftime('%H:%M:%S')}] → Phase 2: Collecte vols passés...")
            success_past = main_past_flights()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Résumé global
            if success_realtime and success_past:
                status = "✓ succès complet (temps réel + passés)"
            elif success_realtime or success_past:
                status = "⚠ succès partiel (une collecte échouée)"
            else:
                status = "✗ échec des deux collectes"
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Collecte combinée terminée avec {status} ({duration:.1f}s)")
            print("=" * 60 + "\n")
            
    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Arrêt demandé par l'utilisateur")
        print("Collecteur arrêté.")


def run_mixed_loop():
    """
    Exécute en boucle en alternant vols temps réel et vols passés
    - Minutes paires (00, 02, 04, 06, 08, 10, etc.) : vols temps réel
    - Minutes impaires (01, 03, 05, 07, 09, 11, etc.) : vols passés
    """
    print("=== MODE BOUCLE MIXTE - Alternance temps réel/passés toutes les 5 minutes ===")
    print("Temps réel: XX:05, XX:15, XX:25, XX:35, XX:45, XX:55")
    print("Vols passés: XX:10, XX:20, XX:30, XX:40, XX:50, XX:00")
    print("Appuyez sur Ctrl+C pour arrêter\n")
    
    try:
        while True:
            now = datetime.now()
            
            # Calculer la prochaine exécution (toutes les 10 minutes)
            current_minute = now.minute
            
            # Déterminer le prochain slot (05, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 00)
            next_slots = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
            next_minute = None
            
            for slot in next_slots:
                if slot > current_minute:
                    next_minute = slot
                    break
            
            if next_minute is None:
                # Prochaine heure à 00
                next_run = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
                collect_past = True  # 00 = vols passés
            else:
                next_run = now.replace(minute=next_minute, second=0, microsecond=0)
                # Minutes 05, 15, 25, 35, 45, 55 = temps réel
                # Minutes 10, 20, 30, 40, 50, 00 = passés
                collect_past = next_minute % 10 == 0
            
            mode_desc = "VOLS PASSÉS" if collect_past else "VOLS TEMPS RÉEL"
            
            wait_seconds = (next_run - datetime.now()).total_seconds()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Prochaine collecte {mode_desc.lower()} à {next_run.strftime('%H:%M:%S')}")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Attente de {wait_seconds/60:.1f} minutes...")
            time.sleep(wait_seconds)
            
            # Exécuter la collecte
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Début de collecte {mode_desc.lower()}...")
            start_time = datetime.now()
            
            if collect_past:
                success = main_past_flights()
            else:
                success = main()
                
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            status = "✓ succès" if success else "✗ erreurs"
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Collecte {mode_desc.lower()} terminée avec {status} ({duration:.1f}s)")
            print("=" * 60 + "\n")
            
    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Arrêt demandé par l'utilisateur")
        print("Collecteur arrêté.")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Collecteur de vols simplifié")
    parser.add_argument('--loop', action='store_true', help="Exécuter en boucle toutes les heures (vols actuels + passés)")
    parser.add_argument('--loop-realtime', action='store_true', help="Exécuter en boucle toutes les heures (vols temps réel seulement)")
    parser.add_argument('--loop-past', action='store_true', help="Exécuter en boucle toutes les heures (vols passés seulement)")
    parser.add_argument('--loop-mixed', action='store_true', help="Exécuter en boucle mixte (alternance temps réel/passés)")
    parser.add_argument('--past', action='store_true', help="Collecter les vols passés une seule fois (il y a 20 heures)")
    
    args = parser.parse_args()
    
    if args.loop:
        run_combined_loop()  # Par défaut: vols actuels + passés
    elif args.loop_realtime:
        run_loop(collect_past_flights=False)
    elif args.loop_past:
        run_loop(collect_past_flights=True)
    elif args.loop_mixed:
        run_mixed_loop()
    elif args.past:
        success = main_past_flights()
        exit(0 if success else 1)
    else:
        success = main()
        exit(0 if success else 1)
