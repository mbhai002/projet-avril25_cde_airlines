# Test du Modèle en Production

## Usage

```bash
python "machine learning\test_model_production.py"
```

## Configuration

Éditez `config_test.py` :
- `POSTGRESQL_URI` : URI PostgreSQL (même format que main.py)
- `N_FLIGHTS_TO_TEST` : Nombre de vols (défaut: 1000)
- `MODEL_CONFIG_PATH` : Chemin du modèle (None = le plus récent)

## Que fait-il ?

1. Récupère les N derniers vols de la view "all"
2. Applique le modèle de prédiction
3. Met à jour le champ `delay_prob` dans la table `flight`
