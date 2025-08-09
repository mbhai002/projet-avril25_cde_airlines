import sys
import os
# Ajouter le répertoire parent au path pour pouvoir importer utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import time
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import pandas as pd
import pytz
from data.utils.flight_html_parser import ParserHtml


class FlightDataScraper:
    """
    Scraper pour récupérer les données de vols depuis airportinfo.live
    """

    def __init__(self, lang: str = "en"):
        """
        Initialise le scraper avec la langue spécifiée
        
        Args:
            lang: Langue pour les requêtes (défaut: "en")
        """
        print(f"[LOG] Initialisation du scraper (langue: {lang})")
        self.base_url = "https://data.airportinfo.live/airportic.php"
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
        print(f"[WARNING] Rate limit atteint. Attente de {wait_time}s (tentative {attempt + 1}/{max_retries})")
        time.sleep(wait_time)
        return True

    def fetch(self, iata_airport: str, date: str, dep_arr: str = "arrival", 
              shift: str = "00", max_retries: int = 3) -> List[Dict]:
        """
        Récupère les données de vol pour un aéroport, une date et une heure donnés
        
        Args:
            iata_airport: Code IATA de l'aéroport
            date: Date au format YYYY-MM-DD
            dep_arr: Type de vol ("arrival" ou "departure")
            shift: Heure au format HH (00-23)
            max_retries: Nombre maximum de tentatives
            
        Returns:
            Liste des vols trouvés, liste vide en cas d'erreur
        """
        print(f"[LOG] Requête {dep_arr} pour {iata_airport} - shift {shift}...")
        
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
                response = requests.post(self.base_url, headers=self.headers, data=payload, timeout=30)
                
                if response.status_code == 429:  # Too Many Requests
                    if not self._handle_rate_limit(attempt, max_retries):
                        break
                    continue
                
                response.raise_for_status()
                print(f"[LOG] ✓ Succès requête {iata_airport} shift {shift} ({dep_arr})")
                
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
                    print(f"[ERREUR] HTTP {response.status_code} pour {iata_airport} shift {shift}: {e}")
                    
            except requests.exceptions.RequestException as e:
                print(f"[ERREUR] Requête pour {iata_airport} shift {shift}: {e}")
                
            except Exception as e:
                print(f"[ERREUR] Inattendue pour {iata_airport} shift {shift}: {e}")
            
            # Attendre avant de réessayer (sauf pour la dernière tentative)
            if attempt < max_retries - 1:
                time.sleep(2)
        
        print(f"[ERREUR] Échec après {max_retries} tentatives pour {iata_airport} shift {shift}")
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
            
            print(f"[LOG] ✓ Données sauvegardées dans {filepath}")
            return True
            
        except Exception as e:
            print(f"[ERREUR] Impossible de sauvegarder dans {filename} : {e}")
            return False

    def fetch_next_hour_departures_top_airports(self, num_airports: int = 200, 
                                               delay: float = 2.0, 
                                               hour_offset: int = 1,
                                               auto_save: bool = True) -> List[Dict]:
        """
        Récupère les départs pour une heure spécifique pour les N premiers aéroports
        en tenant compte du timezone de chaque aéroport
        
        Args:
            num_airports: Nombre d'aéroports à traiter (défaut: 200)
            delay: Délai entre les requêtes pour éviter le rate limiting
            hour_offset: Décalage en heures par rapport à l'heure actuelle
                        Exemples: 1 = prochaine heure, 0 = heure actuelle, -1 = heure précédente
            auto_save: Si True, sauvegarde automatiquement en JSON (défaut: True)
        
        Returns:
            Liste de tous les vols de départ pour l'heure ciblée
        """
        offset_desc = self._get_offset_description(hour_offset)
        print(f"[LOG] Récupération des départs pour {offset_desc} pour les {num_airports} premiers aéroports")
        
        # Charger les données des aéroports
        airports_df = self._load_airports_data()
        if airports_df is None:
            return []
        
        # Prendre les N premiers aéroports
        top_airports = airports_df.head(num_airports)
        print(f"[LOG] {len(top_airports)} aéroports chargés depuis le fichier CSV")
        
        all_flights = []
        utc_now = datetime.now(timezone.utc)
        
        for index, airport in top_airports.iterrows():
            iata_code = airport['code_iata']
            timezone_name = airport['timezone']
            
            try:
                flights = self._fetch_airport_flights(
                    iata_code, timezone_name, utc_now, hour_offset, index, num_airports
                )
                
                if flights:
                    all_flights.extend(flights)
                    print(f"[LOG] ✓ {iata_code}: {len(flights)} vols de départ trouvés")
                else:
                    print(f"[LOG] ⚠ {iata_code}: Aucun vol de départ trouvé")
                    
            except Exception as e:
                print(f"[ERREUR] ✗ {iata_code}: {e}")
            
            # Délai entre les requêtes (sauf pour le dernier)
            if index < len(top_airports) - 1:
                time.sleep(delay)
        
        print(f"[LOG] Total de {len(all_flights)} vols de départ récupérés pour l'heure cible")
        
        # Sauvegarde automatique (optionnelle)
        if auto_save and all_flights:
            self._save_flight_data(all_flights, num_airports, hour_offset)
        elif auto_save:
            print(f"[LOG] Aucun vol trouvé, pas de sauvegarde effectuée")
        else:
            print(f"[LOG] Sauvegarde automatique désactivée")
        
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
            "data/utils", 
            "airports_ref.csv"
        )
        
        if not os.path.exists(csv_path):
            print(f"[ERREUR] Fichier {csv_path} non trouvé")
            return None
        
        try:
            return pd.read_csv(csv_path, sep=';', encoding='utf-8')
        except Exception as e:
            print(f"[ERREUR] Impossible de lire le fichier CSV: {e}")
            return None

    def _fetch_airport_flights(self, iata_code: str, timezone_name: str, 
                             utc_now: datetime, hour_offset: int, 
                             index: int, total: int) -> List[Dict]:
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
            
            print(f"[LOG] {index + 1}/{total} - {iata_code} | "
                  f"Heure locale: {local_time.strftime('%H:%M')} | "
                  f"Heure cible: {shift}h | Date: {date_str} | "
                  f"Offset: {hour_offset:+d}h")
            
            # Faire la requête pour cette heure spécifique
            flights = self.fetch(
                iata_airport=iata_code,
                date=date_str,
                dep_arr="departure",
                shift=shift
            )
            
            # Ajouter des métadonnées sur l'aéroport
            if flights:
                for flight in flights:
                    flight['airport_timezone'] = timezone_name
                    flight['local_time'] = target_hour.strftime("%Y-%m-%d %H:%M:%S")
                    flight['utc_offset'] = str(target_hour.utcoffset())
            
            return flights
            
        except Exception as e:
            print(f"[ERREUR] Erreur pour l'aéroport {iata_code}: {e}")
            return []

    def _save_flight_data(self, flights: List[Dict], num_airports: int, hour_offset: int) -> None:
        """Sauvegarde automatique des données de vol"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        offset_suffix = f"_offset{hour_offset:+d}" if hour_offset != 1 else ""
        filename = f"departures_top{num_airports}{offset_suffix}_{timestamp}.json"
        self.save_to_json(flights, filename)


def main():
    """Fonction principale d'exécution du scraper"""
    print("[LOG] Lancement du scraper...")
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
        hour_offset=-24,
        auto_save=True  # Optionnel: définir à False pour désactiver la sauvegarde automatique
    )
    print(f"[LOG] {len(next_hour_flights)} vols de départ récupérés")


if __name__ == "__main__":
    main()



