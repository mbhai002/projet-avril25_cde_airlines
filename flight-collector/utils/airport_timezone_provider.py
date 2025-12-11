import csv
import os
import sys
from typing import Dict, Optional

# Ajouter le chemin parent pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.simple_logger import get_logger


class AirportTimezoneProvider:
    """
    Classe pour récupérer les timezones des aéroports à partir de leur code IATA
    basée sur le fichier airports_ref.csv
    """
    
    def __init__(self, csv_file_path: str = None):
        """
        Initialise le convertisseur avec le fichier CSV
        
        Args:
            csv_file_path (str): Chemin vers le fichier airports.csv
                                Si None, utilise le chemin par défaut
        """
        if csv_file_path is None:
            # Chemin par défaut relatif au fichier actuel
            current_dir = os.path.dirname(os.path.abspath(__file__))
            csv_file_path = os.path.join(current_dir, 'airports_ref.csv')
        
        self.csv_file_path = csv_file_path
        self.airport_info: Dict[str, Dict] = {}
        self.logger = get_logger(__name__)
        
        self._load_data()
    
    def _load_data(self):
        """Charge les données depuis le fichier CSV"""
        try:
            with open(self.csv_file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file, delimiter=';')
                
                for row in csv_reader:
                    iata = row.get('code_iata', '').strip()
                    timezone = row.get('timezone', '').strip()
                    
                    # Ignorer les lignes sans code IATA
                    if not iata:
                        continue
                    
                    # Stocker seulement les infos nécessaires
                    self.airport_info[iata] = {
                        'time_zone': timezone
                    }
            
            self.logger.info(f"AirportTimezoneProvider initialisé avec {len(self.airport_info)} aéroports")
            
        except FileNotFoundError:
            self.logger.error(f"Fichier CSV non trouvé: {self.csv_file_path}")
            # Fallback avec quelques timezones de base
            self._load_fallback_data()
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement du CSV: {e}")
            self._load_fallback_data()
    
    def _load_fallback_data(self):
        """Charge des données de base en cas d'erreur avec le fichier CSV"""
        self.airport_info = {
            'CDG': {'time_zone': 'Europe/Paris'},
            'ORY': {'time_zone': 'Europe/Paris'},
            'LHR': {'time_zone': 'Europe/London'},
            'JFK': {'time_zone': 'America/New_York'},
            'LAX': {'time_zone': 'America/Los_Angeles'},
            'NRT': {'time_zone': 'Asia/Tokyo'},
            'DXB': {'time_zone': 'Asia/Dubai'},
            'SIN': {'time_zone': 'Asia/Singapore'},
            'FRA': {'time_zone': 'Europe/Berlin'},
            'AMS': {'time_zone': 'Europe/Amsterdam'},
        }
        self.logger.info(f"Utilisation des données de fallback avec {len(self.airport_info)} aéroports")
    
    def get_airport_info(self, iata_code: str) -> Optional[Dict]:
        """
        Récupère toutes les informations d'un aéroport par son code IATA
        
        Args:
            iata_code (str): Code IATA
            
        Returns:
            Optional[Dict]: Dictionnaire avec toutes les infos ou None
        """
        return self.airport_info.get(iata_code.upper())
    
    def get_timezone_from_iata(self, iata_code: str) -> Optional[str]:
        """
        Retourne la timezone d'un aéroport à partir de son code IATA
        
        Args:
            iata_code (str): Code IATA de l'aéroport (ex: 'CDG')
            
        Returns:
            Optional[str]: Timezone de l'aéroport ou None si non trouvé
        """
        airport_info = self.get_airport_info(iata_code)
        if airport_info and airport_info.get('time_zone'):
            return airport_info['time_zone']
        return None

