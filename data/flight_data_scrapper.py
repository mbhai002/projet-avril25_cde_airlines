import sys
import os
# Ajouter le répertoire parent au path pour pouvoir importer utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import urllib3
import time
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import pandas as pd
import pytz
from utils.flight_html_parser import ParserHtml
from utils.ftp_manager import FTPManager
from config.simple_logger import get_logger

# Désactiver les warnings SSL pour ce scraper spécifique
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class FlightDataScraper:
    """
    Scraper pour récupérer les données de vols depuis airportinfo.live
    """

    def __init__(self, lang: str = "en", use_cache_server: bool = False, cache_server_url: str = None):
        """
        Initialise le scraper avec la langue spécifiée
        
        Args:
            lang: Langue pour les requêtes (défaut: "en")
            use_cache_server: Si True, utilise le serveur cache au lieu d'airportinfo.live
            cache_server_url: URL du serveur cache (optionnel)
        """
        self.logger = get_logger(__name__)
        self.use_cache_server = use_cache_server
        
        if use_cache_server:
            self.base_url = cache_server_url
            self.logger.info(f"Initialisation du scraper avec serveur cache: {self.base_url}")
        else:
            self.base_url = "https://data.airportinfo.live/airportic.php"
            self.logger.info(f"Initialisation du scraper (langue: {lang})")
        
        self.lang = lang
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        self.parser = ParserHtml()

    def _handle_rate_limit(self, attempt: int, max_retries: int) -> bool:
        """
        Gère le rate limiting avec backoff exponentiel
        
        Args:
            attempt: Numéro de la tentative actuelle (0-indexé)
            max_retries: Nombre maximum de tentatives
            
        Returns:
            True si on doit continuer à essayer, False sinon
        """
        if attempt >= max_retries - 1:
            return False
            
        wait_time = (2 ** attempt) * 5  # Backoff exponentiel: 5s, 10s, 20s
        self.logger.warning(f"Rate limit atteint. Attente de {wait_time}s (tentative {attempt + 1}/{max_retries})")
        time.sleep(wait_time)
        return True

    def fetch(self, iata_airport: str, date: str, dep_arr: str = "arrival", 
              shift: str = "00", max_retries: int = 3, ftp_config: Optional[Dict] = None) -> List[Dict]:
        """
        Récupère les données de vol pour un aéroport, une date et une heure donnés
        
        Args:
            iata_airport: Code IATA de l'aéroport
            date: Date au format YYYY-MM-DD
            dep_arr: Type de vol ("arrival" ou "departure")
            shift: Heure au format HH (00-23)
            max_retries: Nombre maximum de tentatives
            ftp_config: Configuration FTP pour envoyer la réponse brute
            
        Returns:
            Liste des vols trouvés, liste vide en cas d'erreur
        """
        self.logger.info(f"Requête {dep_arr} pour {iata_airport} - shift {shift}...")
        
        payload = {
            "lang": self.lang,
            "iataAirport": iata_airport,
            "depArr": dep_arr,
            "date": date,
            "shift": str(shift),
            "exec": "1",
            "type": "refresh"
        }

        for attempt in range(max_retries):
            try:
                response = requests.post(self.base_url, headers=self.headers, data=payload, timeout=30, verify=False)
                
                if response.status_code == 429:  # Too Many Requests
                    if not self._handle_rate_limit(attempt, max_retries):
                        break
                    continue
                
                response.raise_for_status()
                self.logger.info(f"✓ Succès requête {iata_airport} shift {shift} ({dep_arr})")
                
                # Upload de la réponse brute vers FTP si configuré
                if ftp_config:
                    self._upload_raw_response_to_ftp(response, iata_airport, date, shift, dep_arr, ftp_config)
                
                flights = self.parser.parse_flights_html(
                    response.text, 
                    date=date, 
                    iata_airport=iata_airport, 
                    dep_arr=dep_arr
                )
                
                return flights if isinstance(flights, list) else []
                
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:
                    if not self._handle_rate_limit(attempt, max_retries):
                        break
                    continue
                else:
                    self.logger.error(f"HTTP {response.status_code} pour {iata_airport} shift {shift}: {e}")
                    
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Requête pour {iata_airport} shift {shift}: {e}")
                
            except Exception as e:
                self.logger.error(f"Inattendue pour {iata_airport} shift {shift}: {e}")
            
            # Attendre avant de réessayer (sauf pour la dernière tentative)
            if attempt < max_retries - 1:
                time.sleep(2)
        
        self.logger.error(f"Échec après {max_retries} tentatives pour {iata_airport} shift {shift}")
        return []

    def save_to_json(self, data: List[Dict], filename: str, output_folder: str = "output") -> bool:
        """
        Sauvegarde les données dans un fichier JSON dans le dossier spécifié
        
        Args:
            data: Données à sauvegarder
            filename: Nom du fichier
            output_folder: Dossier de destination
            
        Returns:
            True si la sauvegarde a réussi, False sinon
        """
        try:
            # Créer le chemin vers le dossier de sortie
            output_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                output_folder
            )
            
            # Créer le dossier s'il n'existe pas
            os.makedirs(output_dir, exist_ok=True)
            
            # Chemin complet du fichier
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✓ Données sauvegardées dans {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Impossible de sauvegarder dans {filename} : {e}")
            return False

    def _upload_raw_response_to_ftp(self, response, iata_airport: str, date: str, 
                                    shift: str, dep_arr: str, ftp_config: Dict) -> None:
        """Upload la réponse HTTP brute vers un serveur FTP et nettoie les vieux fichiers"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"raw_{iata_airport}_{dep_arr}_{date}_{shift}h_{timestamp}.html"
            
            self.logger.info(f"Upload FTP de la réponse brute: {filename}")
            
            with FTPManager(
                host=ftp_config.get('host'),
                port=ftp_config.get('port', 21),
                username=ftp_config.get('username', ''),
                password=ftp_config.get('password', ''),
                use_tls=ftp_config.get('use_tls', False),
                remote_directory=ftp_config.get('remote_directory', '/')
            ) as ftp:
                if ftp.ftp:
                    from io import BytesIO
                    content_bytes = response.content
                    file_obj = BytesIO(content_bytes)
                    
                    # Upload du nouveau fichier
                    ftp.ftp.storbinary(f'STOR {filename}', file_obj)
                    self.logger.info(f"✓ Upload FTP réussi: {filename} ({len(content_bytes)} octets)")
                    
                    # Nettoyage des vieux fichiers (max 24h)
                    max_age_hours = ftp_config.get('cleanup_max_age_hours', 24)
                    if max_age_hours > 0:
                        deleted = ftp.cleanup_old_files(pattern="raw_*.html", max_age_hours=max_age_hours)
                        if deleted > 0:
                            self.logger.info(f"🗑️  Nettoyage FTP: {deleted} fichier(s) supprimé(s)")
                else:
                    self.logger.error("✗ Impossible de se connecter au serveur FTP")
                    
        except Exception as e:
            self.logger.error(f"Erreur lors de l'upload FTP de la réponse brute: {e}")


    def fetch_next_hour_departures_top_airports(self, num_airports: int = 200, 
                                               delay: float = 2.0, 
                                               hour_offset: int = 1,
                                               ftp_config: Optional[Dict] = None) -> List[Dict]:
        """
        Récupère les départs pour une heure spécifique pour les N premiers aéroports
        en tenant compte du timezone de chaque aéroport
        
        Args:
            num_airports: Nombre d'aéroports à traiter (défaut: 200)
            delay: Délai entre les requêtes pour éviter le rate limiting
            hour_offset: Décalage en heures par rapport à l'heure actuelle
                        Exemples: 1 = prochaine heure, 0 = heure actuelle, -1 = heure précédente
            ftp_config: Configuration FTP pour l'upload automatique des réponses brutes
                       Format: {
                           'host': 'ftp.example.com',
                           'port': 21,
                           'username': 'user',
                           'password': 'pass',
                           'use_tls': False,
                           'remote_directory': '/uploads'
                       }
        
        Returns:
            Liste de tous les vols de départ pour l'heure ciblée
        """
        offset_desc = self._get_offset_description(hour_offset)
        self.logger.info(f"Récupération des départs pour {offset_desc} pour les {num_airports} premiers aéroports")
        
        # Charger les données des aéroports
        airports_df = self._load_airports_data()
        if airports_df is None:
            return []
        
        # Prendre les N premiers aéroports
        top_airports = airports_df.head(num_airports)
        self.logger.info(f"{len(top_airports)} aéroports chargés depuis le fichier CSV")
        
        all_flights = []
        utc_now = datetime.now(timezone.utc)
        
        for index, airport in top_airports.iterrows():
            iata_code = airport['code_iata']
            timezone_name = airport['timezone']
            
            # Log de progression
            self.logger.info(f"[{index + 1}/{num_airports}] Traitement de l'aéroport {iata_code}...")
            
            try:
                flights = self._fetch_airport_flights(
                    iata_code, timezone_name, utc_now, hour_offset, index, num_airports, ftp_config
                )
                
                if flights:
                    all_flights.extend(flights)
                    self.logger.info(f"✓ {iata_code}: {len(flights)} vols de départ trouvés")
                else:
                    self.logger.info(f"⚠ {iata_code}: Aucun vol de départ trouvé")
                    
            except Exception as e:
                self.logger.error(f"✗ {iata_code}: {e}")
            
            # Délai entre les requêtes (seulement si on utilise airportinfo.live)
            if index < len(top_airports) - 1 and not self.use_cache_server:
                time.sleep(delay)
        
        self.logger.info(f"Total de {len(all_flights)} vols de départ récupérés pour l'heure cible")
        
        return all_flights

    def _get_offset_description(self, hour_offset: int) -> str:
        """Retourne une description lisible du décalage horaire"""
        if hour_offset == 1:
            return "prochaine heure"
        elif hour_offset == 0:
            return "heure actuelle"
        elif hour_offset == -1:
            return "heure précédente"
        else:
            sign = '+' if hour_offset > 0 else ''
            return f"heure actuelle{sign}{hour_offset}"

    def _load_airports_data(self) -> Optional[pd.DataFrame]:
        """Charge les données des aéroports depuis le fichier CSV"""
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "utils", 
            "airports_ref.csv"
        )
        
        if not os.path.exists(csv_path):
            self.logger.error(f"Fichier {csv_path} non trouvé")
            return None
        
        try:
            return pd.read_csv(csv_path, sep=';', encoding='utf-8')
        except Exception as e:
            self.logger.error(f"Impossible de lire le fichier CSV: {e}")
            return None

    def _fetch_airport_flights(self, iata_code: str, timezone_name: str, 
                             utc_now: datetime, hour_offset: int, 
                             index: int, total: int, ftp_config: Optional[Dict] = None) -> List[Dict]:
        """Récupère les vols pour un aéroport spécifique"""
        try:
            # Obtenir le timezone de l'aéroport
            airport_tz = pytz.timezone(timezone_name)
            
            # Convertir l'heure UTC actuelle vers l'heure locale de l'aéroport
            local_time = utc_now.astimezone(airport_tz)
            
            # Calculer l'heure cible avec le décalage spécifié
            target_hour = local_time.replace(
                minute=0, second=0, microsecond=0
            ) + timedelta(hours=hour_offset)
            
            # Formater la date et l'heure pour la requête
            date_str = target_hour.strftime("%Y-%m-%d")
            shift = target_hour.strftime("%H")
            
            self.logger.debug(f"{index + 1}/{total} - {iata_code} | "
                  f"Heure locale: {local_time.strftime('%H:%M')} | "
                  f"Heure cible: {shift}h | Date: {date_str} | "
                  f"Offset: {hour_offset:+d}h")
            
            # Faire la requête pour cette heure spécifique
            flights = self.fetch(
                iata_airport=iata_code,
                date=date_str,
                dep_arr="departure",
                shift=shift,
                ftp_config=ftp_config
            )
            
            # Ajouter des métadonnées sur l'aéroport
            if flights:
                for flight in flights:
                    flight['airport_timezone'] = timezone_name
                    flight['local_time'] = target_hour.strftime("%Y-%m-%d %H:%M:%S")
                    flight['utc_offset'] = str(target_hour.utcoffset())
            
            return flights
            
        except Exception as e:
            self.logger.error(f"Erreur pour l'aéroport {iata_code}: {e}")
            return []


def main():
    """Fonction principale d'exécution du scraper"""
    logger = get_logger(__name__)
    logger.info("Lancement du scraper...")
    scraper = FlightDataScraper()

    # Option pour récupérer les départs avec différents décalages horaires
    # Exemples d'utilisation :
    # next_hour_flights = scraper.fetch_next_hour_departures_top_airports(num_airports=10, delay=1.0, hour_offset=1)   # Prochaine heure (défaut)
    # current_hour_flights = scraper.fetch_next_hour_departures_top_airports(num_airports=10, delay=1.0, hour_offset=0)  # Heure actuelle
    # previous_hour_flights = scraper.fetch_next_hour_departures_top_airports(num_airports=10, delay=1.0, hour_offset=-1) # Heure précédente
    # future_flights = scraper.fetch_next_hour_departures_top_airports(num_airports=10, delay=1.0, hour_offset=3)       # Dans 3 heures

    next_hour_flights = scraper.fetch_next_hour_departures_top_airports(
        num_airports=5, 
        delay=1.5, 
        hour_offset=-24
    )
    logger.info(f"{len(next_hour_flights)} vols de départ récupérés")


if __name__ == "__main__":
    main()



