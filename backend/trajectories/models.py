from django.db import models
import json


class Trajectory(models.Model):
    """Représente une trajectoire GPS chargée par l'utilisateur."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='trajectories/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Métriques calculées
    total_distance_km = models.FloatField(null=True, blank=True)
    avg_speed_kmh = models.FloatField(null=True, blank=True)
    max_speed_kmh = models.FloatField(null=True, blank=True)
    duration_minutes = models.FloatField(null=True, blank=True)
    point_count = models.IntegerField(default=0)
    anomaly_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Trajectory'
        verbose_name_plural = 'Trajectories'

    def __str__(self):
        return f"{self.name} ({self.created_at.strftime('%Y-%m-%d')})"


class TrajectoryPoint(models.Model):
    """Un point GPS individuel appartenant à une trajectoire."""
    trajectory = models.ForeignKey(
        Trajectory, on_delete=models.CASCADE, related_name='points'
    )
    timestamp = models.DateTimeField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    altitude = models.FloatField(null=True, blank=True)
    speed_kmh = models.FloatField(null=True, blank=True)
    is_anomaly = models.BooleanField(default=False)
    anomaly_reason = models.CharField(max_length=255, blank=True)
    sequence_index = models.IntegerField(default=0)

    class Meta:
        ordering = ['sequence_index']

    def __str__(self):
        return f"Point {self.sequence_index} of {self.trajectory.name}"
