from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from .models import ModelRun, EventSnapshot
from .services import process_single_day, run_problem1_blackbox


class SimulationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_create_event_when_wet_and_rain(self):
        response = self.client.post(
            "/api/simulation/",
            {
                "doy": 126,
                "temperature": 18,
                "bagnatura": 1,
                "humidity": 60,
                "rain": 4,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["events"]), 1)
        self.assertEqual(response.json()["events"][0]["X"], 0.0)

    @patch("simulation.services.random.choice", return_value=1.0)
    def test_x_is_monotonic_and_capped(self, mocked_choice):
        prev = [{"index": 0, "X": 0.9}]
        out = process_single_day(
            {
                "doy": 127,
                "temperature": 20,
                "bagnatura": 0,
                "humidity": 50,
                "rain": 0,
            },
            prev,
        )
        self.assertGreaterEqual(out["events"][0]["X"], 0.9)
        self.assertLessEqual(out["events"][0]["X"], 1.0)

    def test_multiple_iterations_append_new_events(self):
        state = [{"index": 0, "X": 0.2}]
        response = self.client.post(
            "/api/simulation/",
            {
                "doy": 130,
                "temperature": 30,
                "bagnatura": 1,
                "humidity": 82,
                "rain": 5,
                "events": state,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        events = response.json()["events"]
        self.assertEqual(len(events), 2)
        self.assertEqual(events[-1]["index"], 1)
        self.assertEqual(events[-1]["X"], 0.0)

    def test_simulation_api_requires_mandatory_fields(self):
        response = self.client.post(
            "/api/simulation/",
            {
                "doy": 126,
                "temperature": 18,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())


class OidioBatchTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_batch_run_persists_outputs(self):
        payload = {
            "events": [{"index": 0, "X": 0.0}],
            "days": [
                {"doy": 275, "temperature": 30, "bagnatura": 0, "humidity": 32, "rain": 0},
                {"doy": 276, "temperature": 28, "bagnatura": 1, "humidity": 90, "rain": 0},
                {"doy": 277, "temperature": 27, "bagnatura": 1, "humidity": 59, "rain": 22},
            ],
        }

        response = self.client.post("/api/oidio-batch/", payload, format="json")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["outputs"]), 3)
        self.assertIn("run_id", body)
        self.assertEqual(len(body["degree_days"]), 3)

        self.assertEqual(ModelRun.objects.count(), 1)
        self.assertTrue(EventSnapshot.objects.count() > 0)

    def test_batch_requires_days(self):
        response = self.client.post(
            "/api/oidio-batch/",
            {"events": []},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_batch_requires_complete_day_fields(self):
        response = self.client.post(
            "/api/oidio-batch/",
            {
                "events": [],
                "days": [
                    {"doy": 275, "temperature": 30}
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())