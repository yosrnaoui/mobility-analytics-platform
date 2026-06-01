"""
Service d'analyse de trajectoires GPS.
Utilise Pandas et GeoPandas pour les calculs de distance, vitesse et détection d'anomalies.
"""

import pandas as pd
import numpy as np
from math import radians, cos, sin, asin, sqrt
from datetime import datetime
import io
import json


# ── Constantes ────────────────────────────────────────────────────────────────
EARTH_RADIUS_KM = 6371.0
ANOMALY_SPEED_THRESHOLD_KMH = 200.0   # vitesse irréaliste
ANOMALY_ACCEL_THRESHOLD = 50.0        # accélération brutale (km/h par seconde)
ANOMALY_GAP_MINUTES = 30.0            # saut temporel suspect


# ── Utilitaires géographiques ─────────────────────────────────────────────────

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcule la distance en kilomètres entre deux points GPS
    en utilisant la formule de Haversine.
    """
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))


# ── Chargement et validation ──────────────────────────────────────────────────

def load_gps_data(file_content: bytes, filename: str) -> pd.DataFrame:
    """
    Charge un fichier GPS (CSV ou GeoJSON) et retourne un DataFrame normalisé.
    Colonnes requises : latitude, longitude, timestamp
    """
    ext = filename.lower().split('.')[-1]

    if ext == 'csv':
        df = pd.read_csv(io.BytesIO(file_content))
    elif ext == 'json' or ext == 'geojson':
        data = json.loads(file_content)
        if 'features' in data:                # GeoJSON FeatureCollection
            rows = []
            for feat in data['features']:
                props = feat.get('properties', {})
                coords = feat['geometry']['coordinates']
                props['longitude'] = coords[0]
                props['latitude'] = coords[1]
                if len(coords) > 2:
                    props['altitude'] = coords[2]
                rows.append(props)
            df = pd.DataFrame(rows)
        else:
            df = pd.DataFrame(data)
    else:
        raise ValueError(f"Format non supporté : {ext}. Utilisez CSV ou GeoJSON.")

    # Normalisation des noms de colonnes
    df.columns = [c.lower().strip() for c in df.columns]
    col_map = {
        'lat': 'latitude', 'lon': 'longitude', 'lng': 'longitude',
        'time': 'timestamp', 'datetime': 'timestamp', 'date': 'timestamp',
        'alt': 'altitude', 'elev': 'altitude', 'elevation': 'altitude',
    }
    df.rename(columns=col_map, inplace=True)

    required = {'latitude', 'longitude', 'timestamp'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes : {missing}")

    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')
    df.dropna(subset=['latitude', 'longitude', 'timestamp'], inplace=True)
    df.sort_values('timestamp', inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


# ── Calculs métriques ─────────────────────────────────────────────────────────

def compute_metrics(df: pd.DataFrame) -> dict:
    """
    Calcule distance, vitesse et durée pour un DataFrame GPS.
    Retourne un dict de métriques + le DataFrame enrichi.
    """
    if len(df) < 2:
        return {
            'total_distance_km': 0.0,
            'avg_speed_kmh': 0.0,
            'max_speed_kmh': 0.0,
            'duration_minutes': 0.0,
            'point_count': len(df),
            'df': df,
        }

    # Distance segment par segment
    df = df.copy()
    distances = [0.0]
    speeds = [0.0]

    for i in range(1, len(df)):
        d = haversine(
            df.loc[i - 1, 'latitude'], df.loc[i - 1, 'longitude'],
            df.loc[i, 'latitude'],     df.loc[i, 'longitude'],
        )
        dt_hours = (
            df.loc[i, 'timestamp'] - df.loc[i - 1, 'timestamp']
        ).total_seconds() / 3600.0
        distances.append(d)
        speeds.append(d / dt_hours if dt_hours > 0 else 0.0)

    df['segment_distance_km'] = distances
    df['speed_kmh'] = speeds

    total_distance = sum(distances)
    duration_minutes = (
        df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]
    ).total_seconds() / 60.0
    avg_speed = (total_distance / (duration_minutes / 60)) if duration_minutes > 0 else 0.0
    max_speed = df['speed_kmh'].max()

    return {
        'total_distance_km': round(total_distance, 3),
        'avg_speed_kmh': round(avg_speed, 2),
        'max_speed_kmh': round(max_speed, 2),
        'duration_minutes': round(duration_minutes, 2),
        'point_count': len(df),
        'df': df,
    }


# ── Détection d'anomalies ─────────────────────────────────────────────────────

def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Marque les points GPS suspects.
    Stratégies : vitesse excessive, accélération brutale, saut temporel, coordonnées invalides.
    """
    df = df.copy()
    df['is_anomaly'] = False
    df['anomaly_reason'] = ''

    def flag(mask, reason):
        df.loc[mask, 'is_anomaly'] = True
        df.loc[mask, 'anomaly_reason'] = df.loc[mask, 'anomaly_reason'].apply(
            lambda r: f"{r}; {reason}" if r else reason
        )

    # 1. Coordonnées hors limites
    invalid_coords = (
        (df['latitude'] < -90) | (df['latitude'] > 90) |
        (df['longitude'] < -180) | (df['longitude'] > 180)
    )
    flag(invalid_coords, 'Coordonnées invalides')

    if 'speed_kmh' in df.columns:
        # 2. Vitesse irréaliste
        flag(df['speed_kmh'] > ANOMALY_SPEED_THRESHOLD_KMH, 'Vitesse excessive')

        # 3. Accélération brutale
        accel = df['speed_kmh'].diff().abs()
        flag(accel > ANOMALY_ACCEL_THRESHOLD, 'Accélération brutale')

    # 4. Saut temporel
    time_gaps = df['timestamp'].diff().dt.total_seconds() / 60
    flag(time_gaps > ANOMALY_GAP_MINUTES, f'Saut temporel > {ANOMALY_GAP_MINUTES} min')

    # Nettoyer le préfixe "; " résiduel
    df['anomaly_reason'] = df['anomaly_reason'].str.lstrip('; ')
    return df


