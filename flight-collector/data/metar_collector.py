import os
import gzip
import requests
import urllib3
import xmltodict
import traceback
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import sys

# Ajouter le chemin parent pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.simple_logger import get_logger

# Désactiver les warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class MetarCollector:
    """
    Classe pour récupérer les données METAR au format XML depuis aviationweather.gov
    et les convertir en documents JSON.
    """
    
    METAR_URL = "https://aviationweather.gov/data/cache/metars.cache.xml.gz"
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialise le collecteur METAR.
        
        Args:
            data_dir: Répertoire où stocker les fichiers temporaires XML.
                     Si None, utilise ./data/metar
        """
        if data_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.data_dir = os.path.join(project_root, "data", "metar")
        else:
            self.data_dir = data_dir
            
        # Créer le répertoire si nécessaire
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialiser le logger
        self.logger = get_logger(__name__)
        
    def download_file(self, max_retries: int = 5) -> Optional[str]:
        """
        Télécharge le fichier METAR XML compressé depuis aviationweather.gov avec retry.
        
        Args:
            max_retries: Nombre maximum de tentatives de téléchargement
        
        Returns:
            str: Chemin vers le fichier XML décompressé, ou None en cas d'échec après toutes les tentatives
        """
        for attempt in range(1, max_retries + 1):
            try:
                self.logger.info(f"Tentative {attempt}/{max_retries} de téléchargement METAR...")
                result = self._download_attempt()
                if result is not None:
                    self.logger.info(f"✅ Téléchargement METAR réussi à la tentative {attempt}")
                    return result
                else:
                    if attempt < max_retries:
                        wait_time = attempt * 2  # Attente progressive: 2s, 4s, 6s, 8s
                        self.logger.warning(f"Tentative {attempt} échouée, nouvelle tentative dans {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        self.logger.error(f"❌ Échec du téléchargement METAR après {max_retries} tentatives")
            except Exception as e:
                self.logger.error(f"Erreur à la tentative {attempt}/{max_retries}: {e}")
                if attempt < max_retries:
                    wait_time = attempt * 2
                    self.logger.warning(f"Nouvelle tentative dans {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"❌ Échec définitif après {max_retries} tentatives")
                    traceback.print_exc()
        
        return None
    
    def _download_attempt(self) -> Optional[str]:
        """
        Une tentative de téléchargement du fichier METAR.
        
        Returns:
            str: Chemin vers le fichier XML décompressé, ou None en cas d'erreur
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            gz_filename = f"metars_{timestamp}.xml.gz"
            xml_filename = f"metars_{timestamp}.xml"
            
            gz_filepath = os.path.join(self.data_dir, gz_filename)
            xml_filepath = os.path.join(self.data_dir, xml_filename)
            
            self.logger.info(f"Téléchargement depuis {self.METAR_URL}")
            
            # Télécharger le fichier
            response = requests.get(self.METAR_URL, stream=True, timeout=30, verify=False)
            response.raise_for_status()
            
            # Sauvegarder le fichier compressé
            with open(gz_filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.logger.info(f"Fichier téléchargé: {gz_filename}")
            
            # Vérifier la taille du fichier
            file_size = os.path.getsize(gz_filepath)
            self.logger.info(f"Taille du fichier téléchargé: {file_size} bytes")
            
            if file_size < 1000:  # Fichier trop petit, probablement invalide
                self.logger.error(f"Fichier téléchargé trop petit ({file_size} bytes), probablement corrompu")
                os.remove(gz_filepath)
                return None
            
            # Décompresser le fichier avec gestion d'erreur robuste
            try:
                with gzip.open(gz_filepath, 'rt', encoding='utf-8') as gz_file:
                    with open(xml_filepath, 'w', encoding='utf-8') as xml_file:
                        xml_file.write(gz_file.read())
            except EOFError as eof_error:
                self.logger.warning(f"Fichier gzip incomplet, tentative de récupération partielle: {eof_error}")
                # Essayer de lire partiellement le fichier corrompu
                try:
                    with gzip.open(gz_filepath, 'rt', encoding='utf-8', errors='ignore') as gz_file:
                        with open(xml_filepath, 'w', encoding='utf-8') as xml_file:
                            # Lire par blocs pour éviter l'erreur EOF
                            while True:
                                try:
                                    chunk = gz_file.read(8192)
                                    if not chunk:
                                        break
                                    xml_file.write(chunk)
                                except EOFError:
                                    self.logger.warning("EOF atteint, fichier partiellement récupéré")
                                    break
                    
                    # Vérifier si on a pu récupérer quelque chose
                    if os.path.exists(xml_filepath) and os.path.getsize(xml_filepath) > 1000:
                        self.logger.info(f"Fichier partiellement récupéré: {xml_filename}")
                    else:
                        self.logger.error("Impossible de récupérer le fichier, données insuffisantes")
                        if os.path.exists(xml_filepath):
                            os.remove(xml_filepath)
                        os.remove(gz_filepath)
                        return None
                except Exception as recovery_error:
                    self.logger.error(f"Échec de la récupération: {recovery_error}")
                    if os.path.exists(xml_filepath):
                        os.remove(xml_filepath)
                    os.remove(gz_filepath)
                    return None
            
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
        Parse le fichier XML METAR et convertit en liste de documents JSON.
        
        Args:
            xml_filepath: Chemin vers le fichier XML à parser
            
        Returns:
            List[Dict]: Liste des documents METAR convertis en JSON
        """
        try:
            self.logger.info(f"Lecture du fichier METAR XML: {os.path.basename(xml_filepath)}")
            
            # Lire et parser le fichier XML avec xmltodict
            with open(xml_filepath, 'r', encoding='utf-8-sig') as xml_file:
                xml_content = xml_file.read()
            
            # Convertir XML en dictionnaire Python
            data = xmltodict.parse(xml_content)
            self.logger.info("XML parsé avec xmltodict")
            
            documents = []
            
            # Naviguer dans la structure du dictionnaire
            response = data.get('response', {})
            
            # Les METAR peuvent être dans data.data ou directement dans data
            metar_data = response.get('data', {})
            metars = metar_data.get('METAR', [])
            
            # Si METAR n'est pas une liste, en faire une
            if not isinstance(metars, list):
                metars = [metars] if metars else []
            
            self.logger.info(f"{len(metars)} éléments METAR trouvés")
            
            for metar in metars:
                if not metar:  # Skip empty METAR
                    continue
                    
                # Aplatir la structure du METAR (extraire attributs et valeurs)
                doc = self._flatten_dict(metar)
                
                # Convertir les valeurs numériques
                self._convert_numeric_fields(doc)
                
                # Créer un ID unique basé sur station_id et observation_time
                station_id = doc.get('@station_id') or doc.get('station_id')
                observation_time = doc.get('@observation_time') or doc.get('observation_time')
                
                if station_id and observation_time:
                    doc["_id"] = f"{station_id}_{observation_time}"
                else:
                    doc["_id"] = f"metar_{len(documents)}"
                
                # Ajouter des métadonnées
                doc["_metadata"] = {
                    "source": "aviationweather.gov",
                    "data_type": "METAR",
                    "file_downloaded_at": datetime.now(),
                    "xml_file": os.path.basename(xml_filepath),
                    "total_fields": len(doc)
                }
                
                documents.append(doc)
            
            self.logger.info(f"{len(documents)} documents METAR créés")
            
            # Afficher quelques infos sur les documents si disponibles
            if documents:
                example_doc = documents[0]
                station_id = example_doc.get('@station_id') or example_doc.get('station_id')
                observation_time = example_doc.get('@observation_time') or example_doc.get('observation_time')
                temp_c = example_doc.get('@temp_c') or example_doc.get('temp_c')
                wind_dir = example_doc.get('@wind_dir_degrees') or example_doc.get('wind_dir_degrees')
                wind_speed = example_doc.get('@wind_speed_kt') or example_doc.get('wind_speed_kt')
                
                self.logger.info(f"Exemple - Station: {station_id}, Observation: {observation_time}")
                self.logger.info(f"Temp: {temp_c}°C, Vent: {wind_dir}° à {wind_speed}kt")
                self.logger.info(f"Clés par document: {len(example_doc)}")
            
            return documents
            
        except Exception as e:
            self.logger.error(f"Erreur lors du parsing XML METAR: {e}")
            traceback.print_exc()
            return []
    
    def fetch_metar_data(self) -> List[Dict]:
        """
        Méthode principale qui télécharge le fichier XML et le convertit en JSON.
        
        Returns:
            List[Dict]: Liste des documents METAR en format JSON
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
                    self.logger.info(f"Ancien fichier METAR supprimé: {file_to_delete}")
            
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
    collector = MetarCollector()
    logger = get_logger(__name__)
    
    # Récupérer les données METAR
    logger.info("Démarrage de la collecte METAR XML...")
    metar_documents = collector.fetch_metar_data()
    
    if metar_documents:
        logger.info(f"{len(metar_documents)} documents METAR récupérés")
        
        # Afficher quelques exemples
        for i, doc in enumerate(metar_documents[:3]):
            station_id = doc.get('@station_id') or doc.get('station_id', 'N/A')
            temp_c = doc.get('@temp_c') or doc.get('temp_c', 'N/A')
            logger.info(f"Exemple {i+1}: Station {station_id}, Température: {temp_c}°C")
    else:
        logger.error("Aucune donnée METAR récupérée")
    
    # Nettoyer les anciens fichiers
    collector.cleanup_old_files()
