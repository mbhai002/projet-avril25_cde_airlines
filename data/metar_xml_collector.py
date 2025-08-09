import os
import gzip
import requests
import xmltodict
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


class MetarXmlCollector:
    """
    Classe pour récupérer les données METAR au format XML depuis aviationweather.gov
    et les convertir en documents JSON.
    """
    
    METAR_XML_URL = "https://aviationweather.gov/data/cache/metars.cache.xml.gz"
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialise le collecteur METAR XML.
        
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
        
    def download_xml_file(self) -> Optional[str]:
        """
        Télécharge le fichier METAR XML compressé depuis aviationweather.gov.
        
        Returns:
            str: Chemin vers le fichier XML décompressé, ou None en cas d'erreur
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            gz_filename = f"metars_{timestamp}.xml.gz"
            xml_filename = f"metars_{timestamp}.xml"
            
            gz_filepath = os.path.join(self.data_dir, gz_filename)
            xml_filepath = os.path.join(self.data_dir, xml_filename)
            
            print(f"[INFO] Téléchargement depuis {self.METAR_XML_URL}")
            
            # Télécharger le fichier
            response = requests.get(self.METAR_XML_URL, stream=True, timeout=30)
            response.raise_for_status()
            
            # Sauvegarder le fichier compressé
            with open(gz_filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"[SUCCESS] Fichier téléchargé: {gz_filename}")
            
            # Décompresser le fichier
            with gzip.open(gz_filepath, 'rt', encoding='utf-8') as gz_file:
                with open(xml_filepath, 'w', encoding='utf-8') as xml_file:
                    xml_file.write(gz_file.read())
            
            print(f"[SUCCESS] Fichier décompressé: {xml_filename}")
            
            # Supprimer le fichier compressé pour économiser l'espace
            os.remove(gz_filepath)
            
            return xml_filepath
            
        except Exception as e:
            print(f"[ERREUR] Erreur lors du téléchargement: {e}")
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
    
    def parse_xml_to_json(self, xml_filepath: str) -> List[Dict]:
        """
        Parse le fichier XML METAR et convertit en liste de documents JSON.
        
        Args:
            xml_filepath: Chemin vers le fichier XML à parser
            
        Returns:
            List[Dict]: Liste des documents METAR convertis en JSON
        """
        try:
            print(f"[INFO] Lecture du fichier METAR XML: {os.path.basename(xml_filepath)}")
            
            # Lire et parser le fichier XML avec xmltodict
            with open(xml_filepath, 'r', encoding='utf-8') as xml_file:
                xml_content = xml_file.read()
            
            # Convertir XML en dictionnaire Python
            data = xmltodict.parse(xml_content)
            print(f"[INFO] XML parsé avec xmltodict")
            
            documents = []
            
            # Naviguer dans la structure du dictionnaire
            response = data.get('response', {})
            
            # Les METAR peuvent être dans data.data ou directement dans data
            metar_data = response.get('data', {})
            metars = metar_data.get('METAR', [])
            
            # Si METAR n'est pas une liste, en faire une
            if not isinstance(metars, list):
                metars = [metars] if metars else []
            
            print(f"[INFO] {len(metars)} éléments METAR trouvés")
            
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
                doc.update({
                    "_metadata_source": "aviationweather.gov",
                    "_metadata_data_type": "METAR",
                    "_metadata_file_downloaded_at": datetime.now(),
                    "_metadata_xml_file": os.path.basename(xml_filepath),
                    "_metadata_total_fields": len(doc)
                })
                
                documents.append(doc)
            
            print(f"[SUCCESS] {len(documents)} documents METAR créés")
            
            # Afficher quelques infos sur les documents si disponibles
            if documents:
                example_doc = documents[0]
                station_id = example_doc.get('@station_id') or example_doc.get('station_id')
                observation_time = example_doc.get('@observation_time') or example_doc.get('observation_time')
                temp_c = example_doc.get('@temp_c') or example_doc.get('temp_c')
                wind_dir = example_doc.get('@wind_dir_degrees') or example_doc.get('wind_dir_degrees')
                wind_speed = example_doc.get('@wind_speed_kt') or example_doc.get('wind_speed_kt')
                
                print(f"[INFO] Exemple - Station: {station_id}, Observation: {observation_time}")
                print(f"[INFO] Temp: {temp_c}°C, Vent: {wind_dir}° à {wind_speed}kt")
                print(f"[INFO] Clés par document: {len(example_doc)}")
            
            return documents
            
        except Exception as e:
            print(f"[ERREUR] Erreur lors du parsing XML METAR: {e}")
            traceback.print_exc()
            return []
    
    def fetch_metar_data(self) -> List[Dict]:
        """
        Méthode principale qui télécharge le fichier XML et le convertit en JSON.
        
        Returns:
            List[Dict]: Liste des documents METAR en format JSON
        """
        # 1. Télécharger le fichier XML
        xml_filepath = self.download_xml_file()
        if not xml_filepath:
            print("[ERREUR] Impossible de télécharger le fichier XML")
            return []
        
        # 2. Parser le XML en JSON
        documents = self.parse_xml_to_json(xml_filepath)
        
        # 3. Nettoyer le fichier temporaire (optionnel)
        try:
            os.remove(xml_filepath)
            print(f"[INFO] Fichier temporaire supprimé: {os.path.basename(xml_filepath)}")
        except Exception as e:
            print(f"[WARNING] Impossible de supprimer le fichier temporaire: {e}")
        
        return documents
    
    def cleanup_old_files(self, keep_count: int = 5) -> None:
        """
        Nettoie les anciens fichiers XML pour économiser l'espace disque.
        
        Args:
            keep_count: Nombre de fichiers à conserver (par défaut 5)
        """
        try:
            xml_files = [f for f in os.listdir(self.data_dir) if f.endswith('.xml')]
            xml_files.sort()
            
            if len(xml_files) > keep_count:
                files_to_delete = xml_files[:-keep_count]
                for file_to_delete in files_to_delete:
                    file_path = os.path.join(self.data_dir, file_to_delete)
                    os.remove(file_path)
                    print(f"[INFO] Ancien fichier METAR supprimé: {file_to_delete}")
                    
        except Exception as e:
            print(f"[WARNING] Erreur lors du nettoyage: {e}")


# Exemple d'utilisation
if __name__ == "__main__":
    # Créer une instance du collecteur
    collector = MetarXmlCollector()
    
    # Récupérer les données METAR
    print("[INFO] Démarrage de la collecte METAR XML...")
    metar_documents = collector.fetch_metar_data()
    
    if metar_documents:
        print(f"[SUCCESS] {len(metar_documents)} documents METAR récupérés")
        
        # Afficher quelques exemples
        for i, doc in enumerate(metar_documents[:3]):
            station_id = doc.get('@station_id') or doc.get('station_id', 'N/A')
            temp_c = doc.get('@temp_c') or doc.get('temp_c', 'N/A')
            print(f"Exemple {i+1}: Station {station_id}, Température: {temp_c}°C")
    else:
        print("[ERREUR] Aucune donnée METAR récupérée")
    
    # Nettoyer les anciens fichiers
    collector.cleanup_old_files()
