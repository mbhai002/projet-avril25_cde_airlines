#!/usr/bin/env python3
"""
Script principal pour récupérer les vols de la prochaine heure et les intégrer dans MongoDB
"""

import sys
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import time

# Ajouter le répertoire du projet au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.flight_data_scrapper import FlightDataScraper
from data.metar_xml_collector import MetarXmlCollector
from data.taf_xml_collector import TafXmlCollector
from utils.mongodb_manager import MongoDBManager
from config.simple_logger import get_logger, log_operation_time, log_database_operation


class FlightCollectorMain:
    """
    Classe principale pour orchestrer la collecte de vols et l'intégration MongoDB
    """
    
    def __init__(self, 
                 mongodb_uri: str = "mongodb://localhost:27017/",
                 database_name: str = "dst_airlines",
                 collection_name: str = "flights_realtime",
                 enable_xml_weather: bool = True):
        """
        Initialise le collecteur principal
        
        Args:
            mongodb_uri: URI de connexion MongoDB
            database_name: Nom de la base de données
            collection_name: Nom de la collection pour les vols en temps réel
            enable_xml_weather: Si True, active la collecte METAR/TAF XML
        """
        self.mongodb_uri = mongodb_uri
        self.database_name = database_name
        self.collection_name = collection_name
        self.enable_xml_weather = enable_xml_weather
        
        # Initialiser les composants
        self.scraper = FlightDataScraper(lang="en")
        self.mongo_manager = MongoDBManager(mongodb_uri, database_name)
        
        # Initialiser les collecteurs XML si activés
        if enable_xml_weather:
            self.metar_xml_collector = MetarXmlCollector()
            self.taf_xml_collector = TafXmlCollector()
        else:
            self.metar_xml_collector = None
            self.taf_xml_collector = None
        
        # Configuration du logging simplifié
        self.logger = get_logger(__name__)
        
        self.logger.info(f"FlightCollectorMain initialized - Database: {database_name}, Collection: {collection_name}, Weather: {enable_xml_weather}")
    
    def collect_and_store_next_hour_flights(self, 
                                          num_airports: int = 50,
                                          delay: float = 2.0,
                                          hour_offset: int = 1,
                                          batch_size: int = 1000) -> Dict[str, any]:
        """
        Récupère les vols de la prochaine heure et les stocke dans MongoDB
        Optionnellement, collecte aussi les données METAR/TAF XML selon enable_xml_weather
        
        Args:
            num_airports: Nombre d'aéroports à traiter
            delay: Délai entre les requêtes
            hour_offset: Décalage horaire (1 = prochaine heure)
            batch_size: Taille des lots pour l'insertion MongoDB
            
        Returns:
            Dictionnaire avec les statistiques de l'opération
        """
        operation_start_time = datetime.now()
        
        # Générer un ID unique pour cette session de collecte
        collection_session_id = f"session_{operation_start_time.strftime('%Y%m%d_%H%M%S')}_{operation_start_time.microsecond // 1000:03d}"
        
        self.logger.info(f"=== DÉBUT DE LA COLLECTE ===")
        self.logger.info(f"Session ID: {collection_session_id}")
        self.logger.info(f"Heure de début: {operation_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"Paramètres: {num_airports} aéroports, offset {hour_offset}h")
        
        results = {
            'success': False,
            'collection_session_id': collection_session_id,
            'start_time': operation_start_time.isoformat(),
            'end_time': None,
            'duration_seconds': 0,
            'flights_collected': 0,
            'flights_inserted': 0,
            'metar_xml_collected': 0,
            'metar_xml_inserted': 0,
            'taf_xml_collected': 0,
            'taf_xml_inserted': 0,
            'mongodb_connected': False,
            'errors': []
        }
        
        try:
            # Étape 1: Connexion à MongoDB
            self.logger.info("Connecting to MongoDB...")
            if not self.mongo_manager.connect():
                error_msg = "Failed to connect to MongoDB"
                self.logger.error(error_msg)
                results['errors'].append(error_msg)
                return results
                
            results['mongodb_connected'] = True
            self.logger.info("✓ MongoDB connection successful")
            
            # Étape 2: Collecte METAR/TAF XML (en premier)
            if self.enable_xml_weather:
                self.logger.info("Starting XML weather data collection (METAR/TAF)...")
                
                # Collecte METAR XML
                if self.metar_xml_collector:
                    try:
                        metar_start_time = time.time()
                        self.logger.info("Collecting METAR XML data...")
                        metar_xml_documents = self.metar_xml_collector.fetch_metar_data()
                        duration_ms = (time.time() - metar_start_time) * 1000
                        
                        if metar_xml_documents:
                            # Ajouter l'ID de session à chaque document METAR
                            for doc in metar_xml_documents:
                                doc['_collection_session_id'] = collection_session_id
                            
                            # Insertion dans MongoDB
                            metar_xml_inserted = self._insert_weather_xml_to_mongodb(
                                metar_xml_documents, 
                                "metar_xml", 
                                batch_size
                            )
                            
                            results['metar_xml_collected'] = len(metar_xml_documents)
                            results['metar_xml_inserted'] = metar_xml_inserted
                            
                            log_database_operation(
                                self.logger,
                                "insert",
                                "weather_metar_xml",
                                metar_xml_inserted,
                                duration_ms
                            )
                            
                            self.logger.info(f"✓ {metar_xml_inserted} METAR XML documents inserted ({duration_ms:.1f}ms)")
                        else:
                            self.logger.warning("No METAR XML data collected")
                            
                    except Exception as e:
                        error_msg = f"Error during METAR XML collection: {e}"
                        self.logger.error(error_msg, exc_info=True)
                        results['errors'].append(error_msg)
                
                # Collecte TAF XML
                if self.taf_xml_collector:
                    try:
                        taf_start_time = time.time()
                        self.logger.info("Collecting TAF XML data...")
                        taf_xml_documents = self.taf_xml_collector.fetch_taf_data()
                        duration_ms = (time.time() - taf_start_time) * 1000
                        
                        if taf_xml_documents:
                            # Ajouter l'ID de session à chaque document TAF
                            for doc in taf_xml_documents:
                                doc['_collection_session_id'] = collection_session_id
                            
                            # Insertion dans MongoDB
                            taf_xml_inserted = self._insert_weather_xml_to_mongodb(
                                taf_xml_documents, 
                                "taf_xml", 
                                batch_size
                            )
                            
                            results['taf_xml_collected'] = len(taf_xml_documents)
                            results['taf_xml_inserted'] = taf_xml_inserted
                            
                            log_database_operation(
                                self.logger,
                                "insert",
                                "weather_taf_xml",
                                taf_xml_inserted,
                                duration_ms
                            )
                            
                            self.logger.info(f"✓ {taf_xml_inserted} TAF XML documents inserted ({duration_ms:.1f}ms)")
                        else:
                            self.logger.warning("No TAF XML data collected")
                            
                    except Exception as e:
                        error_msg = f"Error during TAF XML collection: {e}"
                        self.logger.error(error_msg, exc_info=True)
                        results['errors'].append(error_msg)
            
            # Étape 3: Collecte des vols
            flight_collection_start_time = time.time()
            self.logger.info(f"Starting flight collection for top {num_airports} airports...")
            
            flights = self.scraper.fetch_next_hour_departures_top_airports(
                num_airports=num_airports,
                delay=delay,
                hour_offset=hour_offset,
                auto_save=False  # Pas de sauvegarde JSON, on va directement en MongoDB
            )
            
            collection_duration_ms = (time.time() - flight_collection_start_time) * 1000
            results['flights_collected'] = len(flights)
            
            log_operation_time(self.logger, "flight_collection", flight_collection_start_time)
            
            self.logger.info(f"✓ {len(flights)} flights collected ({collection_duration_ms:.1f}ms)")
            
            if not flights:
                self.logger.warning("No flights collected, but weather data was collected")
                results['success'] = True  # Succès car les données météo ont été collectées
                return results
            
            # Étape 4: Préparation des données pour MongoDB
            self.logger.info("Preparing flight data for MongoDB insertion...")
            prepared_flights = self._prepare_flights_for_mongodb(flights, collection_session_id)
            
            # Étape 5: Insertion dans MongoDB
            insertion_start_time = time.time()
            self.logger.info(f"Inserting {len(prepared_flights)} flights into MongoDB...")
            
            insertion_success = self._insert_flights_to_mongodb(
                prepared_flights, 
                batch_size
            )
            
            insertion_duration_ms = (time.time() - insertion_start_time) * 1000
            
            if insertion_success:
                results['flights_inserted'] = len(prepared_flights)
                
                log_database_operation(
                    self.logger,
                    "insert",
                    self.collection_name,
                    len(prepared_flights),
                    insertion_duration_ms
                )
                
                self.logger.info(f"✓ {len(prepared_flights)} flights inserted successfully ({insertion_duration_ms:.1f}ms)")
                results['success'] = True
            else:
                error_msg = "Error during flight insertion into MongoDB"
                self.logger.error(error_msg)
                results['errors'].append(error_msg)
                # Même en cas d'erreur pour les vols, on peut considérer un succès partiel si les données météo sont collectées
                if results['metar_xml_collected'] > 0 or results['taf_xml_collected'] > 0:
                    results['success'] = True
                    self.logger.info("Partial success: weather data collected despite flight insertion error")
                
        except Exception as e:
            error_msg = f"Unexpected error during collection: {e}"
            self.logger.error(error_msg, exc_info=True)
            results['errors'].append(error_msg)
            
        finally:
            # Fermeture de la connexion MongoDB
            self.mongo_manager.disconnect()
            
            # Statistiques finales
            end_time = datetime.now()
            results['end_time'] = end_time.isoformat()
            results['duration_seconds'] = (end_time - operation_start_time).total_seconds()
            
            # Log final avec toutes les statistiques
            self.logger.info("=== COLLECTION COMPLETED ===")
            self.logger.info(f"Session: {collection_session_id}, Success: {results['success']}, Duration: {results['duration_seconds']:.1f}s")
            self.logger.info(f"Flights: {results['flights_collected']}/{results['flights_inserted']}, METAR: {results['metar_xml_collected']}/{results['metar_xml_inserted']}, TAF: {results['taf_xml_collected']}/{results['taf_xml_inserted']}")
            
            if results['errors']:
                self.logger.warning(f"Collection completed with {len(results['errors'])} errors")
                for error in results['errors'][:3]:  # Log only first 3 errors
                    self.logger.warning(f"Error: {error}")
            
        return results
    
    def _prepare_flights_for_mongodb(self, flights: List[Dict], collection_session_id: str) -> List[Dict]:
        """
        Prépare les données de vol pour l'insertion MongoDB
        
        Args:
            flights: Liste des vols bruts
            collection_session_id: ID de session pour associer les données
            
        Returns:
            Liste des vols préparés pour MongoDB
        """
        current_time = datetime.now(timezone.utc)
        prepared_flights = []
        
        for flight in flights:
            # Ajouter des métadonnées d'import
            flight_doc = flight.copy()
            flight_doc['_metadata'] = {
                'collection_type': 'realtime_departures',
                'collected_at': current_time.isoformat(),
                'source': 'airportinfo.live',
                'script_version': '1.0'
            }
            
            # Ajouter l'ID de session pour associer avec les données météo
            flight_doc['_collection_session_id'] = collection_session_id
            
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
    
    def _insert_flights_to_mongodb(self, flights: List[Dict], batch_size: int) -> bool:
        """
        Insère les vols dans MongoDB par lots
        
        Args:
            flights: Liste des vols à insérer
            batch_size: Taille des lots
            
        Returns:
            True si l'insertion réussit, False sinon
        """
        try:
            collection = self.mongo_manager.database[self.collection_name]
            total_inserted = 0
            
            # Insertion par lots
            for i in range(0, len(flights), batch_size):
                batch = flights[i:i + batch_size]
                
                try:
                    # Utiliser insert_many avec ordered=False pour continuer même en cas de doublons
                    result = collection.insert_many(batch, ordered=False)
                    batch_inserted = len(result.inserted_ids)
                    total_inserted += batch_inserted
                    
                    self.logger.info(f"Lot {i//batch_size + 1}: {batch_inserted}/{len(batch)} vols insérés")
                    
                except Exception as e:
                    # Gérer spécifiquement les erreurs de bulk write (doublons, etc.)
                    if "BulkWriteError" in str(type(e)) or hasattr(e, 'details'):
                        # C'est une erreur de bulk write (probablement des doublons)
                        details = getattr(e, 'details', {})
                        n_inserted = details.get('nInserted', 0)
                        write_errors = details.get('writeErrors', [])
                        duplicate_errors = sum(1 for err in write_errors if err.get('code') == 11000)
                        
                        total_inserted += n_inserted
                        
                        if duplicate_errors > 0:
                            self.logger.info(f"Lot {i//batch_size + 1}: {n_inserted}/{len(batch)} vols insérés ({duplicate_errors} doublons ignorés)")
                        else:
                            self.logger.warning(f"Lot {i//batch_size + 1}: {n_inserted}/{len(batch)} vols insérés (erreurs: {len(write_errors)})")
                    else:
                        # Autre type d'erreur
                        self.logger.warning(f"Erreur dans le lot {i//batch_size + 1}: {str(e)[:100]}...")
                    
                    # Continuer avec le lot suivant
                    continue
            
            self.logger.info(f"Total inséré: {total_inserted}/{len(flights)} vols")
            
            # Créer des index si nécessaire
            self._ensure_indexes()
            
            return total_inserted > 0
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'insertion MongoDB: {e}")
            return False
    
    def _ensure_indexes(self):
        """Crée les index nécessaires pour optimiser les requêtes"""
        try:
            collection = self.mongo_manager.database[self.collection_name]
            
            # Index essentiels pour les requêtes
            indexes = [
                [("flight_number", 1)],
                [("from_code", 1)],
                [("to_code", 1)],
                [("departure.scheduled_utc", 1)],
                [("_metadata.collected_at", -1)],
                [("_metadata.collection_type", 1)],
                [("_collection_session_id", 1)],  # Index pour associer avec les données météo
                [("from_code", 1), ("departure.scheduled_utc", 1)],
                [("_metadata.collected_at", -1), ("from_code", 1)],
                [("_collection_session_id", 1), ("from_code", 1)]  # Index combiné session + aéroport
            ]
            
            for index_spec in indexes:
                try:
                    collection.create_index(index_spec)
                except Exception as e:
                    # Index existe déjà ou autre erreur non critique
                    pass
                    
            self.logger.info("Index MongoDB vérifiés/créés")
            
        except Exception as e:
            self.logger.warning(f"Erreur lors de la création des index: {e}")
    
    def _insert_weather_xml_to_mongodb(self, documents: List[Dict], collection_suffix: str, batch_size: int) -> int:
        """
        Insère les documents météorologiques XML dans MongoDB par lots
        
        Args:
            documents: Liste des documents à insérer
            collection_suffix: Suffixe pour le nom de la collection (metar_xml ou taf_xml)
            batch_size: Taille des lots
            
        Returns:
            Nombre de documents insérés avec succès
        """
        try:
            collection_name = f"weather_{collection_suffix}"
            collection = self.mongo_manager.database[collection_name]
            total_inserted = 0
            
            # Insertion par lots
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                
                try:
                    # Utiliser insert_many avec ordered=False pour continuer même en cas de doublons
                    result = collection.insert_many(batch, ordered=False)
                    batch_inserted = len(result.inserted_ids)
                    total_inserted += batch_inserted
                    
                    self.logger.info(f"Lot {collection_suffix} {i//batch_size + 1}: {batch_inserted}/{len(batch)} documents insérés")
                    
                except Exception as e:
                    # Gérer spécifiquement les erreurs de bulk write (doublons, etc.)
                    if "BulkWriteError" in str(type(e)) or hasattr(e, 'details'):
                        # C'est une erreur de bulk write (probablement des doublons)
                        details = getattr(e, 'details', {})
                        n_inserted = details.get('nInserted', 0)
                        write_errors = details.get('writeErrors', [])
                        duplicate_errors = sum(1 for err in write_errors if err.get('code') == 11000)
                        
                        total_inserted += n_inserted
                        
                        if duplicate_errors > 0:
                            self.logger.info(f"Lot {collection_suffix} {i//batch_size + 1}: {n_inserted}/{len(batch)} documents insérés ({duplicate_errors} doublons ignorés)")
                        else:
                            self.logger.warning(f"Lot {collection_suffix} {i//batch_size + 1}: {n_inserted}/{len(batch)} documents insérés (erreurs: {len(write_errors)})")
                    else:
                        # Autre type d'erreur
                        self.logger.warning(f"Erreur dans le lot {collection_suffix} {i//batch_size + 1}: {str(e)[:100]}...")
                    
                    # Continuer avec le lot suivant
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
                # Index pour les données METAR XML
                indexes = [
                    [("@station_id", 1)],
                    [("@observation_time", -1)],
                    [("_metadata_source", 1)],
                    [("_metadata_file_downloaded_at", -1)],
                    [("_collection_session_id", 1)],  # Index pour associer avec les vols
                    [("@station_id", 1), ("@observation_time", -1)],
                    [("_metadata_data_type", 1)],
                    [("_collection_session_id", 1), ("@station_id", 1)]  # Index combiné
                ]
            elif data_type == "taf_xml":
                # Index pour les données TAF XML
                indexes = [
                    [("@station_id", 1)],
                    [("@issue_time", -1)],
                    [("_metadata_source", 1)],
                    [("_metadata_file_downloaded_at", -1)],
                    [("_collection_session_id", 1)],  # Index pour associer avec les vols
                    [("@station_id", 1), ("@issue_time", -1)],
                    [("_metadata_data_type", 1)],
                    [("forecast_@fcst_time_from", 1)],
                    [("forecast_@fcst_time_to", 1)],
                    [("_collection_session_id", 1), ("@station_id", 1)]  # Index combiné
                ]
            else:
                indexes = []
            
            for index_spec in indexes:
                try:
                    collection.create_index(index_spec)
                except Exception as e:
                    # Index existe déjà ou autre erreur non critique
                    pass
                    
            self.logger.info(f"Index {data_type} MongoDB vérifiés/créés")
            
        except Exception as e:
            self.logger.warning(f"Erreur lors de la création des index {data_type}: {e}")
    
    def _extract_airport_codes_from_flights(self, flights: List[Dict]) -> List[str]:
        """
        Extrait tous les codes d'aéroports uniques des vols collectés
        
        Args:
            flights: Liste des vols
            
        Returns:
            Liste des codes d'aéroports uniques
        """
        airport_codes = set()
        
        for flight in flights:
            # Aéroport de départ
            from_code = flight.get('from_code')
            if from_code:
                airport_codes.add(from_code)
            
            # Aéroport d'arrivée
            to_code = flight.get('to_code')
            if to_code:
                airport_codes.add(to_code)
        
        return list(airport_codes)


def main():
    """Fonction principale"""
    print("=== COLLECTEUR DE VOLS EN TEMPS RÉEL ===")
    
    # Configuration
    config = {
        'mongodb_uri': "mongodb://localhost:27017/",
        'database_name': "dst_airlines2",
        'collection_name': "flights_realtime",
        'num_airports': 200,  # Nombre d'aéroports à traiter
        'delay': 1.5,        # Délai entre requêtes
        'hour_offset': 1,    # Prochaine heure
        'batch_size': 500,   # Taille des lots MongoDB
        'enable_xml_weather': True  # Activer la collecte METAR/TAF XML
    }
    
    # Initialiser le collecteur
    collector = FlightCollectorMain(
        mongodb_uri=config['mongodb_uri'],
        database_name=config['database_name'],
        collection_name=config['collection_name'],
        enable_xml_weather=config['enable_xml_weather']
    )
    
    # Lancer la collecte
    results = collector.collect_and_store_next_hour_flights(
        num_airports=config['num_airports'],
        delay=config['delay'],
        hour_offset=config['hour_offset'],
        batch_size=config['batch_size']
    )
    
    # Afficher le résumé
    print(f"\n=== RÉSUMÉ ===")
    print(f"Succès: {'✓' if results['success'] else '✗'}")
    print(f"Durée: {results['duration_seconds']:.1f} secondes")
    print(f"Vols collectés: {results['flights_collected']}")
    print(f"Vols insérés: {results['flights_inserted']}")
    if config['enable_xml_weather']:
        print(f"METAR XML collectés: {results['metar_xml_collected']}")
        print(f"METAR XML insérés: {results['metar_xml_inserted']}")
        print(f"TAF XML collectés: {results['taf_xml_collected']}")
        print(f"TAF XML insérés: {results['taf_xml_inserted']}")
    
    if results['errors']:
        print(f"Erreurs: {len(results['errors'])}")
        for error in results['errors']:
            print(f"  - {error}")
    
    return results['success']


def run_loop():
    """Exécute en boucle toutes les heures à XX:05"""
    print("=== MODE BOUCLE - Exécution toutes les heures à XX:05 ===")
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
            
            # Exécuter la collecte
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Début de collecte...")
            start_time = datetime.now()
            success = main()
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            if success:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Collecte terminée avec succès ({duration:.1f}s)")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Collecte terminée avec des erreurs ({duration:.1f}s)")
            
            print("=" * 60 + "\n")
            
    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Arrêt demandé par l'utilisateur")
        print("Collecteur arrêté.")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Collecteur de vols")
    parser.add_argument(
        '--loop', 
        action='store_true',
        help="Exécuter en boucle toutes les heures"
    )
    
    args = parser.parse_args()
    
    if args.loop:
        run_loop()
    else:
        success = main()
        exit(0 if success else 1)
