FROM postgres:17.4

# Install curl for FTP downloads during initialization
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*
