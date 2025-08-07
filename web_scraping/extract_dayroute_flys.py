from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from datetime import datetime
import time


class ExtractFlightDates:

    def __init__(self):
        options = Options()
        options.add_argument("--headless")
        self.driver = webdriver.Chrome(options=options)

    @staticmethod
    def is_valid_date(date_str):
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def search(self, source_airport_iata, dest_airport_iata, flight_date):
        if not ExtractFlightDates.is_valid_date(flight_date):
            print(f"Format de date invalide : {flight_date}. Format attendu : YYYY-MM-DD.")
            return []

        url = f"https://www.flightsfrom.com/{source_airport_iata}-{dest_airport_iata}"
        self.driver.get(url)
        time.sleep(3)

        try:
            # Ouvre le calendrier et choisit la date
            self.driver.find_element(By.CSS_SELECTOR, ".datepicker-toggle").click()
            self.driver.find_element(By.XPATH, f"//td[@data-date='{flight_date}']").click()
            time.sleep(2)

            html = self.driver.page_source
            soup = BeautifulSoup(html, "html.parser")
            flights = soup.select("div.flightRouteList__item")

            results = []
            for flight in flights:
                airline = flight.select_one(".flightRouteList__airlineName")
                flight_number = flight.select_one(".flightRouteList__flightNumber")
                time_dep = flight.select_one(".flightRouteList__departureTime")

                if airline and flight_number and time_dep:
                    results.append({
                        "airline": airline.text.strip(),
                        "flight_number": flight_number.text.strip(),
                        "flight_time": time_dep.text.strip()
                    })
                    print(f"{airline.text.strip()} — {flight_number.text.strip()} — {time_dep.text.strip()}")

            return results

        except Exception as e:
            print(f"Erreur lors de l'extraction : {e}")
            return []

    def close(self):
        self.driver.quit() 
    
if __name__ == "__main__":
    dates = ["2025-08-01", "2025-08-02"]  # Exemple
    routes = [
        {"source_airport_iata": "CDG", "dest_airport_iata": "JFK"},
        {"source_airport_iata": "LHR", "dest_airport_iata": "DXB"}
    ]

    extraction = ExtractFlightDates()

    for d in dates:
        for r in routes:
            results = extraction.search(r["source_airport_iata"], r["dest_airport_iata"], d)
            if results:
                # TODO : Écriture dans un fichier ou base de données
                pass

    extraction.close()

