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


        mongo_manager.disconnect()