import os
import gzip
import requests
import urllib3
import xmltodict
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import sys

# Ajouter le chemin parent pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.simple_logger import get_logger

# Désactiver les warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TafCollector:
    """
    Classe pour récupérer les données TAF au format XML depuis aviationweather.gov
    et les convertir en documents JSON.
    """
    
    TAF_URL = "https://aviationweather.gov/data/cache/tafs.cache.xml.gz"
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialise le collecteur TAF XML.
        
        Args:
            data_dir: Répertoire où stocker les fichiers temporaires XML.
                     Si None, utilise ./data/taf
        """
        if data_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.data_dir = os.path.join(project_root, "data", "taf")
        else:
            self.data_dir = data_dir
            
        # Créer le répertoire si nécessaire
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialiser le logger
        self.logger = get_logger(__name__)
        
    def download_file(self) -> Optional[str]:
        """
        Télécharge le fichier TAF XML compressé depuis aviationweather.gov.
        
        Returns:
            str: Chemin vers le fichier XML décompressé, ou None en cas d'erreur
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            gz_filename = f"tafs_{timestamp}.xml.gz"
            xml_filename = f"tafs_{timestamp}.xml"
            
            gz_filepath = os.path.join(self.data_dir, gz_filename)
            xml_filepath = os.path.join(self.data_dir, xml_filename)
            
            self.logger.info(f"Téléchargement depuis {self.TAF_URL}")
            
            # Télécharger le fichier
            response = requests.get(self.TAF_URL, stream=True, timeout=30, verify=False)
            response.raise_for_status()
            
            # Sauvegarder le fichier compressé
            with open(gz_filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.logger.info(f"Fichier téléchargé: {gz_filename}")
            
            # Décompresser le fichier
            with gzip.open(gz_filepath, 'rt', encoding='utf-8') as gz_file:
                with open(xml_filepath, 'w', encoding='utf-8') as xml_file:
                    xml_file.write(gz_file.read())
            
            self.logger.info(f"Fichier décompressé: {xml_filename}")
            
            # Supprimer le fichier compressé pour économiser l'espace
            os.remove(gz_filepath)
            
            return xml_filepath
            
        except Exception as e:
            self.logger.error(f"Erreur lors du téléchargement: {e}")
            traceback.print_exc()
            return None
    
    def _flatten_dict(self, data: Dict, prefix: str = '', exclude_keys: List[str] = None) -> Dict:
        """
        Aplatit un dictionnaire imbriqué en séparant les attributs XML avec des préfixes.
        
        Args:
            data: Dictionnaire à aplatir
            prefix: Préfixe à ajouter aux clés
            exclude_keys: Liste des clés à exclure
            
        Returns:
            Dict: Dictionnaire aplati
        """
        if exclude_keys is None:
            exclude_keys = []
        
        result = {}
        
        if not isinstance(data, dict):
            return result
        
        for key, value in data.items():
            if key in exclude_keys:
                continue
                
            # Construire la nouvelle clé
            new_key = f"{prefix}{key}" if prefix else key
            
            if isinstance(value, dict):
                # Si c'est un dictionnaire, l'aplatir récursivement
                result.update(self._flatten_dict(value, prefix=f"{new_key}_", exclude_keys=exclude_keys))
            elif isinstance(value, list):
                # Si c'est une liste, ne pas l'aplatir pour préserver les structures
                result[new_key] = value
            else:
                # Valeur simple
                result[new_key] = value
        
        return result
    
    def _convert_numeric_fields(self, doc: Dict) -> None:
        """
        Convertit les champs numériques en int/float quand c'est possible.
        Modifie le dictionnaire en place.
        
        Args:
            doc: Document à modifier
        """
        numeric_patterns = [
            'latitude', 'longitude', 'elevation_m', 'temp_c', 'dewpoint_c',
            'wind_dir_degrees', 'wind_speed_kt', 'wind_gust_kt',
            'visibility_statute_mi', 'altim_in_hg',
            'cloud_base_ft_agl', 'max_temp_c', 'min_temp_c'
        ]
        
        for key, value in doc.items():
            # Vérifier si la clé contient un pattern numérique
            should_convert = any(pattern in key.lower() for pattern in numeric_patterns)
            
            if should_convert and value and str(value) not in ['VRB', 'NSC', '6+', 'CAVOK']:
                try:
                    str_value = str(value)
                    if '.' in str_value:
                        doc[key] = float(value)
                    else:
                        doc[key] = int(value)
                except (ValueError, TypeError):
                    pass  # Garder la valeur originale si conversion impossible
    
    def parse_to_json(self, xml_filepath: str) -> List[Dict]:
        """
        Parse le fichier XML TAF et convertit en liste de documents JSON.
        Un document par forecast pour préserver les détails des prévisions.
        
        Args:
            xml_filepath: Chemin vers le fichier XML à parser
            
        Returns:
            List[Dict]: Liste des documents TAF convertis en JSON
        """
        try:
            self.logger.info(f"Lecture du fichier TAF XML: {os.path.basename(xml_filepath)}")
            
            # Lire et parser le fichier XML avec xmltodict
            with open(xml_filepath, 'r', encoding='utf-8') as xml_file:
                xml_content = xml_file.read()
            
            # Convertir XML en dictionnaire Python
            data = xmltodict.parse(xml_content)
            self.logger.info("XML parsé avec xmltodict")
            
            documents = []
            
            # Naviguer dans la structure du dictionnaire
            response = data.get('response', {})
            
            # Les TAF peuvent être dans data.data ou directement dans data
            taf_data = response.get('data', {})
            tafs = taf_data.get('TAF', [])
            
            # Si TAF n'est pas une liste, en faire une
            if not isinstance(tafs, list):
                tafs = [tafs] if tafs else []
            
            self.logger.info(f"{len(tafs)} éléments TAF trouvés")
            
            for taf in tafs:
                if not taf:  # Skip empty TAF
                    continue
                    
                # Aplatir la structure du TAF (extraire attributs et valeurs, exclure forecasts)
                base_doc = self._flatten_dict(taf, exclude_keys=['forecast'])
                
                # Traiter les forecasts
                forecasts = taf.get('forecast', [])
                
                # Si forecast n'est pas une liste, en faire une
                if not isinstance(forecasts, list):
                    forecasts = [forecasts] if forecasts else []
                
                if not forecasts:
                    # Si pas de forecast, créer un document avec juste les données de base
                    doc = base_doc.copy()
                    
                    # Créer un ID unique
                    station_id = doc.get('@station_id') or doc.get('station_id')
                    issue_time = doc.get('@issue_time') or doc.get('issue_time') or doc.get('@bulletin_time') or doc.get('bulletin_time')
                    
                    if station_id and issue_time:
                        doc["_id"] = f"{station_id}_{issue_time}_base"
                    else:
                        doc["_id"] = f"taf_{len(documents)}_base"
                    
                    # Ajouter des métadonnées
                    doc["_metadata"] = {
                        "source": "aviationweather.gov",
                        "data_type": "TAF_BASE",
                        "file_downloaded_at": datetime.now(),
                        "xml_file": os.path.basename(xml_filepath),
                        "total_fields": len(doc),
                        "forecast_index": None
                    }
                    
                    documents.append(doc)
                else:
                    # Créer un document pour chaque forecast
                    for forecast_idx, forecast in enumerate(forecasts):
                        if not forecast:  # Skip empty forecast
                            continue
                            
                        doc = base_doc.copy()
                        
                        # Aplatir et ajouter les données du forecast avec préfixe
                        forecast_data = self._flatten_dict(forecast, prefix='forecast_')
                        doc.update(forecast_data)
                        
                        # Convertir les valeurs numériques
                        self._convert_numeric_fields(doc)
                        
                        # Créer un ID unique incluant l'index du forecast pour distinguer les variations météo
                        station_id = doc.get('@station_id') or doc.get('station_id')
                        issue_time = doc.get('@issue_time') or doc.get('issue_time') or doc.get('@bulletin_time') or doc.get('bulletin_time')
                        fcst_time_from = doc.get('forecast_@fcst_time_from', '') or doc.get('forecast_fcst_time_from', '')
                        fcst_time_to = doc.get('forecast_@fcst_time_to', '') or doc.get('forecast_fcst_time_to', '')
                        
                        if station_id and issue_time and fcst_time_from and fcst_time_to:
                            doc["_id"] = f"{station_id}_{issue_time}_{fcst_time_from}_{fcst_time_to}_f{forecast_idx}"
                        elif station_id and issue_time and fcst_time_from:
                            doc["_id"] = f"{station_id}_{issue_time}_{fcst_time_from}_f{forecast_idx}"
                        elif station_id and issue_time:
                            doc["_id"] = f"{station_id}_{issue_time}_f{forecast_idx}"
                        else:
                            doc["_id"] = f"taf_{len(documents)}_f{forecast_idx}"
                        
                        # Ajouter des métadonnées
                        doc["_metadata"] = {
                            "source": "aviationweather.gov",
                            "data_type": "TAF_FORECAST",
                            "file_downloaded_at": datetime.now(),
                            "xml_file": os.path.basename(xml_filepath),
                            "total_fields": len(doc),
                            "forecast_index": forecast_idx
                        }
                        
                        documents.append(doc)
            
            self.logger.info(f"{len(documents)} documents TAF créés")
            
            # Afficher quelques infos sur les documents si disponibles
            if documents:
                # Compter les types de documents
                base_docs = sum(1 for doc in documents if doc.get('_metadata', {}).get('data_type') == 'TAF_BASE')
                forecast_docs = sum(1 for doc in documents if doc.get('_metadata', {}).get('data_type') == 'TAF_FORECAST')
                
                self.logger.info(f"Documents de base TAF: {base_docs}")
                self.logger.info(f"Documents de forecast: {forecast_docs}")
                
                # Exemple de forecast
                forecast_doc = next((doc for doc in documents if doc.get('_metadata', {}).get('data_type') == 'TAF_FORECAST'), None)
                if forecast_doc:
                    station_id = forecast_doc.get('@station_id') or forecast_doc.get('station_id')
                    issue_time = forecast_doc.get('@issue_time') or forecast_doc.get('issue_time')
                    fcst_from = forecast_doc.get('forecast_@fcst_time_from') or forecast_doc.get('forecast_fcst_time_from')
                    fcst_to = forecast_doc.get('forecast_@fcst_time_to') or forecast_doc.get('forecast_fcst_time_to')
                    wind_dir = forecast_doc.get('forecast_@wind_dir_degrees') or forecast_doc.get('forecast_wind_dir_degrees')
                    wind_speed = forecast_doc.get('forecast_@wind_speed_kt') or forecast_doc.get('forecast_wind_speed_kt')
                    
                    self.logger.info(f"Exemple - Station: {station_id}, Issue: {issue_time}")
                    self.logger.info(f"Période: {fcst_from} -> {fcst_to}")
                    self.logger.info(f"Vent: {wind_dir}° à {wind_speed}kt")
                    self.logger.info(f"Clés par document: {len(forecast_doc)}")
            
            return documents
            
        except Exception as e:
            self.logger.error(f"Erreur lors du parsing XML TAF: {e}")
            traceback.print_exc()
            return []
    
    def fetch_taf_data(self) -> List[Dict]:
        """
        Méthode principale qui télécharge le fichier XML et le convertit en JSON.
        
        Returns:
            List[Dict]: Liste des documents TAF en format JSON
        """
        # 1. Télécharger le fichier XML
        xml_filepath = self.download_file()
        if not xml_filepath:
            self.logger.error("Impossible de télécharger le fichier XML")
            return []
        
        # 2. Parser le XML en JSON
        documents = self.parse_to_json(xml_filepath)
        
        # 3. Nettoyer le fichier temporaire
        try:
            os.remove(xml_filepath)
            self.logger.info(f"Fichier temporaire supprimé: {os.path.basename(xml_filepath)}")
        except Exception as e:
            self.logger.warning(f"Impossible de supprimer le fichier temporaire: {e}")
        
        # 4. Nettoyer les anciens fichiers
        self.cleanup_old_files()
        
        return documents
    
    def cleanup_old_files(self, keep_count: int = 5) -> None:
        """
        Nettoie les anciens fichiers XML et GZ pour économiser l'espace disque.
        
        Args:
            keep_count: Nombre de fichiers à conserver (par défaut 5)
        """
        try:
            # Nettoyer les fichiers XML
            xml_files = sorted([f for f in os.listdir(self.data_dir) if f.endswith('.xml')])
            
            if len(xml_files) > keep_count:
                files_to_delete = xml_files[:-keep_count]
                for file_to_delete in files_to_delete:
                    file_path = os.path.join(self.data_dir, file_to_delete)
                    os.remove(file_path)
                    self.logger.info(f"Ancien fichier TAF supprimé: {file_to_delete}")
            
            # Nettoyer aussi les éventuels fichiers .gz résiduels
            gz_files = [f for f in os.listdir(self.data_dir) if f.endswith('.xml.gz')]
            for gz_file in gz_files:
                file_path = os.path.join(self.data_dir, gz_file)
                os.remove(file_path)
                self.logger.info(f"Fichier .gz résiduel supprimé: {gz_file}")
                    
        except Exception as e:
            self.logger.warning(f"Erreur lors du nettoyage: {e}")


# Exemple d'utilisation
if __name__ == "__main__":
    # Créer une instance du collecteur
    collector = TafCollector()
    logger = get_logger(__name__)
    
    # Récupérer les données TAF
    logger.info("Démarrage de la collecte TAF...")
    taf_documents = collector.fetch_taf_data()
    
    if taf_documents:
        logger.info(f"{len(taf_documents)} documents TAF récupérés")
        
        # Compter les types de documents
        base_docs = sum(1 for doc in taf_documents if doc.get('_metadata', {}).get('data_type') == 'TAF_BASE')
        forecast_docs = sum(1 for doc in taf_documents if doc.get('_metadata', {}).get('data_type') == 'TAF_FORECAST')
        
        logger.info(f"Documents de base: {base_docs}")
        logger.info(f"Documents de forecast: {forecast_docs}")
        
        # Afficher quelques exemples
        forecast_examples = [doc for doc in taf_documents if doc.get('_metadata', {}).get('data_type') == 'TAF_FORECAST'][:3]
        for i, doc in enumerate(forecast_examples):
            station_id = doc.get('@station_id') or doc.get('station_id', 'N/A')
            fcst_from = doc.get('forecast_@fcst_time_from') or doc.get('forecast_fcst_time_from', 'N/A')
            fcst_to = doc.get('forecast_@fcst_time_to') or doc.get('forecast_fcst_time_to', 'N/A')
            logger.info(f"Exemple {i+1}: Station {station_id}, Période: {fcst_from} -> {fcst_to}")
    else:
        logger.error("Aucune donnée TAF récupérée")
    
    # Nettoyer les anciens fichiers
    collector.cleanup_old_files()
