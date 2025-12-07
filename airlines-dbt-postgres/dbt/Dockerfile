FROM python:3.11-slim

# Dépendances système
RUN apt-get update && apt-get install -y  \
    git build-essential \
    postgresql-client \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Dossier de travail
WORKDIR /app
COPY . /app

# Environnement virtuel
COPY requirements.txt .
RUN python -m venv /dbt_venv
ENV PATH="/dbt_venv/bin:$PATH"

# Installer dbt postgres
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r ./requirements.txt

# Copier scripts
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Entrypoint par défaut
ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]
#CMD ["sleep", "infinity"]


