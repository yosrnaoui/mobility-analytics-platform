"""
API Views pour la Mobility Analytics Platform.
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
import json

from .models import Trajectory, TrajectoryPoint
from .services import process_trajectory, generate_sample_trajectory


@csrf_exempt
@require_http_methods(["POST"])
def upload_trajectory(request):
    """
    POST /api/trajectories/upload/
    Charge un fichier GPS, calcule les métriques et détecte les anomalies.
    """
    if 'file' not in request.FILES:
        return JsonResponse({'error': 'Aucun fichier fourni.'}, status=400)

    uploaded = request.FILES['file']
    filename = uploaded.name
    name = request.POST.get('name', filename)
    description = request.POST.get('description', '')

    try:
        content = uploaded.read()
        result = process_trajectory(content, filename)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=422)
    except Exception as e:
        return JsonResponse({'error': f'Erreur de traitement : {e}'}, status=500)

    metrics = result['metrics']
    points_data = result['points']

    # Sauvegarde en base
    trajectory = Trajectory.objects.create(
        name=name,
        description=description,
        total_distance_km=metrics['total_distance_km'],
        avg_speed_kmh=metrics['avg_speed_kmh'],
        max_speed_kmh=metrics['max_speed_kmh'],
        duration_minutes=metrics['duration_minutes'],
        point_count=metrics['point_count'],
        anomaly_count=metrics['anomaly_count'],
    )

    TrajectoryPoint.objects.bulk_create([
        TrajectoryPoint(
            trajectory=trajectory,
            timestamp=p['timestamp'],
            latitude=p['latitude'],
            longitude=p['longitude'],
            altitude=p.get('altitude'),
            speed_kmh=p.get('speed_kmh'),
            is_anomaly=p['is_anomaly'],
            anomaly_reason=p.get('anomaly_reason', ''),
            sequence_index=i,
        )
        for i, p in enumerate(points_data)
    ])

    return JsonResponse({
        'id': trajectory.id,
        'name': trajectory.name,
        'metrics': metrics,
        'points': points_data,
    }, status=201)


@require_http_methods(["GET"])
def list_trajectories(request):
    """GET /api/trajectories/ — Liste toutes les trajectoires."""
    trajectories = Trajectory.objects.values(
        'id', 'name', 'description', 'created_at',
        'total_distance_km', 'avg_speed_kmh', 'max_speed_kmh',
        'duration_minutes', 'point_count', 'anomaly_count',
    )
    return JsonResponse({'trajectories': list(trajectories)})


@require_http_methods(["GET"])
def get_trajectory(request, pk):
    """GET /api/trajectories/<pk>/ — Détail + points d'une trajectoire."""
    try:
        t = Trajectory.objects.get(pk=pk)
    except Trajectory.DoesNotExist:
        return JsonResponse({'error': 'Trajectoire introuvable.'}, status=404)

    points = list(t.points.values(
        'sequence_index', 'latitude', 'longitude', 'timestamp',
        'altitude', 'speed_kmh', 'is_anomaly', 'anomaly_reason',
    ))

    return JsonResponse({
        'id': t.id,
        'name': t.name,
        'description': t.description,
        'created_at': t.created_at.isoformat(),
        'metrics': {
            'total_distance_km': t.total_distance_km,
            'avg_speed_kmh': t.avg_speed_kmh,
            'max_speed_kmh': t.max_speed_kmh,
            'duration_minutes': t.duration_minutes,
            'point_count': t.point_count,
            'anomaly_count': t.anomaly_count,
        },
        'points': points,
    })


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_trajectory(request, pk):
    """DELETE /api/trajectories/<pk>/"""
    try:
        Trajectory.objects.get(pk=pk).delete()
        return JsonResponse({'message': 'Supprimée.'})
    except Trajectory.DoesNotExist:
        return JsonResponse({'error': 'Trajectoire introuvable.'}, status=404)


@require_http_methods(["GET"])
def demo_trajectory(request):
    """
    GET /api/trajectories/demo/
    Retourne une trajectoire simulée sans rien sauvegarder en base.
    """
    from .services import generate_sample_trajectory, compute_metrics, detect_anomalies
    import pandas as pd

    raw_points = generate_sample_trajectory()
    df = pd.DataFrame(raw_points)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df.sort_values('timestamp', inplace=True)
    df.reset_index(drop=True, inplace=True)

    from .services import compute_metrics, detect_anomalies
    metrics_result = compute_metrics(df)
    df_enriched = detect_anomalies(metrics_result.pop('df'))

    points_out = []
    for _, row in df_enriched.iterrows():
        points_out.append({
            'latitude':      float(row['latitude']),
            'longitude':     float(row['longitude']),
            'timestamp':     row['timestamp'].isoformat(),
            'altitude':      float(row['altitude']) if 'altitude' in row else None,
            'speed_kmh':     round(float(row['speed_kmh']), 2) if 'speed_kmh' in row else None,
            'is_anomaly':    bool(row['is_anomaly']),
            'anomaly_reason': str(row['anomaly_reason']) if row['is_anomaly'] else '',
        })

    return JsonResponse({
        'id': 'demo',
        'name': 'Démo — Tunis → Carthage',
        'metrics': {**metrics_result, 'anomaly_count': int(df_enriched['is_anomaly'].sum())},
        'points': points_out,
    })
