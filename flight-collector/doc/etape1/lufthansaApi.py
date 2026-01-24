import requests
from datetime import datetime, timedelta
import json
import pymongo
from pymongo import MongoClient

class LufthansaAPI:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = self.get_token()
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }

    def get_token(self):
        url = "https://api.lufthansa.com/v1/oauth/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        response = requests.post(url, headers=headers, data=data)
        token = response.json().get("access_token")
        if not token:
            print("Erreur lors de la récupération du token")
            exit()
        return token
    
    def get_countries(self):
        countries = []
        limit = 100
        offset = 0

        while True:
            countries_url = f"https://api.lufthansa.com/v1/mds-references/countries/?lang=EN&limit={limit}&offset={offset}"
            countries_response = requests.get(countries_url, headers=self.headers)
            data = countries_response.json()
            # Accès à la bonne clé dans la structure JSON
            countries_batch = data.get("CountryResource", {}).get("Countries", {}).get("Country", [])
            # On extrait uniquement le code et le nom du pays
            for country in countries_batch:
                country_code = country.get("CountryCode")
                country_name = country.get("Names", {}).get("Name", {}).get("$")
                countries.append({
                "CountryCode": country_code,
                "Name": country_name
            })
            if len(countries_batch) < limit:
                break
            offset += limit
        return countries
    
    def get_cities(self):
        cities = []
        limit = 100
        offset = 0

        while True:
            cities_url = f"https://api.lufthansa.com/v1/mds-references/cities/?lang=EN&limit={limit}&offset={offset}"
            cities_response = requests.get(cities_url, headers=self.headers)
            data = cities_response.json()
            # Accès à la bonne clé dans la structure JSON
            cities_batch = data.get("CityResource", {}).get("Cities", {}).get("City", [])
            # On extrait uniquement le code et le nom de la ville
            for city in cities_batch:
                cities.append({
                    "CityCode": city.get("CityCode"),
                    "CountryCode": city.get("CountryCode"),
                    "Name": city.get("Names", {}).get("Name", {}).get("$")
                })
            if len(cities_batch) < limit:
                break
            offset += limit
        return cities
    
    def get_airports(self):
        airports = []
        limit = 100
        offset = 0

        while True:
            airports_url = f"https://api.lufthansa.com/v1/mds-references/airports/?lang=EN&limit={limit}&offset={offset}&LHoperated=1"
            response = requests.get(airports_url, headers=self.headers)
            data = response.json()
            airport_batch = data.get("AirportResource", {}).get("Airports", {}).get("Airport", [])
            for airport in airport_batch:
                airports.append({
                    "AirportCode": airport.get("AirportCode"),
                    "CityCode": airport.get("CityCode"),
                    "CountryCode": airport.get("CountryCode"),
                    "Name": airport.get("Names", {}).get("Name", {}).get("$"),
                    "Latitude": airport.get("Position", {}).get("Coordinate", {}).get("Latitude"),
                    "Longitude": airport.get("Position", {}).get("Coordinate", {}).get("Longitude"),
                    "UtcOffset": airport.get("UtcOffset"),
                    "TimeZoneId": airport.get("TimeZoneId")
                })
            if len(airport_batch) < limit:
                break
            offset += limit
        return airports
    
    def get_airlines(self):
        airlines = []
        limit = 100
        offset = 0

        while True:
            airlines_url = f"https://api.lufthansa.com/v1/mds-references/airlines/?limit={limit}&offset={offset}"
            response = requests.get(airlines_url, headers=self.headers)
            data = response.json()
            airline_batch = data.get("AirlineResource", {}).get("Airlines", {}).get("Airline", [])
            for airline in airline_batch:
                airlines.append({
                    "AirlineID": airline.get("AirlineID"),
                    "AirlineID_ICAO": airline.get("AirlineID_ICAO"),
                    "Name": airline.get("Names", {}).get("Name", {}).get("$")
                })
            if len(airline_batch) < limit:
                break
            offset += limit
        return airlines
    
    def get_aircraft(self):
        aircraft = []
        limit = 100
        offset = 0

        while True:
            aircraft_url = f"https://api.lufthansa.com/v1/mds-references/aircraft/?&limit={limit}&offset={offset}"
            response = requests.get(aircraft_url, headers=self.headers)
            data = response.json()
            aircraft_batch = data.get("AircraftResource", {}).get("AircraftSummaries", {}).get("AircraftSummary", [])
            for ac in aircraft_batch:
                aircraft.append({
                    "AircraftCode": ac.get("AircraftCode"),
                    "Name": ac.get("Names", {}).get("Name", {}).get("$"),
                    "AirlineEquipCode": ac.get("AirlineEquipCode")
                })
            if len(aircraft_batch) < limit:
                break
            offset += limit
        return aircraft       
       
    
    def get_all_arrivals_by_hour(self, airport_code, date_str, output_file="arrivals.json"):
        """
    Récupère tous les vols arrivant à un aéroport donné pour chaque heure d'une journée.

    L'API est vraiment bizarre car pour certaines heures, elle renvoie un code 400 Bad Request.
    Il faut donc interroger l'API pour chaque heure de la journée, en évitant les doublons.
    
    Pour chaque heure (de 00:00 à 23:00), la fonction interroge l'API Lufthansa et collecte les vols d'arrivée.
    Les doublons sont évités grâce à un identifiant unique par vol.
    Les résultats sont sauvegardés dans un fichier JSON.

    Args:
        airport_code (str): Code IATA de l'aéroport (ex: 'FRA').
        date_str (str): Date au format 'YYYY-MM-DD'.
        output_file (str): Nom du fichier de sortie JSON.

    Returns:
        list: Liste de tous les vols d'arrivée collectés pour la journée.
    """
        all_flights = []
        seen = set()
        for hour in range(24):
            dt_str = f"{date_str}T{hour:02d}:00"
            url = f"https://api.lufthansa.com/v1/operations/customerflightinformation/arrivals/{airport_code}/{dt_str}"
            response = requests.get(url, headers=self.headers)
            print(f"Réponse API: {response.status_code} à {dt_str}")
            if response.status_code != 200:
                continue
            data = response.json()
            flights = data.get("FlightInformation", {}).get("Flights", {}).get("Flight", [])

            if not isinstance(flights, list):
                flights = [flights] if flights else []
            for flight in flights:
                # Identifiant unique basé sur numéro de vol + date/heure de départ
                dep = flight.get("Departure", {})
                op = flight.get("OperatingCarrier", {})
                unique_id = (
                    op.get("AirlineID", "") + "_" +
                    op.get("FlightNumber", "") + "_" +
                    dep.get("Scheduled", {}).get("Date", "") + "_" +
                    dep.get("Scheduled", {}).get("Time", "")
                )
                if unique_id not in seen:
                    seen.add(unique_id)
                    all_flights.append(flight)
        # Sauvegarde dans un fichier JSON
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_flights, f, ensure_ascii=False, indent=2)
        print(f"{len(all_flights)} vols sauvegardés dans {output_file}")
        return all_flights   
    

    
    def save_flights_to_mongodb(self, flights, db_name="dst_airlines", collection_name="flights"):
        """
    Insère une liste de vols dans une collection MongoDB locale.

    Pour chaque vol, un identifiant unique (_id) est généré pour éviter les doublons.
    La fonction calcule et ajoute automatiquement le champ 'DelayMinutes' (retard à l'arrivée en minutes, 0 si à l'heure, None si non calculable).
    Les vols déjà présents (même _id) sont ignorés lors de l'insertion.

    Args:
        flights (list): Liste de dictionnaires représentant les vols à insérer.
        db_name (str): Nom de la base MongoDB (par défaut 'dst_airlines').
        collection_name (str): Nom de la collection (par défaut 'flights').

    Affiche le nombre de vols insérés et un message si certains existaient déjà.
    """
        client = MongoClient("mongodb://localhost:27017/")
        db = client[db_name]
        collection = db[collection_name]
        if flights:
            for flight in flights:
                dep = flight.get("Departure", {})
                op = flight.get("OperatingCarrier", {})
                unique_id = (
                    op.get("AirlineID", "") + "_" +
                    op.get("FlightNumber", "") + "_" +
                    dep.get("Scheduled", {}).get("Date", "") + "_" +
                    dep.get("Scheduled", {}).get("Time", "")
                )
                flight["_id"] = unique_id  # Utilise _id pour éviter les doublons

                # Ajout du champ DelayMinutes
                arr = flight.get("Arrival", {})
                sched = arr.get("Scheduled", {})
                actual = arr.get("Actual", {})
                try:
                    sched_dt = datetime.strptime(f"{sched.get('Date','')}T{sched.get('Time','')}", "%Y-%m-%dT%H:%M")
                    actual_dt = datetime.strptime(f"{actual.get('Date','')}T{actual.get('Time','')}", "%Y-%m-%dT%H:%M")
                    delay = int((actual_dt - sched_dt).total_seconds() // 60)
                    delay = max(delay, 0)
                except Exception:
                    delay = None
                flight["DelayMinutes"] = delay

            try:
                collection.insert_many(flights, ordered=False)
            except Exception as e:
                print("Certains vols existent déjà dans la base :", e)
        print(f"{len(flights)} vols insérés dans MongoDB ({db_name}.{collection_name})")


    def get_arrivals_by_hour_between_dates(self, airport_code, start_date, end_date, output_prefix="arrivals"):
        """
    Récupère tous les vols d'arrivée pour un aéroport entre deux dates incluses.

    Pour chaque date du range, la fonction appelle get_all_arrivals_by_hour et sauvegarde les résultats dans un fichier JSON par jour.
    Tous les vols collectés sont également retournés dans une seule liste.

    Args:
        airport_code (str): Code IATA de l'aéroport (ex: 'FRA').
        start_date (str): Date de début au format 'YYYY-MM-DD'.
        end_date (str): Date de fin au format 'YYYY-MM-DD'.
        output_prefix (str): Préfixe des fichiers de sortie (par défaut 'arrivals').

    Returns:
        list: Liste de tous les vols d'arrivée collectés sur la période.
    """
        current = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        all_flights = []
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            output_file = f"{output_prefix} {date_str}.json"
            flights = self.get_all_arrivals_by_hour(airport_code, date_str, output_file=output_file)
            all_flights.extend(flights)
            current += timedelta(days=1)
        return all_flights

# Exemple d'utilisation 
lufth_api = LufthansaAPI("4wny2qpch3ah5f3ed2vbf8f8n", "yCSFENEnU5")

flights = lufth_api.get_arrivals_by_hour_between_dates("FRA", "2025-07-01", "2025-07-02")
# lufth_api.save_flights_to_mongodb(flights)


# Pour exporter les données de référence dans des fichiers JSON (décommenter si nécessaire)

# countries = lufth_api.get_countries()
# with open("countries.json", "w", encoding="utf-8") as f:
#     json.dump(countries, f, indent=2, ensure_ascii=False)

# cities = lufth_api.get_cities()
# with open("cities.json", "w", encoding="utf-8") as f:
#     json.dump(cities, f, indent=2, ensure_ascii=False)

# airports = lufth_api.get_airports()
# with open("airports.json", "w", encoding="utf-8") as f:
#     json.dump(airports, f, indent=2, ensure_ascii=False)

# airlines = lufth_api.get_airlines()
# with open("airlines.json", "w", encoding="utf-8") as f:
#     json.dump(airlines, f, indent=2, ensure_ascii=False)

# aircraft = lufth_api.get_aircraft()
# with open("aircraft.json", "w", encoding="utf-8") as f:
#     json.dump(aircraft, f, indent=2, ensure_ascii=False)





# Exemples de tests pour comprendre l'API -> certaines heures/minutes renvoient 400 Bad Request mais c'est différent pour chaque jour... A n'y rien comprendre...

# https://api.lufthansa.com/v1/operations/customerflightinformation/departures/FRA/2025-06-30T06:30 -> 200
# https://api.lufthansa.com/v1/operations/customerflightinformation/departures/FRA/2025-06-30T07:00 -> 200
# https://api.lufthansa.com/v1/operations/customerflightinformation/departures/FRA/2025-06-30T07:03 -> 200
# https://api.lufthansa.com/v1/operations/customerflightinformation/departures/FRA/2025-06-30T07:04 -> 200
# https://api.lufthansa.com/v1/operations/customerflightinformation/departures/FRA/2025-06-30T07:05 -> 200
# https://api.lufthansa.com/v1/operations/customerflightinformation/departures/FRA/2025-06-30T07:06 -> 400 Bad Request
# https://api.lufthansa.com/v1/operations/customerflightinformation/departures/FRA/2025-06-30T07:07 -> 400 Bad Request
# https://api.lufthansa.com/v1/operations/customerflightinformation/departures/FRA/2025-06-30T07:08 -> 400 Bad Request
# https://api.lufthansa.com/v1/operations/customerflightinformation/departures/FRA/2025-06-30T07:09 -> 400 Bad Request
# https://api.lufthansa.com/v1/operations/customerflightinformation/departures/FRA/2025-06-30T07:10 -> 400 Bad Request
# https://api.lufthansa.com/v1/operations/customerflightinformation/departures/FRA/2025-06-30T07:11 -> 400 Bad Request
# https://api.lufthansa.com/v1/operations/customerflightinformation/departures/FRA/2025-06-30T07:15 -> 400 Bad Request
# https://api.lufthansa.com/v1/operations/customerflightinformation/departures/FRA/2025-06-30T07:30 -> 400 Bad Request
# https://api.lufthansa.com/v1/operations/customerflightinformation/departures/FRA/2025-06-30T07:45 -> 400 Bad Request
# https://api.lufthansa.com/v1/operations/customerflightinformation/departures/FRA/2025-06-30T08:30 -> 400 Bad Request
# https://api.lufthansa.com/v1/operations/customerflightinformation/departures/FRA/2025-06-30T08:31 -> 200
# https://api.lufthansa.com/v1/operations/customerflightinformation/departures/FRA/2025-06-30T08:32 -> 200


# https://api.lufthansa.com/v1/operations/customerflightinformation/departures/FRA/2025-06-28T07:10 -> 400 Bad Request
# https://api.lufthansa.com/v1/operations/customerflightinformation/departures/FRA/2025-06-28T08:30 -> 400 Bad Request
# https://api.lufthansa.com/v1/operations/customerflightinformation/departures/FRA/2025-06-28T08:31 -> 200


# https://api.lufthansa.com/v1/mds-references/airports/?lang=EN&limit=100&offset=0&LHoperated=1 provoque un retour très étrange
