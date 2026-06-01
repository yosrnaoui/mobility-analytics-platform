from django.contrib import admin
from .models import Trajectory, TrajectoryPoint

@admin.register(Trajectory)
class TrajectoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'total_distance_km', 'avg_speed_kmh', 'point_count', 'anomaly_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']

@admin.register(TrajectoryPoint)
class TrajectoryPointAdmin(admin.ModelAdmin):
    list_display = ['trajectory', 'sequence_index', 'latitude', 'longitude', 'speed_kmh', 'is_anomaly']
    list_filter = ['is_anomaly', 'trajectory']
