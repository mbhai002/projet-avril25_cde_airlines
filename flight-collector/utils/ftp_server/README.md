# Airportinfo Data Server

## 📋 Description

Serveur PHP pour servir les données HTML brutes collectées depuis airportinfo.live, permettant de contourner les limitations Cloudflare pour les instances multiples de votre collecteur.

## 🚀 Installation

### 1. Structure des fichiers sur le serveur FTP

```
/airportinfo/
├── index.php              # Endpoint principal
├── list.php               # Listing des fichiers
├── documentation.html     # Documentation interactive
├── README.md             # Ce fichier
└── data/                 # Dossier contenant les fichiers HTML
    ├── raw_CDG_departure_2025-11-12_14h_20251112_142530.html
    ├── raw_JFK_departure_2025-11-12_15h_20251112_152645.html
    └── ...
```

### 2. Upload des fichiers

```bash
# Via FTP
ftp 7k0n6.ftp.infomaniak.com
user: 7k0n6_dst
password: DST@datascientest123

# Ou via votre client FTP préféré (FileZilla, WinSCP, etc.)
```

### 3. Permissions

```bash
chmod 755 index.php list.php
chmod 755 data/
chmod 644 data/*.html
```

### 4. Configuration du collecteur Python

Modifiez `ftp_remote_directory` dans votre configuration:

```python
ftp_remote_directory: str = "/airportinfo/data"
```

## 🔌 Utilisation

### Endpoint principal: `index.php`

Récupère les données HTML pour un aéroport/date/heure spécifique.

**Paramètres:**
- `iataAirport` (requis) - Code IATA (ex: CDG, JFK, LHR)
- `depArr` (optionnel) - Type: `departure` ou `arrival` (défaut: departure)
- `date` (optionnel) - Format YYYY-MM-DD (défaut: aujourd'hui)
- `shift` (optionnel) - Heure 00-23 (défaut: 00)

**Exemple Python:**
```python
import requests

response = requests.post('https://votre-domaine.com/airportinfo/index.php', data={
    'iataAirport': 'CDG',
    'depArr': 'departure',
    'date': '2025-11-12',
    'shift': '14'
})

if response.status_code == 200:
    html = response.text
    age_minutes = response.headers.get('X-Data-Age-Minutes')
    print(f"Data age: {age_minutes} minutes")
```

### Listing: `list.php`

Retourne la liste de tous les fichiers disponibles en JSON.

**Filtres optionnels:**
- `airport` - Code IATA
- `date` - Date YYYY-MM-DD
- `depArr` - Type de vol

**Exemple:**
```bash
curl "https://votre-domaine.com/airportinfo/list.php?airport=CDG&date=2025-11-12"
```

## 📊 Réponse JSON de list.php

```json
{
  "status": "success",
  "stats": {
    "total_files": 50,
    "airports": ["CDG", "JFK", "LHR", ...],
    "dates": ["2025-11-12", "2025-11-11"],
    "oldest_file_age_hours": 2.5,
    "newest_file_age_hours": 0.1
  },
  "files": [
    {
      "filename": "raw_CDG_departure_2025-11-12_14h_20251112_142530.html",
      "airport": "CDG",
      "type": "departure",
      "date": "2025-11-12",
      "shift": "14",
      "timestamp": "20251112_142530",
      "size": 45678,
      "modified": "2025-11-12 14:25:30",
      "age_hours": 0.5
    }
  ]
}
```

## 🔄 Intégration avec le collecteur

Modifiez `flight_data_scrapper.py` pour utiliser votre serveur au lieu d'airportinfo.live:

```python
class FlightDataScraper:
    def __init__(self, lang: str = "en", use_cache_server: bool = False, cache_server_url: str = None):
        self.use_cache_server = use_cache_server
        self.cache_server_url = cache_server_url or "https://votre-domaine.com/airportinfo/index.php"
        self.base_url = self.cache_server_url if use_cache_server else "https://data.airportinfo.live/airportic.php"
```

## ⚙️ Configuration

Dans `index.php`, vous pouvez ajuster:

```php
define('DATA_DIR', __DIR__ . '/data/');
define('MAX_AGE_HOURS', 24); // Durée de validité des données
```

## 🔒 Sécurité

### Protection contre les abus

Ajoutez un `.htaccess` pour limiter les requêtes:

```apache
# Rate limiting
<IfModule mod_ratelimit.c>
    SetOutputFilter RATE_LIMIT
    SetEnv rate-limit 400
</IfModule>

# Bloquer les mauvais bots
SetEnvIfNoCase User-Agent "^$" bad_bot
Deny from env=bad_bot
```

### Authentification optionnelle

Pour restreindre l'accès, ajoutez dans `index.php`:

```php
// Authentification simple
$api_key = $_SERVER['HTTP_X_API_KEY'] ?? '';
if ($api_key !== 'votre_cle_secrete') {
    http_response_code(401);
    die('Unauthorized');
}
```

## 📈 Monitoring

### Logs Apache

Les requêtes sont automatiquement loguées dans les logs Apache du serveur.

### Script de nettoyage automatique

Créez `cleanup.php` pour supprimer les vieux fichiers:

```php
<?php
define('DATA_DIR', __DIR__ . '/data/');
define('MAX_AGE_DAYS', 7);

$files = glob(DATA_DIR . 'raw_*.html');
$deleted = 0;

foreach ($files as $file) {
    if (time() - filemtime($file) > MAX_AGE_DAYS * 86400) {
        unlink($file);
        $deleted++;
    }
}

echo "Deleted $deleted old files\n";
```

Ajoutez un cron job:
```bash
0 2 * * * php /path/to/cleanup.php
```

## 🧪 Tests

### Test manuel

```bash
# Test basique
curl -X POST https://votre-domaine.com/airportinfo/index.php \
  -d "iataAirport=CDG" \
  -d "depArr=departure" \
  -d "date=2025-11-12" \
  -d "shift=14"

# Test listing
curl https://votre-domaine.com/airportinfo/list.php

# Test avec filtres
curl "https://votre-domaine.com/airportinfo/list.php?airport=CDG"
```

### Script de test Python

```python
import requests

def test_cache_server(base_url):
    # Test 1: Récupération de données
    response = requests.post(f"{base_url}/index.php", data={
        'iataAirport': 'CDG',
        'depArr': 'departure',
        'date': '2025-11-12',
        'shift': '14'
    })
    
    print(f"Status: {response.status_code}")
    print(f"Data age: {response.headers.get('X-Data-Age-Minutes')} min")
    
    # Test 2: Listing
    response = requests.get(f"{base_url}/list.php")
    data = response.json()
    print(f"Total files: {data['stats']['total_files']}")
    print(f"Airports: {', '.join(data['stats']['airports'][:5])}")

test_cache_server("https://votre-domaine.com/airportinfo")
```

## 🆘 Dépannage

### Erreur 404
- Vérifiez que les fichiers PHP sont bien uploadés
- Vérifiez le chemin `DATA_DIR` dans `index.php`

### Erreur 500
- Vérifiez les permissions (755 pour PHP, 644 pour HTML)
- Vérifiez les logs Apache

### Pas de données
- Vérifiez que le collecteur Python uploade bien vers `/airportinfo/data/`
- Utilisez `list.php` pour voir les fichiers disponibles

## 📝 Changelog

### v1.0 (2025-11-12)
- Version initiale
- Support GET/POST
- Listing JSON
- Documentation interactive

## 👨‍💻 Auteur

Data Science Test Project - Collecteur de vols

## 📄 Licence

Usage interne - Data Science Test Project
