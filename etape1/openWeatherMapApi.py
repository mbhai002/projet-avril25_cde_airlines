import requests
import json

# Limitation : 1,000 API calls per day for free 
# https://openweathermap.org/api
# https://openweathermap.org/current
# https://openweathermap.org/forecast5

# Permet de récupérer le temps sur tout point du globe

class OpenWeatherClient:
    def __init__(self, api_key: str, lat: str, lon: str):
        self.api_key = api_key
        self.lat = lat
        self.lon = lon
        self.base_url = "https://api.openweathermap.org/data/2.5/"

    def _build_url(self, endpoint: str) -> str:
        return f"{self.base_url}{endpoint}?lat={self.lat}&lon={self.lon}&appid={self.api_key}&units=metric"

    def _get_data(self, endpoint: str) -> dict:
        url = self._build_url(endpoint)
        response = requests.get(url)
        if response.status_code == 200:
            print(f"Données reçues depuis {endpoint}")
            return response.json()
        else:
            print(f"Erreur {response.status_code} pour {endpoint}")
            return {}

    def save_to_file(self, data: dict, filename: str):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Données sauvegardées dans {filename}")

    def fetch_and_save_weather(self):
        data = self._get_data("weather")
        if data:
            self.save_to_file(data, "weather.json")

    def fetch_and_save_forecast(self):
        data = self._get_data("forecast")
        if data:
            self.save_to_file(data, "forecast.json")

# Cayenne
client = OpenWeatherClient(
        api_key="782940975705336b8df7397e5aed67ec",
        lat="5.00",
        lon="-52.60"
    )

# # Océan
# client = OpenWeatherClient(
#         api_key="782940975705336b8df7397e5aed67ec",
#         lat="8.2",
#         lon="-50.8"
#     )

# # Antarctique
# client = OpenWeatherClient(
#         api_key="782940975705336b8df7397e5aed67ec",
#         lat="-77",
#         lon="-78"
#     )

client.fetch_and_save_weather()
client.fetch_and_save_forecast()

