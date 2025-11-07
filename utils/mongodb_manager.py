import json
import logging
import sys
import os
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, BulkWriteError
from datetime import datetime

# Ajouter le chemin parent pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.simple_logger import get_logger

class MongoDBManager:
    """
    Classe pour gérer les opérations MongoDB, notamment l'intégration de fichiers JSON
    dans des collections MongoDB.
    """
    
    def __init__(self, connection_string: str = "mongodb://localhost:27017/", 
                 database_name: str = ""):
        """
        Initialise la connexion MongoDB.
        
        Args:
            connection_string (str): Chaîne de connexion MongoDB
            database_name (str): Nom de la base de données
        """
        self.connection_string = connection_string
        self.database_name = database_name
        self.client: Optional[MongoClient] = None
        self.database: Optional[Database] = None
        self.logger = get_logger(__name__)
    
    def connect(self) -> bool:
        """
        Établit la connexion à MongoDB.
        
        Returns:
            bool: True si la connexion est réussie, False sinon
        """
        try:
            self.client = MongoClient(self.connection_string)
            # Test de la connexion
            self.client.admin.command('ping')
            self.database = self.client[self.database_name]
            self.logger.info(f"Connexion réussie à MongoDB: {self.database_name}")
            return True
        except ConnectionFailure as e:
            self.logger.error(f"Erreur de connexion à MongoDB: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Erreur inattendue lors de la connexion: {e}")
            return False
    
    def disconnect(self):
        """Ferme la connexion MongoDB."""
        if self.client:
            self.client.close()
            self.logger.info("Connexion MongoDB fermée")
    
    def load_json_file(self, file_path: str) -> Optional[List[Dict[Any, Any]]]:
        """
        Charge un fichier JSON et retourne son contenu.
        
        Args:
            file_path (str): Chemin vers le fichier JSON
            
        Returns:
            Optional[List[Dict]]: Contenu du fichier JSON ou None si erreur
        """
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"Le fichier {file_path} n'existe pas")
                return None
                
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                
            # Vérifier si c'est une liste ou un dictionnaire
            if isinstance(data, dict):
                data = [data]  # Convertir en liste si c'est un seul objet
                
            self.logger.info(f"Fichier JSON chargé: {file_path} ({len(data)} documents)")
            return data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Erreur de décodage JSON dans {file_path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement de {file_path}: {e}")
            return None
    
    def insert_json_to_collection(self, file_path: str, collection_name: str, 
                                 batch_size: int = 1000, 
                                 add_metadata: bool = True) -> bool:
        """
        Intègre un fichier JSON dans une collection MongoDB.
        
        Args:
            file_path (str): Chemin vers le fichier JSON
            collection_name (str): Nom de la collection MongoDB
            batch_size (int): Taille des lots pour l'insertion
            add_metadata (bool): Ajouter des métadonnées (timestamp, source file)
            
        Returns:
            bool: True si l'insertion est réussie, False sinon
        """
        if self.database is None:
            self.logger.error("Pas de connexion à la base de données")
            return False
            
        # Charger le fichier JSON
        data = self.load_json_file(file_path)
        if not data:
            return False
            
        try:
            collection: Collection = self.database[collection_name]
            
            # Ajouter des métadonnées si demandé
            if add_metadata:
                current_time = datetime.now()
                filename = os.path.basename(file_path)
                
                for document in data:
                    document['_metadata'] = {
                        'source_file': filename,
                        'imported_at': current_time,
                        'file_path': file_path
                    }
            
            # Insertion par lots pour optimiser les performances
            total_inserted = 0
            total_documents = len(data)
            
            for i in range(0, total_documents, batch_size):
                batch = data[i:i + batch_size]
                try:
                    result = collection.insert_many(batch, ordered=False)
                    total_inserted += len(result.inserted_ids)
                    self.logger.info(f"Lot {i//batch_size + 1}: {len(result.inserted_ids)} documents insérés")
                    
                except BulkWriteError as e:
                    # Continuer même si certains documents échouent
                    total_inserted += e.details['nInserted']
                    self.logger.warning(f"Erreurs lors de l'insertion du lot: {len(e.details['writeErrors'])} erreurs")
                    
            self.logger.info(f"Insertion terminée: {total_inserted}/{total_documents} documents dans '{collection_name}'")
            return total_inserted > 0
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'insertion dans {collection_name}: {e}")
            return False
    
    def create_index(self, collection_name: str, index_fields: List[str]) -> bool:
        """
        Crée un index sur une collection.
        
        Args:
            collection_name (str): Nom de la collection
            index_fields (List[str]): Liste des champs à indexer
            
        Returns:
            bool: True si l'index est créé, False sinon
        """
        try:
            collection = self.database[collection_name]
            index_spec = [(field, 1) for field in index_fields]
            collection.create_index(index_spec)
            self.logger.info(f"Index créé sur {collection_name}: {index_fields}")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de la création de l'index: {e}")
            return False
    
    def get_collection_stats(self, collection_name: str) -> Optional[Dict]:
        """
        Retourne les statistiques d'une collection.
        
        Args:
            collection_name (str): Nom de la collection
            
        Returns:
            Optional[Dict]: Statistiques de la collection
        """
        try:
            collection = self.database[collection_name]
            stats = {
                'count': collection.count_documents({}),
                'indexes': list(collection.list_indexes()),
                'size': self.database.command("collStats", collection_name).get('size', 0)
            }
            return stats
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des stats: {e}")
            return None
    
    def bulk_insert_json_files(self, json_files: List[str], 
                              collection_mapping: Optional[Dict[str, str]] = None) -> Dict[str, bool]:
        """
        Intègre plusieurs fichiers JSON dans MongoDB.
        
        Args:
            json_files (List[str]): Liste des chemins des fichiers JSON
            collection_mapping (Optional[Dict[str, str]]): Mapping fichier -> collection
            
        Returns:
            Dict[str, bool]: Résultats de l'insertion pour chaque fichier
        """
        results = {}
        
        for file_path in json_files:
            filename = os.path.basename(file_path)
            
            # Déterminer le nom de la collection
            if collection_mapping and file_path in collection_mapping:
                collection_name = collection_mapping[file_path]
            else:
                # Génerer un nom de collection basé sur le nom du fichier
                collection_name = filename.replace('.json', '').replace('-', '_')
            
            self.logger.info(f"Traitement de {filename} -> collection '{collection_name}'")
            success = self.insert_json_to_collection(file_path, collection_name)
            results[file_path] = success
            
        return results
    
    def query_flights_by_time_range(self, collection_name: str, 
                                   start_time_utc: str, 
                                   end_time_utc: str,
                                   time_field: str = "arrival.scheduled_utc",
                                   return_airports: bool = False) -> Optional[List[Dict]]:
        """
        Recherche des vols dans un créneau horaire spécifique.
        
        Args:
            collection_name (str): Nom de la collection à interroger
            start_time_utc (str): Heure de début au format ISO (ex: "2025-07-20T18:00:00.000Z")
            end_time_utc (str): Heure de fin au format ISO (ex: "2025-07-20T18:15:00.000Z")
            time_field (str): Champ temporel à interroger (par défaut "arrival.scheduled_utc")
            return_airports (bool): Si True, retourne une liste d'aéroports au lieu des vols complets
            
        Returns:
            Optional[List[Dict]]: Liste des vols trouvés ou liste d'aéroports, ou None si erreur
        """
        if self.database is None:
            self.logger.error("Pas de connexion à la base de données")
            return None
            
        try:
            collection = self.database[collection_name]
            
            # Construire la requête MongoDB
            query = {
                time_field: {
                    "$gte": start_time_utc,
                    "$lt": end_time_utc
                }
            }
            
            if return_airports:
                # Déterminer le champ d'aéroport à extraire selon le type de recherche
                if "departure" in time_field:
                    # Pour les départs, on veut les destinations
                    airport_field = "to_code"
                    airport_type = "destinations"
                else:
                    # Pour les arrivées, on veut les origines
                    airport_field = "from_code"
                    airport_type = "origines"
                
                # Utiliser l'agrégation pour obtenir la liste unique des aéroports
                pipeline = [
                    {"$match": query},
                    {"$group": {
                        "_id": f"${airport_field}",
                        "count": {"$sum": 1}
                    }},
                    {"$project": {
                        "airport_code": "$_id",
                        "flight_count": "$count",
                        "_id": 0
                    }},
                    {"$sort": {"flight_count": -1}}  # Tri par nombre de vols décroissant
                ]
                
                results = list(collection.aggregate(pipeline))
                
                self.logger.info(f"Requête aéroports exécutée sur '{collection_name}': {len(results)} aéroports {airport_type} "
                               f"trouvés entre {start_time_utc} et {end_time_utc}")
                
                return results
            else:
                # Exécuter la requête normale pour les vols
                cursor = collection.find(query)
                results = list(cursor)
                
                self.logger.info(f"Requête exécutée sur '{collection_name}': {len(results)} vols trouvés "
                               f"entre {start_time_utc} et {end_time_utc}")
                
                return results
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la requête sur {collection_name}: {e}")
            return None
    
    def query_flights_by_arrival_time(self, collection_name: str, 
                                     start_time_utc: str, 
                                     end_time_utc: str,
                                     use_estimated: bool = False,
                                     return_airports: bool = False) -> Optional[List[Dict]]:
        """
        Recherche des vols par heure d'arrivée dans un créneau spécifique.
        
        Args:
            collection_name (str): Nom de la collection
            start_time_utc (str): Heure de début UTC (ISO format)
            end_time_utc (str): Heure de fin UTC (ISO format)
            use_estimated (bool): Utiliser l'heure estimée au lieu de l'heure prévue
            return_airports (bool): Si True, retourne les aéroports d'origine au lieu des vols
            
        Returns:
            Optional[List[Dict]]: Liste des vols d'arrivée ou des aéroports d'origine
        """
        field = "arrival.estimated_utc" if use_estimated else "arrival.scheduled_utc"
        return self.query_flights_by_time_range(collection_name, start_time_utc, end_time_utc, field, return_airports)
    
    def query_flights_by_departure_time(self, collection_name: str, 
                                       start_time_utc: str, 
                                       end_time_utc: str,
                                       use_estimated: bool = False,
                                       return_airports: bool = False) -> Optional[List[Dict]]:
        """
        Recherche des vols par heure de départ dans un créneau spécifique.
        
        Args:
            collection_name (str): Nom de la collection
            start_time_utc (str): Heure de début UTC (ISO format)
            end_time_utc (str): Heure de fin UTC (ISO format)
            use_estimated (bool): Utiliser l'heure estimée au lieu de l'heure prévue
            return_airports (bool): Si True, retourne les aéroports de destination au lieu des vols
            
        Returns:
            Optional[List[Dict]]: Liste des vols de départ ou des aéroports de destination
        """
        field = "departure.estimated_utc" if use_estimated else "departure.scheduled_utc"
        return self.query_flights_by_time_range(collection_name, start_time_utc, end_time_utc, field, return_airports)
    
    def query_flights_advanced(self, collection_name: str, **kwargs) -> Optional[List[Dict]]:
        """
        Recherche avancée de vols avec plusieurs critères.
        
        Args:
            collection_name (str): Nom de la collection
            **kwargs: Critères de recherche possibles:
                - arrival_start_utc, arrival_end_utc: Créneau d'arrivée
                - departure_start_utc, departure_end_utc: Créneau de départ
                - from_code: Code aéroport de départ
                - to_code: Code aéroport d'arrivée
                - airline: Compagnie aérienne
                - flight_number: Numéro de vol
                - use_estimated: Utiliser les heures estimées (bool)
                
        Returns:
            Optional[List[Dict]]: Liste des vols correspondants
        """
        if self.database is None:
            self.logger.error("Pas de connexion à la base de données")
            return None
            
        try:
            collection = self.database[collection_name]
            query = {}
            
            # Critères de temps d'arrivée
            if 'arrival_start_utc' in kwargs and 'arrival_end_utc' in kwargs:
                time_field = "arrival.estimated_utc" if kwargs.get('use_estimated', False) else "arrival.scheduled_utc"
                query[time_field] = {
                    "$gte": kwargs['arrival_start_utc'],
                    "$lt": kwargs['arrival_end_utc']
                }
            
            # Critères de temps de départ
            if 'departure_start_utc' in kwargs and 'departure_end_utc' in kwargs:
                time_field = "departure.estimated_utc" if kwargs.get('use_estimated', False) else "departure.scheduled_utc"
                query[time_field] = {
                    "$gte": kwargs['departure_start_utc'],
                    "$lt": kwargs['departure_end_utc']
                }
            
            # Critères d'aéroports
            if 'from_code' in kwargs:
                query['from_code'] = kwargs['from_code']
            if 'to_code' in kwargs:
                query['to_code'] = kwargs['to_code']
                
            # Critères de vol
            if 'airline' in kwargs:
                query['airline'] = {"$regex": kwargs['airline'], "$options": "i"}  # Recherche insensible à la casse
            if 'flight_number' in kwargs:
                query['flight_number'] = kwargs['flight_number']
            
            # Exécuter la requête
            cursor = collection.find(query)
            results = list(cursor)
            
            self.logger.info(f"Requête avancée sur '{collection_name}': {len(results)} vols trouvés")
            self.logger.debug(f"Critères de recherche: {query}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la requête avancée sur {collection_name}: {e}")
            return None
    
    def get_airports_by_time_range(self, collection_name: str,
                                  start_time_utc: str,
                                  end_time_utc: str,
                                  direction: str = "arrival") -> Optional[Dict[str, List[str]]]:
        """
        Fonction utilitaire pour obtenir les listes d'aéroports dans un créneau horaire.
        
        Args:
            collection_name (str): Nom de la collection
            start_time_utc (str): Heure de début UTC
            end_time_utc (str): Heure de fin UTC
            direction (str): "arrival" pour les origines, "departure" pour les destinations
            
        Returns:
            Optional[Dict]: Dictionnaire avec les codes d'aéroports et leurs statistiques
        """
        if direction == "arrival":
            airports = self.query_flights_by_arrival_time(
                collection_name, start_time_utc, end_time_utc, return_airports=True
            )
            airport_type = "origines"
        else:
            airports = self.query_flights_by_departure_time(
                collection_name, start_time_utc, end_time_utc, return_airports=True
            )
            airport_type = "destinations"
        
        if airports:
            return {
                "type": airport_type,
                "time_range": f"{start_time_utc} - {end_time_utc}",
                "airports": [airport["airport_code"] for airport in airports],
                "airport_stats": airports,
                "total_airports": len(airports),
                "total_flights": sum(airport["flight_count"] for airport in airports)
            }
        
        return None

    def insert_all_combined_files(self, output_dir: str = "output", collection_name: str = "flights_combined") -> Dict[str, Dict[str, Any]]:
        """
        Insère tous les fichiers JSON commençant par 'combined' dans une seule collection.
        Ne traite que les fichiers à la racine du dossier output (pas les sous-dossiers).
        
        Args:
            output_dir (str): Dossier contenant les fichiers JSON (par défaut "output")
            collection_name (str): Nom de la collection unique pour tous les fichiers (par défaut "flights_combined")
            
        Returns:
            Dict[str, Dict[str, Any]]: Résultats détaillés de l'insertion pour chaque fichier
        """
        import glob
        import re
        
        if self.database is None:
            self.logger.error("Pas de connexion à la base de données")
            return {}
        
        # Rechercher SEULEMENT les fichiers combined*.json à la RACINE du dossier output
        pattern = os.path.join(output_dir, "combined*.json")
        combined_files = glob.glob(pattern, recursive=False)  # recursive=False pour éviter les sous-dossiers
        
        self.logger.info(f"Fichiers 'combined' trouvés à la racine de {output_dir}: {len(combined_files)}")
        
        results = {}
        collection = self.database[collection_name]
        
        # Statistiques globales
        total_documents_all_files = 0
        total_inserted_all_files = 0
        total_errors_all_files = 0
        
        for file_path in combined_files:
            try:
                filename = os.path.basename(file_path)
                self.logger.info(f"Traitement de: {filename}")
                
                # Analyser le nom de fichier pour extraire les informations
                # Format attendu: combined_arrival_2025-07-31.json ou combined_departure_2025-07-31.json
                match = re.match(r'combined_([a-z]+)_(\d{4}-\d{2}-\d{2})\.json', filename)
                
                if match:
                    flight_type = match.group(1)  # arrival ou departure
                    date_str = match.group(2)     # 2025-07-31
                else:
                    # Fallback
                    flight_type = "unknown"
                    date_str = "unknown"
                
                self.logger.info(f"  -> Collection unique: {collection_name}")
                
                # Charger et préparer les données
                data = self.load_json_file(file_path)
                if not data:
                    results[filename] = {
                        "success": False,
                        "error": "Impossible de charger le fichier JSON",
                        "collection": collection_name,
                        "documents_count": 0
                    }
                    continue
                
                # Ajouter des métadonnées spécifiques aux vols
                current_time = datetime.now()
                for document in data:
                    document['_metadata'] = {
                        'source_file': filename,
                        'imported_at': current_time,
                        'file_path': file_path,
                        'flight_type': flight_type,
                        'flight_date': date_str,
                        'collection_type': 'flights'
                    }
                
                # Insertion par lots dans la collection unique
                batch_size = 1000
                total_inserted = 0
                total_documents = len(data)
                errors_count = 0
                
                for i in range(0, total_documents, batch_size):
                    batch = data[i:i + batch_size]
                    try:
                        result = collection.insert_many(batch, ordered=False)
                        batch_inserted = len(result.inserted_ids)
                        total_inserted += batch_inserted
                        self.logger.info(f"    Lot {i//batch_size + 1}: {batch_inserted} documents insérés")
                        
                    except BulkWriteError as e:
                        batch_inserted = e.details['nInserted']
                        batch_errors = len(e.details['writeErrors'])
                        total_inserted += batch_inserted
                        errors_count += batch_errors
                        self.logger.warning(f"    Lot {i//batch_size + 1}: {batch_inserted} insérés, {batch_errors} erreurs")
                
                # Mettre à jour les statistiques globales
                total_documents_all_files += total_documents
                total_inserted_all_files += total_inserted
                total_errors_all_files += errors_count
                
                # Enregistrer les résultats pour ce fichier
                results[filename] = {
                    "success": total_inserted > 0,
                    "collection": collection_name,
                    "documents_total": total_documents,
                    "documents_inserted": total_inserted,
                    "documents_errors": errors_count,
                    "flight_type": flight_type,
                    "flight_date": date_str,
                    "file_path": file_path
                }
                
                self.logger.info(f"  ✓ {total_inserted}/{total_documents} documents insérés depuis {filename}")
                
            except Exception as e:
                self.logger.error(f"Erreur lors du traitement de {filename}: {e}")
                results[filename] = {
                    "success": False,
                    "error": str(e),
                    "collection": collection_name,
                    "documents_count": 0
                }
        
        # Créer les index une seule fois pour la collection unique
        if total_inserted_all_files > 0:
            try:
                self._create_combined_flight_indexes(collection_name)
            except Exception as idx_error:
                self.logger.warning(f"Erreur lors de la création des index pour {collection_name}: {idx_error}")
        
        # Résumé final
        total_files = len(results)
        successful_files = len([r for r in results.values() if r["success"]])
        
        self.logger.info(f"=== RÉSUMÉ ===")
        self.logger.info(f"Collection unique: {collection_name}")
        self.logger.info(f"Fichiers traités: {successful_files}/{total_files}")
        self.logger.info(f"Total documents: {total_documents_all_files}")
        self.logger.info(f"Total insérés: {total_inserted_all_files}")
        self.logger.info(f"Total erreurs: {total_errors_all_files}")
        
        return results
    
    def _create_combined_flight_indexes(self, collection_name: str):
        """
        Crée des index optimisés pour une collection combinée de vols (arrivals + departures).
        
        Args:
            collection_name (str): Nom de la collection
        """
        collection = self.database[collection_name]
        
        # Index de base pour tous les vols
        indexes_to_create = [
            # Index simples
            [("flight_number", 1)],
            [("from_code", 1)],
            [("to_code", 1)],
            [("airline", 1)],
            [("_metadata.flight_type", 1)],
            [("_metadata.flight_date", 1)],
            [("_metadata.source_file", 1)],
            [("_metadata.imported_at", -1)],
            
            # Index temporels
            [("arrival.scheduled_utc", 1)],
            [("arrival.estimated_utc", 1)],
            [("arrival.actual_utc", 1)],
            [("departure.scheduled_utc", 1)],
            [("departure.estimated_utc", 1)],
            [("departure.actual_utc", 1)],
            
            # Index composés pour requêtes optimisées
            [("_metadata.flight_type", 1), ("_metadata.flight_date", 1)],
            [("from_code", 1), ("arrival.scheduled_utc", 1)],
            [("to_code", 1), ("departure.scheduled_utc", 1)],
            [("airline", 1), ("_metadata.flight_date", 1)],
            [("_metadata.flight_date", 1), ("arrival.scheduled_utc", 1)],
            [("_metadata.flight_date", 1), ("departure.scheduled_utc", 1)]
        ]
        
        # Créer tous les index
        for index_spec in indexes_to_create:
            try:
                collection.create_index(index_spec)
            except Exception as e:
                # Ignorer les erreurs d'index déjà existants
                if "already exists" not in str(e).lower():
                    self.logger.warning(f"Erreur création index {index_spec}: {e}")
        
        self.logger.info(f"Index créés pour la collection combinée {collection_name}")

    def _create_flight_indexes(self, collection_name: str, flight_type: str):
        """
        Crée des index optimisés pour les collections de vols.
        
        Args:
            collection_name (str): Nom de la collection
            flight_type (str): Type de vol (arrival, departure, etc.)
        """
        collection = self.database[collection_name]
        
        # Index de base pour tous les types de vols
        basic_indexes = [
            [("flight_number", 1)],
            [("from_code", 1)],
            [("to_code", 1)],
            [("airline", 1)],
            [("_metadata.flight_date", 1)],
            [("_metadata.imported_at", -1)]
        ]
        
        # Index spécifiques selon le type de vol
        if flight_type == "arrival":
            time_indexes = [
                [("arrival.scheduled_utc", 1)],
                [("arrival.estimated_utc", 1)],
                [("arrival.actual_utc", 1)],
                [("from_code", 1), ("arrival.scheduled_utc", 1)],
                [("arrival.scheduled_utc", 1), ("to_code", 1)]
            ]
        elif flight_type == "departure":
            time_indexes = [
                [("departure.scheduled_utc", 1)],
                [("departure.estimated_utc", 1)],
                [("departure.actual_utc", 1)],
                [("to_code", 1), ("departure.scheduled_utc", 1)],
                [("departure.scheduled_utc", 1), ("from_code", 1)]
            ]
        else:
            # Index génériques si le type n'est pas reconnu
            time_indexes = [
                [("arrival.scheduled_utc", 1)],
                [("departure.scheduled_utc", 1)]
            ]
        
        # Créer tous les index
        all_indexes = basic_indexes + time_indexes
        
        for index_spec in all_indexes:
            try:
                collection.create_index(index_spec)
            except Exception as e:
                # Ignorer les erreurs d'index déjà existants
                if "already exists" not in str(e).lower():
                    self.logger.warning(f"Erreur création index {index_spec}: {e}")
        
        self.logger.info(f"Index créés pour {collection_name} (type: {flight_type})")

# Fonction utilitaire pour une utilisation rapide
def integrate_json_to_mongodb(json_file_path: str, 
                            collection_name: str,
                            connection_string: str = "mongodb://localhost:27017/",
                            database_name: str = "airlines_db") -> bool:
    """
    Fonction utilitaire pour intégrer rapidement un fichier JSON dans MongoDB.
    
    Args:
        json_file_path (str): Chemin vers le fichier JSON
        collection_name (str): Nom de la collection
        connection_string (str): Chaîne de connexion MongoDB
        database_name (str): Nom de la base de données
        
    Returns:
        bool: True si l'intégration réussit
    """
    mongo_manager = MongoDBManager(connection_string, database_name)
    
    try:
        if mongo_manager.connect():
            return mongo_manager.insert_json_to_collection(json_file_path, collection_name)
        else:
            return False
    finally:
        mongo_manager.disconnect()

# Fonction utilitaire pour insérer tous les fichiers combined
def integrate_all_combined_files(output_dir: str = "output",
                                collection_name: str = "flights_combined",
                                connection_string: str = "mongodb://localhost:27017/",
                                database_name: str = "dst_airlines") -> Dict[str, Dict[str, Any]]:
    """
    Fonction utilitaire pour intégrer rapidement tous les fichiers combined* dans une collection unique MongoDB.
    
    Args:
        output_dir (str): Dossier contenant les fichiers JSON (par défaut "output")
        collection_name (str): Nom de la collection unique (par défaut "flights_combined")
        connection_string (str): Chaîne de connexion MongoDB
        database_name (str): Nom de la base de données
        
    Returns:
        Dict[str, Dict[str, Any]]: Résultats détaillés de l'insertion
    """
    mongo_manager = MongoDBManager(connection_string, database_name)
    
    try:
        if mongo_manager.connect():
            return mongo_manager.insert_all_combined_files(output_dir, collection_name)
        else:
            return {"error": "Impossible de se connecter à MongoDB"}
    finally:
        mongo_manager.disconnect()

# Exemple d'utilisation
if __name__ == "__main__":
    # Configuration
    MONGODB_URI = "mongodb://localhost:27017/"
    DATABASE_NAME = "dst_airlines"
    
    # Initialiser le logger
    logger = get_logger(__name__)
    
    # Initialiser le gestionnaire MongoDB
    mongo_manager = MongoDBManager(MONGODB_URI, DATABASE_NAME)
    
    try:
        # Se connecter à MongoDB
        if mongo_manager.connect():
            logger.info("=== INTÉGRATION DES FICHIERS COMBINED ===")
            
            # Insérer tous les fichiers combined* du dossier output
            results = mongo_manager.insert_all_combined_files()
            
            # Afficher les résultats
            logger.info(f"\nRésultats de l'intégration:")
            for filename, result in results.items():
                if result["success"]:
                    logger.info(f"✓ {filename}")
                    logger.info(f"  Collection: {result['collection']}")
                    logger.info(f"  Documents: {result['documents_inserted']}/{result['documents_total']}")
                    logger.info(f"  Type: {result['flight_type']} | Date: {result['flight_date']}")
                else:
                    logger.error(f"✗ {filename}")
                    logger.error(f"  Erreur: {result.get('error', 'Erreur inconnue')}")
                logger.info("")     
        else:
            logger.error("Erreur de connexion à MongoDB")
            
    finally:
        mongo_manager.disconnect()