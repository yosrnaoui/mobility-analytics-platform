# ─── Build Stage ──────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Dépendances système nécessaires pour GeoPandas
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev \
    gdal-bin \
    libgeos-dev \
    libproj-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ─── Production Stage ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS production

WORKDIR /app

# Dépendances système runtime uniquement
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal32 \
    libgeos-c1v5 \
    && rm -rf /var/lib/apt/lists/*

# Copier les paquets Python installés depuis le builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copier le code source
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Variables d'environnement par défaut
ENV DJANGO_SETTINGS_MODULE=core.settings
ENV PYTHONPATH=/app/backend
ENV DEBUG=False
ENV SECRET_KEY=change-me-in-production

WORKDIR /app/backend

# Collecter les fichiers statiques
RUN python manage.py collectstatic --noinput

# Créer les dossiers nécessaires
RUN mkdir -p media

EXPOSE 8000

# Lancer avec Gunicorn en production
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