# ── Pipeline principal ────────────────────────────────────────────────────────

def process_trajectory(file_content: bytes, filename: str) -> dict:
    """
    Pipeline complet : chargement → métriques → anomalies → résultat JSON.
    Retourne un dict prêt à être sérialisé par Django REST Framework.
    """
    df = load_gps_data(file_content, filename)
    metrics = compute_metrics(df)
    df_enriched = detect_anomalies(metrics.pop('df'))

    # Construction de la réponse
    points = []
    for _, row in df_enriched.iterrows():
        points.append({
            'latitude':      float(row['latitude']),
            'longitude':     float(row['longitude']),
            'timestamp':     row['timestamp'].isoformat(),
            'altitude':      float(row['altitude']) if 'altitude' in row and pd.notna(row['altitude']) else None,
            'speed_kmh':     round(float(row['speed_kmh']), 2) if 'speed_kmh' in row else None,
            'is_anomaly':    bool(row['is_anomaly']),
            'anomaly_reason': str(row['anomaly_reason']) if row['is_anomaly'] else '',
        })

    anomaly_count = int(df_enriched['is_anomaly'].sum())

    return {
        'metrics': {**metrics, 'anomaly_count': anomaly_count},
        'points': points,
    }


# ── Génération de données démo ─────────────────────────────────────────────────

def generate_sample_trajectory() -> list[dict]:
    """Génère une trajectoire GPS simulée pour la démo (Tunis → Carthage)."""
    import random
    base_lat, base_lon = 36.8189, 10.1658      # Tunis centre
    points = []
    timestamp = pd.Timestamp('2024-01-15 08:00:00', tz='UTC')

    for i in range(80):
        noise = random.gauss(0, 0.001)
        lat = base_lat + (i * 0.003) + noise
        lon = base_lon + (i * 0.001) + noise
        # Injecter 2 anomalies
        if i in (20, 55):
            lat += random.uniform(0.05, 0.1)

        points.append({
            'latitude':  round(lat, 6),
            'longitude': round(lon, 6),
            'timestamp': timestamp.isoformat(),
            'altitude':  round(random.uniform(5, 50), 1),
        })
        timestamp += pd.Timedelta(seconds=random.randint(10, 30))

    return points
