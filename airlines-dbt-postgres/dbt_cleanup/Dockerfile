FROM python:3.11-slim

# Dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*
i
# Dossier de travail
WORKDIR /app
COPY . /app

# Environnement virtuel
COPY requirements.txt .
RUN python -m venv /cleanup_venv
ENV PATH="/cleanup_venv/bin:$PATH"

# Installer dbt postgres
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copier scripts
COPY  cleanup_dups_airtlines.py .

# Entrypoint par défaut
ENTRYPOINT ["python3", "/app/cleanup_dups.py"]

