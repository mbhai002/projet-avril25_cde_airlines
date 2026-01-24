FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y wget bash dos2unix && apt-get clean

# installation des dépendances python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copie du Python + scripts shell
COPY fleet_average_age.py .
COPY cleanup_iata_dups.py .
COPY fast_load_seeds.py .
COPY alim_airlines_dims.sh . 
COPY fix_headers.sh .
COPY run_seed_prepare.sh .

# convertir les fins de ligne CRLF vers LF
RUN dos2unix /app/alim_airlines_dims.sh \
    && dos2unix /app/fix_headers.sh \
    && dos2unix /app/run_seed_prepare.sh

# rendre executables
RUN chmod +x /app/fleet_average_age.py \
    && chmod +x /app/cleanup_iata_dups.py \
    && chmod +x /app/fast_load_seeds.py \
    && chmod +x /app/alim_airlines_dims.sh \
    && chmod +x /app/fix_headers.sh \
    && chmod +x /app/run_seed_prepare.sh

CMD ["/bin/bash", "/app/run_seed_prepare.sh"]

