#!/usr/bin/env python3
"""
Orchestrateur principal pour la collecte de vols
"""

import sys
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import time

# Ajouter le répertoire du projet au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.flight_data_scrapper import FlightDataScraper
from data.metar_xml_collector import MetarXmlCollector
from data.taf_xml_collector import TafXmlCollector
from utils.mongodb_manager import MongoDBManager
from config.simple_logger import get_logger, log_operation_time, log_database_operation
from config.collection_config import CollectionConfig, CollectionResults, CollectionType


class FlightOrchestrator:
    """
    Orchestrateur principal pour la collecte de vols et l'intégration MongoDB
    Responsabilité : Coordonner les différentes étapes de collecte
    """
    
    def __init__(self, config: CollectionConfig):
        """
        Initialise l'orchestrateur
        
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
        
        self.logger.info(f"FlightOrchestrator initialized - Database: {config.database_name}, "
                        f"Collection: {config.collection_name}, Weather: {config.enable_xml_weather}")
    
    def collect_and_store_realtime_flights(self) -> CollectionResults:
        """
        ÉTAPE 1: Collecte et stocke les vols temps réel
        
        Returns:
            Résultats de l'opération
        """
        operation_start_time = datetime.now()
        session_id = f"realtime_{operation_start_time.strftime('%Y%m%d_%H%M%S')}_{operation_start_time.microsecond // 1000:03d}"
        
        results = CollectionResults(
            collection_session_id=session_id,
            start_time=operation_start_time.isoformat()
        )
        
        self.logger.info("=== ÉTAPE 1: COLLECTE VOLS TEMPS RÉEL ===")
        self.logger.info(f"Session ID: {session_id}")
        self.logger.info(f"Paramètres: {self.config.num_airports} aéroports, offset {self.config.hour_offset}h")
        
        try:
            # Connexion MongoDB
            if not self._connect_to_mongodb(results):
                return results
            
            # Collecte des vols temps réel
            flights = self._collect_flights(results, self.config.hour_offset, "temps réel")
            if not flights:
                results.success = True
                return results
            
            # Insertion en base
            self._insert_flights(results, flights, session_id, CollectionType.REALTIME, is_past=False)
            
        except Exception as e:
            error_msg = f"Erreur lors de la collecte vols temps réel: {e}"
            self.logger.error(error_msg, exc_info=True)
            results.errors.append(error_msg)
            
        finally:
            self._finalize_collection(results, operation_start_time, "VOLS TEMPS RÉEL")
            
        return results
    
    def collect_and_store_weather_data(self) -> CollectionResults:
        """
        ÉTAPE 2: Collecte et stocke les données météorologiques (METAR/TAF)
        
        Returns:
            Résultats de l'opération
        """
        operation_start_time = datetime.now()
        session_id = f"weather_{operation_start_time.strftime('%Y%m%d_%H%M%S')}_{operation_start_time.microsecond // 1000:03d}"
        
        results = CollectionResults(
            collection_session_id=session_id,
            start_time=operation_start_time.isoformat()
        )
        
        self.logger.info("=== ÉTAPE 2: COLLECTE DONNÉES MÉTÉO ===")
        self.logger.info(f"Session ID: {session_id}")
        self.logger.info("Collecte METAR et TAF XML")
        
        try:
            # Connexion MongoDB
            if not self._connect_to_mongodb(results):
                return results
            
            # Collecte des données météo
            if self.config.enable_xml_weather:
                self._collect_weather_data(results, session_id)
                results.success = True
            else:
                self.logger.info("Collecte météo désactivée dans la configuration")
                results.success = True
            
        except Exception as e:
            error_msg = f"Erreur lors de la collecte météo: {e}"
            self.logger.error(error_msg, exc_info=True)
            results.errors.append(error_msg)
            
        finally:
            self._finalize_collection(results, operation_start_time, "DONNÉES MÉTÉO")
            
        return results
    
    def collect_and_store_past_flights(self) -> CollectionResults:
        """
        ÉTAPE 3: Collecte et stocke les vols passés
        
        Returns:
            Résultats de l'opération
        """
        operation_start_time = datetime.now()
        session_id = f"past_{operation_start_time.strftime('%Y%m%d_%H%M%S')}_{operation_start_time.microsecond // 1000:03d}"
        
        results = CollectionResults(
            collection_session_id=session_id,
            start_time=operation_start_time.isoformat()
        )
        
        self.logger.info("=== ÉTAPE 3: COLLECTE VOLS PASSÉS ===")
        self.logger.info(f"Session ID: {session_id}")
        self.logger.info(f"Paramètres: {self.config.num_airports} aéroports, offset {self.config.past_hour_offset}h")
        
        try:
            # Connexion MongoDB
            if not self._connect_to_mongodb(results):
                return results
            
            # Collecte des vols passés
            flights = self._collect_flights(results, self.config.past_hour_offset, "vols passés")
            if not flights:
                results.success = True
                return results
            
            # Insertion en base (avec upsert)
            self._insert_flights(results, flights, session_id, CollectionType.PAST, is_past=True)
            
        except Exception as e:
            error_msg = f"Erreur lors de la collecte vols passés: {e}"
            self.logger.error(error_msg, exc_info=True)
            results.errors.append(error_msg)
            
        finally:
            self._finalize_collection(results, operation_start_time, "VOLS PASSÉS")
            
        return results
    
    def collect_and_store_flights(self, collection_type: CollectionType = CollectionType.REALTIME) -> CollectionResults:
        """
        Méthode de compatibilité - utilise les nouvelles méthodes spécialisées
        
        Args:
            collection_type: Type de collecte (temps réel ou passé)
            
        Returns:
            Résultats de l'opération
        """
        if collection_type == CollectionType.REALTIME:
            return self.collect_and_store_realtime_flights()
        else:
            return self.collect_and_store_past_flights()
    
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
    
    def _collect_flights(self, results: CollectionResults, hour_offset: int, description: str = "flights") -> List[Dict]:
        """Collecte les vols"""
        start_time = time.time()
        self.logger.info(f"Début collecte {description} (offset {hour_offset}h) pour {self.config.num_airports} aéroports...")
        
        flights = self.scraper.fetch_next_hour_departures_top_airports(
            num_airports=self.config.num_airports,
            delay=self.config.delay,
            hour_offset=hour_offset,
            auto_save=False
        )
        
        duration_ms = (time.time() - start_time) * 1000
        results.flights_collected = len(flights)
        
        log_operation_time(self.logger, f"{description.replace(' ', '_')}_collection", start_time)
        self.logger.info(f"✓ {len(flights)} {description} collectés ({duration_ms:.1f}ms)")
        
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
    
    def _finalize_collection(self, results: CollectionResults, start_time: datetime, description: str):
        """Finalise la collecte"""
        self.mongo_manager.disconnect()
        
        end_time = datetime.now()
        results.end_time = end_time.isoformat()
        results.duration_seconds = (end_time - start_time).total_seconds()
        
        # Log final
        self.logger.info(f"=== COLLECTION {description} TERMINÉE ===")
        self.logger.info(f"Session: {results.collection_session_id}, Success: {results.success}, "
                        f"Duration: {results.duration_seconds:.1f}s")
        
        # Log spécifique selon le type
        if "MÉTÉO" in description:
            self.logger.info(f"METAR: {results.metar_xml_collected}/{results.metar_xml_inserted}, "
                           f"TAF: {results.taf_xml_collected}/{results.taf_xml_inserted}")
        else:
            self.logger.info(f"Vols: {results.flights_collected}/{results.flights_inserted}")
        
        if results.errors:
            self.logger.warning(f"Collection terminée avec {len(results.errors)} erreurs")
            for error in results.errors[:3]:
                self.logger.warning(f"Error: {error}")
    
    def _prepare_flights_for_mongodb(self, flights: List[Dict], session_id: str, 
                                   collection_type: CollectionType) -> List[Dict]:
        """Prépare les données de vol pour l'insertion MongoDB"""
        current_time = datetime.now(timezone.utc)
        prepared_flights = []
        
        for flight in flights:
            # Ajouter des métadonnées d'import
            flight_doc = flight.copy()
            flight_doc['_metadata'] = {
                'collection_type': collection_type.value,
                'collected_at': current_time.isoformat(),
                'source': self.config.source,
                'script_version': self.config.script_version,
                'collection_session_id': session_id,
                'is_updated': False,
                'update_count': 0
            }
            
            # Ajouter un ID unique basé sur le vol et l'heure de collecte
            flight_doc['_id'] = self._generate_flight_id(flight, current_time)
            
            prepared_flights.append(flight_doc)
            
        return prepared_flights
    
    def _generate_flight_id(self, flight: Dict, collection_time: datetime = None) -> str:
        """
        Génère un ID unique et stable pour le vol basé sur ses caractéristiques intrinsèques
        
        Args:
            flight: Données du vol
            collection_time: Heure de collecte (ignorée pour stabilité)
            
        Returns:
            ID unique et stable pour le vol
        """
        # Utiliser les données intrinsèques du vol pour un ID stable
        departure_scheduled = flight.get('departure', {}).get('scheduled_utc', '')
        
        # Extraire la date et heure du départ programmé pour créer un ID stable
        departure_id = ""
        if departure_scheduled:
            try:
                # Nettoyer le scheduled_utc pour créer un ID stable
                # Format attendu: "2025-08-11T14:30:00Z" -> "20250811_1430"
                clean_scheduled = departure_scheduled.replace('-', '').replace(':', '').replace('T', '_').replace('Z', '')
                if len(clean_scheduled) >= 13:  # 20250811_1430
                    departure_id = clean_scheduled[:13]  # Prendre YYYYMMDD_HHMM
                else:
                    departure_id = clean_scheduled
            except:
                departure_id = "UNKNOWN_TIME"
        else:
            departure_id = "UNKNOWN_TIME"
        
        base_elements = [
            flight.get('flight_number', 'UNKNOWN'),
            flight.get('from_code', 'XXX'), 
            flight.get('to_code', 'XXX'),
            departure_id  # ID stable basé sur l'heure de départ programmée
        ]
        
        return '_'.join(str(elem) for elem in base_elements if elem)
    
    def _insert_flights_to_mongodb(self, flights: List[Dict]) -> bool:
        """Insère les vols dans MongoDB par lots (insert normal)"""
        return self._insert_or_upsert_flights(flights, upsert=False)
    
    def _upsert_flights_to_mongodb(self, flights: List[Dict]) -> bool:
        """Insère/met à jour les vols dans MongoDB par lots (upsert)"""
        return self._insert_or_upsert_flights(flights, upsert=True)
    
    def _insert_or_upsert_flights(self, flights: List[Dict], upsert: bool = False) -> bool:
        """Insère ou met à jour les vols dans MongoDB par lots"""
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
        """Insère les documents météorologiques XML dans MongoDB par lots"""
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

    def associate_flights_with_metar(self, target_session_id: str = None) -> CollectionResults:
        """
        ÉTAPE 4: Associe les données de vols avec les données METAR
        Ajoute un champ metar_id à chaque vol quand il y a correspondance ICAO/IATA
        
        Args:
            target_session_id: Session ID spécifique des vols à traiter (optionnel)
        
        Returns:
            Résultats de l'opération
        """
        operation_start_time = datetime.now()
        session_id = f"association_metar_{operation_start_time.strftime('%Y%m%d_%H%M%S')}_{operation_start_time.microsecond // 1000:03d}"
        
        results = CollectionResults(
            collection_session_id=session_id,
            start_time=operation_start_time.isoformat()
        )
        
        self.logger.info("=== ÉTAPE 4: ASSOCIATION VOLS-METAR ===")
        self.logger.info(f"Session ID: {session_id}")
        if target_session_id:
            self.logger.info(f"Filtrage sur session de vols: {target_session_id}")
        
        try:
            # Connexion MongoDB
            if not self._connect_to_mongodb(results):
                return results
            
            # Charger la table de correspondance IATA/ICAO
            iata_icao_mapping = self._load_iata_icao_mapping()
            
            if not iata_icao_mapping:
                error_msg = "Impossible de charger la correspondance IATA/ICAO"
                results.errors.append(error_msg)
                self.logger.error(error_msg)
                return results
            
            # Obtenir les collections
            flights_collection = self.mongo_manager.database[self.config.collection_name]
            metar_collection = self.mongo_manager.database["weather_metar_xml"]
            
            # Construire le filtre pour les vols
            flights_filter = {}
            if target_session_id:
                flights_filter["_metadata.collection_session_id"] = target_session_id
                self.logger.info(f"Recherche des vols avec session_id: {target_session_id}")
            else:
                # Trouver toutes les sessions de collecte de la journée courante (comportement par défaut)
                today_str = operation_start_time.strftime('%Y%m%d')
                flights_filter["_metadata.collection_session_id"] = {"$regex": f"^realtime_{today_str}"}
                self.logger.info(f"Recherche des vols de la journée: {today_str}")
            
            # Exclure les vols avec operated_by (doublons code-share)
            flights_filter["operated_by"] = {"$exists": False}
            
            # Compter les vols à traiter
            total_flights = flights_collection.count_documents(flights_filter)
            if total_flights == 0:
                self.logger.warning("Aucun vol trouvé avec les critères spécifiés")
                results.success = True
                return results
            
            self.logger.info(f"{total_flights} vols trouvés pour association METAR (doublons code-share exclus)")
            
            # Récupérer les vols selon le filtre défini
            current_flights = list(flights_collection.find(flights_filter))
            
            if not current_flights:
                self.logger.info("Aucun vol trouvé pour l'association")
                results.success = True
                return results
            
            # Récupérer tous les derniers METAR (le plus récent pour chaque station)
            latest_metars_pipeline = [
                {
                    "$sort": {"observation_time": -1}  # Trier par heure d'observation décroissante
                },
                {
                    "$group": {
                        "_id": "$station_id",  # Grouper par station (sans @)
                        "latest_metar": {"$first": "$$ROOT"}  # Prendre le plus récent
                    }
                },
                {
                    "$replaceRoot": {"newRoot": "$latest_metar"}  # Remplacer la racine
                }
            ]
            
            latest_metars = list(metar_collection.aggregate(latest_metars_pipeline))
            
            if not latest_metars:
                self.logger.info("Aucune donnée METAR trouvée dans la base pour l'association")
                results.success = True
                return results
            
            self.logger.info(f"Association de {len(current_flights)} vols avec {len(latest_metars)} derniers METAR (toutes stations)")
            
            # Créer un index de recherche METAR par station ICAO
            metar_by_icao = {}
            for metar in latest_metars:
                station_id = metar.get('station_id')  # Utiliser station_id (sans @)
                if station_id:
                    metar_by_icao[station_id] = metar.get('_id')
            
            self.logger.info(f"Index METAR créé pour {len(metar_by_icao)} stations ICAO")
            
            # Parcourir chaque vol et chercher les correspondances
            flights_updated = 0
            
            for flight in current_flights:
                try:
                    flight_updated = False
                    update_fields = {}
                    
                    # Traiter uniquement l'aéroport de départ
                    departure_iata = flight.get('from_code', '')
                    if departure_iata and departure_iata in iata_icao_mapping:
                        departure_icao = iata_icao_mapping[departure_iata]
                        if departure_icao in metar_by_icao:
                            update_fields['metar_id'] = metar_by_icao[departure_icao]
                            flight_updated = True
                            self.logger.debug(f"Vol {flight.get('_id')}: {departure_iata} -> METAR {metar_by_icao[departure_icao]}")
                    
                    # Mettre à jour le vol si une correspondance a été trouvée
                    if flight_updated:
                        # Ajouter les métadonnées d'association
                        update_fields['_metadata.metar_associated'] = True
                        update_fields['_metadata.metar_association_date'] = operation_start_time.isoformat()
                        
                        flights_collection.update_one(
                            {"_id": flight["_id"]},
                            {"$set": update_fields}
                        )
                        flights_updated += 1
                        
                except Exception as e:
                    error_msg = f"Erreur lors de l'association du vol {flight.get('_id', 'unknown')}: {e}"
                    self.logger.warning(error_msg)
                    results.errors.append(error_msg)
            
            self.logger.info(f"✓ {flights_updated} vols mis à jour avec des associations METAR")
            results.flights_inserted = flights_updated  # Réutilise ce champ pour les vols mis à jour
            results.success = True
            
        except Exception as e:
            error_msg = f"Erreur lors de l'association vols-METAR: {e}"
            self.logger.error(error_msg, exc_info=True)
            results.errors.append(error_msg)
            
        finally:
            self._finalize_collection(results, operation_start_time, "ASSOCIATION VOLS-METAR")
            
        return results
    
    def _load_iata_icao_mapping(self) -> dict:
        """
        Charge la correspondance IATA/ICAO depuis le fichier CSV
        
        Returns:
            Dictionnaire {code_iata: icao_code}
        """
        try:
            import csv
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            csv_path = os.path.join(project_root, "utils", "airports_ref.csv")
            
            mapping = {}
            
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=';')
                for row in reader:
                    iata = row.get('code_iata', '').strip()
                    icao = row.get('icao_code', '').strip()
                    if iata and icao:
                        mapping[iata] = icao
            
            self.logger.info(f"Correspondance IATA/ICAO chargée: {len(mapping)} aéroports")
            return mapping
            
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement de la correspondance IATA/ICAO: {e}")
            return {}

    def _find_matching_taf_forecast(self, tafs_list: list, arrival_time_utc: str) -> dict:
        """
        Trouve le forecast TAF qui correspond à l'heure d'arrivée du vol
        Priorité: 1) Interval le plus petit, 2) Priorité des indicateurs de changement
        
        Args:
            tafs_list: Liste des TAF pour une station
            arrival_time_utc: Heure d'arrivée UTC du vol au format ISO
            
        Returns:
            Dictionnaire du TAF forecast correspondant ou None
        """
        try:
            from datetime import datetime
            
            # Convertir l'heure d'arrivée en objet datetime
            arrival_dt = datetime.fromisoformat(arrival_time_utc.replace('Z', '+00:00'))
            
            # Définir la priorité des indicateurs de changement (plus bas = meilleur)
            priority_map = {
                'FM': 1,      # FROM - changement permanent, priorité max
                'BECMG': 2,   # BECOMING - changement graduel
                'TEMPO': 3,   # TEMPORARY - changement temporaire
                'PROB': 4,    # PROBABILITY - changement probable
                None: 5,      # Aucun indicateur
                '': 5         # Indicateur vide
            }
            
            candidates = []
            
            for taf in tafs_list:
                try:
                    # Vérifier si c'est un forecast TAF (pas juste base)
                    if taf.get('_metadata_data_type') != 'TAF_FORECAST':
                        continue
                    
                    fcst_time_from = taf.get('forecast_fcst_time_from')
                    fcst_time_to = taf.get('forecast_fcst_time_to')
                    
                    if not fcst_time_from:
                        continue
                    
                    # Convertir les heures de forecast
                    from_dt = datetime.fromisoformat(fcst_time_from.replace('Z', '+00:00'))
                    to_dt = None
                    interval_duration = float('inf')  # Durée de l'intervalle
                    
                    if fcst_time_to:
                        to_dt = datetime.fromisoformat(fcst_time_to.replace('Z', '+00:00'))
                        interval_duration = (to_dt - from_dt).total_seconds()
                    
                    # Vérifier si l'heure d'arrivée est dans l'intervalle
                    is_in_interval = False
                    distance_to_center = 0
                    
                    if to_dt:
                        # Intervalle fermé [from, to]
                        if from_dt <= arrival_dt <= to_dt:
                            is_in_interval = True
                            # Distance au centre de l'intervalle
                            center_dt = from_dt + (to_dt - from_dt) / 2
                            distance_to_center = abs((arrival_dt - center_dt).total_seconds())
                    else:
                        # Intervalle ouvert [from, +∞)
                        if arrival_dt >= from_dt:
                            is_in_interval = True
                            # Distance depuis le début (pénalisée pour les intervalles ouverts)
                            distance_to_center = abs((arrival_dt - from_dt).total_seconds())
                    
                    if is_in_interval:
                        # Récupérer l'indicateur de changement
                        change_indicator = taf.get('forecast_change_indicator')
                        priority = priority_map.get(change_indicator, 5)
                        
                        candidates.append({
                            'taf': taf,
                            'interval_duration': interval_duration,
                            'distance_to_center': distance_to_center,
                            'change_priority': priority,
                            'change_indicator': change_indicator
                        })
                
                except Exception as e:
                    self.logger.debug(f"Erreur lors de l'analyse du TAF {taf.get('_id')}: {e}")
                    continue
            
            # Trier les candidats selon les critères de priorité
            if not candidates:
                return None
            
            # Tri par:
            # 1. Priorité de l'indicateur de changement (FM > BECMG > TEMPO > PROB > rien)
            # 2. Durée d'intervalle (plus petit = mieux)
            # 3. Distance au centre (plus proche = mieux)
            candidates.sort(key=lambda x: (
                x['change_priority'],      # Priorité indicateur (1=FM, 5=rien)
                x['interval_duration'],    # Durée intervalle (plus petit = mieux)
                x['distance_to_center']    # Distance centre (plus petit = mieux)
            ))
            
            best_match = candidates[0]['taf']
            
            # Log de débogage amélioré
            if best_match:
                best_candidate = candidates[0]
                duration_hours = best_candidate['interval_duration'] / 3600 if best_candidate['interval_duration'] != float('inf') else '∞'
                distance_hours = best_candidate['distance_to_center'] / 3600
                indicator = best_candidate['change_indicator'] or 'Base'
                
                self.logger.debug(f"TAF trouvé pour {arrival_time_utc}: {best_match.get('_id')} "
                                f"(indicateur: {indicator}, durée: {duration_hours}h, "
                                f"distance: {distance_hours:.1f}h)")
            
            return best_match
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la recherche TAF pour {arrival_time_utc}: {e}")
            return None

    def associate_flights_with_taf(self, target_session_id: str = None) -> CollectionResults:
        """
        ÉTAPE 5: Associe les données de vols avec les données TAF
        Ajoute un champ taf_id aux vols pour l'aéroport d'arrivée quand il y a correspondance ICAO/IATA
        
        Args:
            target_session_id: Session ID spécifique des vols à traiter (optionnel)
        
        Returns:
            Résultats de l'opération
        """
        operation_start_time = datetime.now()
        session_id = f"association_taf_{operation_start_time.strftime('%Y%m%d_%H%M%S')}_{operation_start_time.microsecond // 1000:03d}"
        
        results = CollectionResults(
            collection_session_id=session_id,
            start_time=operation_start_time.isoformat()
        )
        
        self.logger.info("=== ÉTAPE 5: ASSOCIATION VOLS-TAF ===")
        self.logger.info(f"Session ID: {session_id}")
        if target_session_id:
            self.logger.info(f"Filtrage sur session de vols: {target_session_id}")
        
        try:
            # Connexion MongoDB
            if not self._connect_to_mongodb(results):
                return results
            
            # Charger la table de correspondance IATA/ICAO
            iata_icao_mapping = self._load_iata_icao_mapping()
            
            if not iata_icao_mapping:
                error_msg = "Impossible de charger la correspondance IATA/ICAO"
                results.errors.append(error_msg)
                self.logger.error(error_msg)
                return results
            
            # Obtenir les collections
            flights_collection = self.mongo_manager.database[self.config.collection_name]
            taf_collection = self.mongo_manager.database["weather_taf_xml"]
            
            # Construire le filtre pour les vols
            flights_filter = {}
            if target_session_id:
                flights_filter["_metadata.collection_session_id"] = target_session_id
                self.logger.info(f"Recherche des vols avec session_id: {target_session_id}")
            else:
                # Trouver toutes les sessions de collecte de la journée courante (comportement par défaut)
                today_str = operation_start_time.strftime('%Y%m%d')
                flights_filter["_metadata.collection_session_id"] = {"$regex": f"^realtime_{today_str}"}
                self.logger.info(f"Recherche des vols de la journée: {today_str}")
            
            # Exclure les vols avec operated_by (doublons code-share)
            flights_filter["operated_by"] = {"$exists": False}
            
            # Compter les vols à traiter
            total_flights = flights_collection.count_documents(flights_filter)
            if total_flights == 0:
                self.logger.warning("Aucun vol trouvé avec les critères spécifiés")
                results.success = True
                return results
            
            self.logger.info(f"{total_flights} vols trouvés pour association TAF (doublons code-share exclus)")
            
            # Récupérer les vols selon le filtre défini
            current_flights = list(flights_collection.find(flights_filter))
            
            if not current_flights:
                self.logger.info("Aucun vol trouvé pour l'association TAF")
                results.success = True
                return results
            
            # Récupérer uniquement les TAF dont l'intervalle de fin est supérieur à l'heure courante
            # Cela évite de récupérer les forecasts expirés
            current_time_iso = operation_start_time.isoformat() + "Z"
            
            valid_tafs = list(taf_collection.find({
                "$or": [
                    # TAF avec intervalle de fin dans le futur
                    {"forecast_fcst_time_to": {"$gte": current_time_iso}},
                    # TAF sans heure de fin (intervalle ouvert)
                    {"forecast_fcst_time_to": {"$exists": False}},
                    {"forecast_fcst_time_to": None}
                ]
            }))
            
            if not valid_tafs:
                self.logger.info("Aucune donnée TAF valide trouvée dans la base pour l'association")
                results.success = True
                return results
            
            self.logger.info(f"Association de {len(current_flights)} vols avec {len(valid_tafs)} forecasts TAF valides (filtrés par heure)")
            
            # Créer un index de recherche TAF par station ICAO et intervalle de temps
            tafs_by_station = {}
            for taf in valid_tafs:
                station_id = taf.get('station_id')
                if station_id:
                    if station_id not in tafs_by_station:
                        tafs_by_station[station_id] = []
                    tafs_by_station[station_id].append(taf)
            
            self.logger.info(f"Index TAF créé pour {len(tafs_by_station)} stations ICAO")
            
            # Parcourir chaque vol et chercher les correspondances TAF par intervalle
            flights_updated = 0
            
            for flight in current_flights:
                try:
                    flight_updated = False
                    update_fields = {}
                    
                    # Traiter uniquement l'aéroport d'arrivée
                    arrival_iata = flight.get('to_code', '')
                    arrival_time_utc = flight.get('arrival', {}).get('scheduled_utc', '')
                    
                    if arrival_iata and arrival_iata in iata_icao_mapping and arrival_time_utc:
                        arrival_icao = iata_icao_mapping[arrival_iata]
                        
                        if arrival_icao in tafs_by_station:
                            # Trouver le TAF forecast qui correspond à l'heure d'arrivée
                            matching_taf = self._find_matching_taf_forecast(
                                tafs_by_station[arrival_icao], 
                                arrival_time_utc
                            )
                            
                            if matching_taf:
                                update_fields['taf_id'] = matching_taf.get('_id')
                                flight_updated = True
                                self.logger.debug(f"Vol {flight.get('_id')}: {arrival_iata} ({arrival_time_utc}) -> TAF {matching_taf.get('_id')}")
                    
                    # Mettre à jour le vol si une correspondance a été trouvée
                    if flight_updated:
                        # Ajouter les métadonnées d'association
                        update_fields['_metadata.taf_associated'] = True
                        update_fields['_metadata.taf_association_date'] = operation_start_time.isoformat()
                        
                        flights_collection.update_one(
                            {"_id": flight["_id"]},
                            {"$set": update_fields}
                        )
                        flights_updated += 1
                        
                except Exception as e:
                    error_msg = f"Erreur lors de l'association TAF du vol {flight.get('_id', 'unknown')}: {e}"
                    self.logger.warning(error_msg)
                    results.errors.append(error_msg)
            
            self.logger.info(f"✓ {flights_updated} vols mis à jour avec des associations TAF")
            results.flights_inserted = flights_updated  # Réutilise ce champ pour les vols mis à jour
            results.success = True
            
        except Exception as e:
            error_msg = f"Erreur lors de l'association vols-TAF: {e}"
            self.logger.error(error_msg, exc_info=True)
            results.errors.append(error_msg)
            
        finally:
            self._finalize_collection(results, operation_start_time, "ASSOCIATION VOLS-TAF")
            
        return results
