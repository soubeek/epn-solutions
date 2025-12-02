# Dockerfile pour Backend Django - Poste Public Manager

FROM python:3.11-slim

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les requirements Python
COPY requirements/production.txt requirements.txt
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copier le code du projet
COPY . .

# Créer les répertoires nécessaires
RUN mkdir -p /var/log/poste-public \
    && mkdir -p staticfiles \
    && mkdir -p media/photos

# Port exposé
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/health/', timeout=5)" || exit 1

# La commande sera définie dans docker-compose.yml
# pour permettre les migrations et collectstatic avant le démarrage
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
