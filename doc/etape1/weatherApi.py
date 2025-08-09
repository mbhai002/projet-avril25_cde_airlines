import requests
import json

# Limitation : 1 000 000 de requêtes / mois 
# https://www.weatherapi.com/pricing.aspx


# Commentaire : 
# Endpoint "forecast" :  3 jours de prévision max et pas disponible en mer. Sur la mer, forcast à la journée avec l'endpoint "marine". 
# Endpoint "current" : Temps actuel pour un lieu sur la terre.
# Endpoint "marine" :  Temps actuel pour un lieu en mer ou pas disponible à l'endpoint "current".

class WeatherApiClient:
    def __init__(self, api_key: str, lat: str, lon: str):
        self.api_key = api_key
        self.lat = lat
        self.lon = lon
        self.base_url = "http://api.weatherapi.com/v1"

    def _build_url(self, endpoint: str) -> str:
        url = f"{self.base_url}/{endpoint}.json?key={self.api_key}&q={self.lat},{self.lon}"
        if endpoint == "forecast":
            return f"{url}&days=3" # limité à 3 jour en version gratuite
        else:
            return url

    def _get_data(self, endpoint: str, allow_marine_fallback: bool = False) -> dict:
        url = self._build_url(endpoint)
        response = requests.get(url)
        
        if response.status_code == 200:
            print(f"Données reçues depuis {endpoint}")
            return response.json()
        
        elif response.status_code == 400 and allow_marine_fallback:
            try:
                error_data = response.json()
                if error_data.get("error", {}).get("code") == 1006:
                    print(f"Aucun lieu trouvé pour '{endpoint}'. Tentative avec 'marine'...")
                    return self._get_data("marine", allow_marine_fallback=False)
            except Exception as e:
                print(f"Erreur lors de l’analyse du message d’erreur : {e}")
        
        print(f"Erreur {response.status_code} pour {endpoint}")
        return {}

    def save_to_file(self, data: dict, filename: str):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"💾 Données sauvegardées dans {filename}")

    def fetch_and_save_weather(self):
        data = self._get_data("current", allow_marine_fallback=True)
        if data:
            self.save_to_file(data, "current_weatherApi.json")

    def fetch_and_save_forecast(self):
        data = self._get_data("forecast")
        if data:
            self.save_to_file(data, "forecast_weatherApi.json")


# Cayenne
client = WeatherApiClient(
        api_key="ef49c48610b949a0811153643252506",
        lat="5.00",
        lon="-52.60"
    )

# # Océan
# client = WeatherApiClient(
#         api_key="ef49c48610b949a0811153643252506",
#         lat="8.2",
#         lon="-50.8"
#     )
# # Antarctique
# client = WeatherApiClient(
#         api_key="ef49c48610b949a0811153643252506",
#          lat="-77",
#         lon="-78"
#     )

client.fetch_and_save_weather()
client.fetch_and_save_forecast()
