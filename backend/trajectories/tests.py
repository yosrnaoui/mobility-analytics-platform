"""
Tests unitaires pour la Mobility Analytics Platform.
"""

from django.test import TestCase, Client
from django.urls import reverse
import json
import io


SAMPLE_CSV = b"""timestamp,latitude,longitude,altitude
2024-01-15T08:00:00+00:00,36.8189,10.1658,12.5
2024-01-15T08:00:15+00:00,36.8192,10.1661,13.0
2024-01-15T08:00:32+00:00,36.8196,10.1664,13.2
2024-01-15T08:00:48+00:00,36.8201,10.1668,14.0
2024-01-15T08:01:05+00:00,36.8207,10.1672,14.5
"""


class TrajectoryAPITests(TestCase):

    def setUp(self):
        self.client = Client()

    def test_list_trajectories_empty(self):
        """La liste est vide au départ."""
        response = self.client.get('/api/trajectories/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['trajectories'], [])

    def test_upload_csv(self):
        """Upload d'un CSV valide retourne les métriques."""
        csv_file = io.BytesIO(SAMPLE_CSV)
        csv_file.name = 'test.csv'
        response = self.client.post(
            '/api/trajectories/upload/',
            {'file': csv_file, 'name': 'Test Upload'},
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn('metrics', data)
        self.assertIn('points', data)
        self.assertGreater(data['metrics']['point_count'], 0)
        self.assertGreater(data['metrics']['total_distance_km'], 0)

    def test_demo_endpoint(self):
        """Le endpoint démo retourne des données sans sauvegarder."""
        response = self.client.get('/api/trajectories/demo/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['id'], 'demo')
        self.assertIn('metrics', data)
        self.assertIn('points', data)
        self.assertGreater(len(data['points']), 0)

    def test_upload_no_file(self):
        """Upload sans fichier retourne une erreur 400."""
        response = self.client.post('/api/trajectories/upload/', {})
        self.assertEqual(response.status_code, 400)

    def test_trajectory_detail(self):
        """Charger le détail d'une trajectoire existante."""
        # Créer d'abord une trajectoire
        csv_file = io.BytesIO(SAMPLE_CSV)
        csv_file.name = 'test.csv'
        upload_resp = self.client.post(
            '/api/trajectories/upload/',
            {'file': csv_file, 'name': 'Detail Test'},
        )
        traj_id = upload_resp.json()['id']

        # Récupérer le détail
        response = self.client.get(f'/api/trajectories/{traj_id}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['id'], traj_id)
        self.assertIn('points', data)

    def test_delete_trajectory(self):
        """Supprimer une trajectoire existante."""
        csv_file = io.BytesIO(SAMPLE_CSV)
        csv_file.name = 'test.csv'
        upload_resp = self.client.post(
            '/api/trajectories/upload/',
            {'file': csv_file, 'name': 'Delete Test'},
        )
        traj_id = upload_resp.json()['id']

        response = self.client.delete(f'/api/trajectories/{traj_id}/delete/')
        self.assertEqual(response.status_code, 200)

        # Vérifier que c'est bien supprimé
        get_resp = self.client.get(f'/api/trajectories/{traj_id}/')
        self.assertEqual(get_resp.status_code, 404)


class ServicesTests(TestCase):

    def test_haversine(self):
        """Distance Haversine entre Tunis et Carthage."""
        from trajectories.services import haversine
        dist = haversine(36.8189, 10.1658, 36.8525, 10.3236)
        self.assertAlmostEqual(dist, 15.1, delta=2.0)

    def test_process_trajectory(self):
        """Pipeline complet sur un CSV de test."""
        from trajectories.services import process_trajectory
        result = process_trajectory(SAMPLE_CSV, 'test.csv')
        self.assertIn('metrics', result)
        self.assertIn('points', result)
        self.assertEqual(result['metrics']['point_count'], 5)
        self.assertGreater(result['metrics']['total_distance_km'], 0)
