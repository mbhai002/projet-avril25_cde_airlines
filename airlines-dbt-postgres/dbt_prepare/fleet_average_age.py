import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from io import StringIO

def fetch_statbase_table(url, table_index=0):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        raise ValueError("Aucune table HTML trouvée sur la page")
    df_list = pd.read_html(StringIO(str(tables[table_index])))
    return df_list[0]

def download_age_mean_airlines(Groupby='company'):
    DBT_SEED_DIR = os.getenv('SOURCE_DIR', ".")
    if Groupby != 'company':
        Groupby = 'country'
        url = "https://statbase.org/datasets/air-rail-and-water-transportation/aircraft-fleet-average-age/"
    else:
        url = "https://statbase.org/datasets/air-rail-and-water-transportation/aircraft-fleet-average-age-by-company/"
    # Créer le dossier statsbase si nécessaire
    output_dir = os.path.join(DBT_SEED_DIR, "statsbase")
    os.makedirs(output_dir, exist_ok=True)
    output_csv = os.path.join(output_dir, f"fleet_age_by_{Groupby}.csv")
    df = fetch_statbase_table(url, table_index=0)
    df.to_csv(output_csv, index=False, encoding="utf-8")
    print(f"CSV généré : {output_csv}")

if __name__ == "__main__":
    # download_age_mean_airlines('country')
    # download_age_mean_airlines('company')
    print("Ce script est à reprendre car lors de l'exécution de fetch_statbase_table dans le container,  resp = requests.get(url, headers=headers) -> resp.text  ne renvoit pas une table mais du javascript")
    exit(0) 
