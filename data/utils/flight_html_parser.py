from bs4 import BeautifulSoup
import re
from datetime import datetime
from typing import Optional
import pytz
from .airport_timezone_provider import AirportTimezoneProvider


class ParserHtml:
    """
    Classe dédiée au parsing du HTML pour extraire les données de vols
    depuis les pages web d'airportinfo.live
    """
    
    def __init__(self):
        """Initialise le parser HTML"""
        print("[LOG] Initialisation du parser HTML")
        # Initialiser le provider de timezone pour récupérer les timezones
        self.timezone_provider = AirportTimezoneProvider()
    
    def parse_flights_html(self, html_content: str, date: str, iata_airport: str, dep_arr: str) -> list:
        """Parse le HTML pour extraire les données des vols en format JSON"""
        if not html_content:
            return []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            flights = []
            
            # Trouver le tableau des vols
            table = soup.find('table', class_='flightsTable')
            if not table:
                print("[LOG] Aucun tableau de vols trouvé dans le HTML")
                return []
            
            # Vérifier s'il y a un message "no flights"
            no_flights_span = soup.find('span', class_='noflights')
            if no_flights_span:
                print("[LOG] Aucun vol disponible pour cette période (message 'noflights' détecté)")
                return []
            
             # Extraire chaque ligne de vol et gérer les lignes compensation
            rows = table.find_all('tr')
            i = 0
            while i < len(rows):
                row = rows[i]
                
                # Ignorer les lignes d'en-tête
                if (row.find('th') or 'flightsTable-header' in row.get('class', [])):
                    i += 1
                    continue
                
                # Traiter les lignes de compensation séparément
                if 'compensation-row' in row.get('class', []):
                    i += 1
                    continue
                
                # Extraire les données du vol
                flight_data = self._extract_flight_data(row, date=date, iata_airport=iata_airport, dep_arr=dep_arr)
                
                if flight_data:
                    # Vérifier si la ligne suivante est une ligne compensation pour ce vol
                    if i + 1 < len(rows):
                        next_row = rows[i + 1]
                        if 'compensation-row' in next_row.get('class', []):
                            operated_by = self._extract_operated_by(next_row)
                            if operated_by:
                                flight_data['operated_by'] = operated_by
                    
                    flights.append(flight_data)
                
                i += 1
            
            print(f"[LOG] {len(flights)} vols extraits du HTML")
            return flights
            
        except Exception as e:
            print(f"[ERREUR] Parsing HTML : {e}")
            return []
    
    def _extract_flight_data(self, row, date: str, iata_airport: str, dep_arr: str) -> dict:
        """Extrait les données d'un vol depuis une ligne TR"""
        try:
            cells = row.find_all('td')
            if len(cells) < 6:
                return None
            
            # Extraction des données de base
            flight_cell = cells[0]
            destination_origin_cell = cells[1]  # "TO" pour départs, "FROM" pour arrivées
            airline_cell = cells[2]
            departure_cell = cells[3]
            arrival_cell = cells[4]
            status_cell = cells[5]
            
            # Numéro de vol
            flight_link = flight_cell.find('a')
            flight_number = flight_link.text.strip() if flight_link else ""

            # Extraire la date de départ depuis l'URL du lien
            departure_date = None
            if flight_link:
                href = flight_link.get('href', '')
                # Chercher le pattern d=YYYY-MM-DD dans l'URL
                date_match = re.search(r'd=(\d{4}-\d{2}-\d{2})', href)
                departure_date = date_match.group(1) if date_match else date
            
            # Extraire la date d'arrivée depuis l'attribut data-arrivaltime
            arrival_date = None
            for button in status_cell.find_all('button'):
                arrival_time_attr = button.get('data-arrivaltime')
                if arrival_time_attr:
                    # Extraire seulement la date (YYYY-MM-DD) depuis YYYY-MM-DDTHH:MM:SS.sss
                    arrival_date_match = re.search(r'(\d{4}-\d{2}-\d{2})', arrival_time_attr)
                    arrival_date = arrival_date_match.group(1) if arrival_date_match else None
                    break
            
            # Aéroport de départ
            destination_origin_link = destination_origin_cell.find('a')
            airport_code = ""

            if destination_origin_link:
                text = destination_origin_link.text.strip()
                # Extraire le code entre crochets
                code_match = re.search(r'\[([A-Z]{3})\]', text)
                airport_code = code_match.group(1) if code_match else ""
                airport_name = text.replace(f'[{airport_code}]', '').strip()
            
            # Logique selon le type de requête
            if dep_arr == "departure":
                # Pour les départs : l'aéroport de la requête est l'origine
                from_code = iata_airport  # Code de l'aéroport de la requête
                to_code = airport_code  # Code de la destination
            else:  # arrival
                # Pour les arrivées : l'aéroport de la requête est la destination
                from_code = airport_code  # Code de l'origine
                to_code = iata_airport  # Code de l'aéroport de la requête
            
            # Compagnie aérienne
            airline_link = airline_cell.find('a')
            airline = airline_link.text.strip() if airline_link else airline_cell.text.strip()
            
            # Heures de départ - extraire toutes les heures présentes
            dep_times = self._extract_time_data(departure_cell)
            dep_gate = self._extract_gate_terminal(departure_cell)
            dep_delay = self._extract_delay_info_from_cell(departure_cell)
            
            # Heures d'arrivée - extraire toutes les heures présentes  
            arr_times = self._extract_time_data(arrival_cell)
            arr_gate = self._extract_gate_terminal(arrival_cell)
            arr_delay = self._extract_delay_info_from_cell(arrival_cell)
            
            # Statut
            status_span = status_cell.find('span')
            status = status_span.text.strip() if status_span else ""
            
            # Conversion des heures locales en UTC
            dep_scheduled_utc = self._convert_to_utc(departure_date, dep_times["scheduled"], from_code)
            dep_estimated_utc = self._convert_to_utc(departure_date, dep_times["estimated"], from_code)
            arr_scheduled_utc = self._convert_to_utc(arrival_date, arr_times["scheduled"], to_code)
            arr_estimated_utc = self._convert_to_utc(arrival_date, arr_times["estimated"], to_code)
            
            flight_data = {
                "flight_number": flight_number,
                "from_code": from_code,
                "to_code": to_code,
                "airline": airline,
                "departure": {
                    "date": departure_date,
                    "scheduled": dep_times["scheduled"],
                    "estimated": dep_times["estimated"],
                    "scheduled_utc": dep_scheduled_utc,
                    "estimated_utc": dep_estimated_utc,
                    "gate": dep_gate.get('gate', ''),
                    "terminal": dep_gate.get('terminal', ''),
                    "delay": dep_delay
                },
                "arrival": {
                    "date": arrival_date,
                    "scheduled": arr_times["scheduled"],
                    "estimated": arr_times["estimated"],
                    "scheduled_utc": arr_scheduled_utc,
                    "estimated_utc": arr_estimated_utc,
                    "gate": arr_gate.get('gate', ''),
                    "terminal": arr_gate.get('terminal', ''),
                    "delay": arr_delay 
                },
                "status": status,
                "airport_type": dep_arr  # Ajout pour savoir si c'est un départ ou une arrivée
            }
            
            return flight_data
            
        except Exception as e:
            print(f"[ERREUR] Extraction données vol : {e}")
            return None
    
    def _extract_times(self, cell):
        """Extrait toutes les heures d'une cellule et les retourne dans l'ordre"""
        times = []
        time_pattern = r'\d{1,2}:\d{2}'
        
        # Chercher dans tous les éléments de la cellule
        for element in cell.find_all():
            text = element.text.strip()
            if re.search(time_pattern, text):
                # Nettoyer le texte (enlever les dates entre crochets)
                cleaned_text = re.sub(r'\s*\[.*?\]', '', text)
                # Trouver toutes les heures dans cet élément
                time_matches = re.findall(time_pattern, cleaned_text)
                for time_match in time_matches:
                    if time_match not in times:  # Éviter les doublons
                        times.append(time_match)
        
        # Si aucun élément enfant ne contient d'heure, chercher directement dans le texte de la cellule
        if not times:
            cell_text = cell.text.strip()
            cleaned_text = re.sub(r'\s*\[.*?\]', '', cell_text)
            time_matches = re.findall(time_pattern, cleaned_text)
            times.extend(time_matches)
        
        return times
    
    def _extract_time_data(self, cell):
        """Extrait les données temporelles d'une cellule (heure prévue et estimée)"""
        times = self._extract_times(cell)
        
        if len(times) == 0:
            return {"scheduled": "", "estimated": ""}
        elif len(times) == 1:
            # Une seule heure = heure prévue (pas de changement)
            return {"scheduled": times[0], "estimated": times[0]}
        else:
            # Plusieurs heures = première heure barrée (prévue) + dernière heure (estimée)
            return {"scheduled": times[0], "estimated": times[-1]}
    
    def _extract_gate_terminal(self, cell):
        """Extrait les infos de porte et terminal"""
        result = {"gate": "", "terminal": ""}
        
        terminal_elem = cell.find(class_='terminal')
        if terminal_elem:
            result["terminal"] = terminal_elem.text.strip()
        
        gate_elem = cell.find(class_='gate')
        if gate_elem:
            result["gate"] = gate_elem.text.strip()
        
        return result
    
    def _extract_delay_info_from_cell(self, cell):
        """Extrait les informations de retard d'une cellule spécifique (départ ou arrivée)"""
        delay_info = {"is_delayed": False, "minutes": 0}
        
        # Chercher spécifiquement les spans avec les classes estimatedTime et arrDelayed/depDelayed
        delayed_spans = cell.find_all('span', class_=['estimatedTime arrDelayed', 'estimatedTime depDelayed'])
        
        for span in delayed_spans:
            data_delay = span.get('data-delay')
            if data_delay is not None:
                try:
                    delay_minutes = int(data_delay)
                    if delay_minutes > 0:
                        delay_info["is_delayed"] = True
                        delay_info["minutes"] = delay_minutes
                        return delay_info
                except (ValueError, TypeError):
                    continue
        
        return delay_info
    
    def _extract_operated_by(self, compensation_row):
        """
        Extrait l'information 'operated by' depuis une ligne de compensation
        
        Args:
            compensation_row: Element TR avec class="compensation-row"
            
        Returns:
            str: Code du vol opérateur (ex: "DE1500") ou None
        """
        try:
            # Vérifier que c'est bien une ligne de compensation
            if 'compensation-row' not in compensation_row.get('class', []):
                return None
            
            # Extraire le contenu de la cellule
            td = compensation_row.find('td')
            if not td:
                return None
            
            text = td.text.strip()
            
            # Chercher le pattern "operated by [CODE]"
            operated_by_match = re.search(r'operated by\s+([A-Z0-9]+)', text, re.IGNORECASE)
            if operated_by_match:
                return operated_by_match.group(1)
            
            # Alternative: extraire depuis l'attribut data-cs
            data_cs = compensation_row.get('data-cs')
            if data_cs:
                return data_cs
            
            return None
            
        except Exception as e:
            print(f"[ERREUR] Extraction operated_by : {e}")
            return None
    
    def _convert_to_utc(self, date_str: str, time_str: str, airport_code: str) -> Optional[str]:
        """
        Convertit une date/heure locale en UTC en utilisant la timezone de l'aéroport
        
        Args:
            date_str (str): Date au format YYYY-MM-DD
            time_str (str): Heure au format HH:MM
            airport_code (str): Code IATA de l'aéroport
            
        Returns:
            Optional[str]: Date/heure UTC au format ISO (YYYY-MM-DDTHH:MM:SSZ) ou None
        """
        if not date_str or not time_str or not airport_code:
            return None
        
        try:
            # Récupérer la timezone de l'aéroport
            timezone_str = self.timezone_provider.get_timezone_from_iata(airport_code)
            if not timezone_str:
                print(f"[WARNING] Timezone non trouvée pour l'aéroport {airport_code}")
                return None
            
            # Créer un objet datetime à partir de la date et heure locale
            local_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            
            # Créer la timezone
            local_tz = pytz.timezone(timezone_str)
            
            # Localiser le datetime (ajouter l'info de timezone)
            localized_dt = local_tz.localize(local_datetime)
            
            # Convertir en UTC
            utc_dt = localized_dt.astimezone(pytz.UTC)
            
            # Retourner au format ISO
            return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            
        except Exception as e:
            print(f"[ERREUR] Conversion UTC pour {airport_code} {date_str} {time_str}: {e}")
            return None
