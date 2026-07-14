# simulation/tests/test_problem2_api.py
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from simulation.models import ModelRun, EventSnapshot


class Problem2ApiTests(APITestCase):
    def setUp(self):
        self.url = reverse("oidio_batch_api")

    @patch("simulation.services.random.choice", side_effect=[0.2, 0.4, 0.2, 0.4])
    def test_batch_creates_run_and_snapshots(self, _mock_choice):
        payload = {
            "days": [
                {
                    "doy": 126,
                    "temperature": 15.94,
                    "bagnatura": 1,
                    "humidity": 97.25,
                    "rain": 0.0,
                },
                {
                    "doy": 127,
                    "temperature": 17.15,
                    "bagnatura": 0,
                    "humidity": 42.35,
                    "rain": 0.0,
                },
                {
                    "doy": 128,
                    "temperature": 37.0,
                    "bagnatura": 1,
                    "humidity": 42.35,
                    "rain": 10.0,
                },
            ],
            "events": []
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ModelRun.objects.count(), 1)
        self.assertEqual(len(response.data["outputs"]), 3)

        run = ModelRun.objects.first()
        self.assertEqual(run.first_doy, 126)
        self.assertEqual(run.last_doy, 128)

        snapshots = EventSnapshot.objects.filter(run=run).order_by("doy", "event_index")
        self.assertTrue(snapshots.exists())

        doy_126 = snapshots.filter(doy=126)
        doy_127 = snapshots.filter(doy=127)
        doy_128 = snapshots.filter(doy=128)

        self.assertEqual(doy_126.count(), 1)
        self.assertEqual(doy_127.count(), 1)
        self.assertGreaterEqual(doy_128.count(), 2)

    def test_batch_requires_days(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "days is required")