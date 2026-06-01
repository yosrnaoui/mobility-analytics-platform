from django.urls import path
from . import views

urlpatterns = [
    path('trajectories/', views.list_trajectories, name='trajectory-list'),
    path('trajectories/upload/', views.upload_trajectory, name='trajectory-upload'),
    path('trajectories/demo/', views.demo_trajectory, name='trajectory-demo'),
    path('trajectories/<int:pk>/', views.get_trajectory, name='trajectory-detail'),
    path('trajectories/<int:pk>/delete/', views.delete_trajectory, name='trajectory-delete'),
]
