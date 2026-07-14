from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class Problem1ApiTests(APITestCase):
    def setUp(self):
        self.url = reverse("simulation_api")

    def test_post_valid_first_call_creates_event(self):
        payload = {
            "doy": 126,
            "temperature": 15.94,
            "bagnatura": 1,
            "humidity": 97.25,
            "rain": 0.0,
        }
        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["doy"], 126)
        self.assertEqual(len(response.data["events"]), 1)
        self.assertEqual(response.data["events"][0]["index"], 0)
        self.assertEqual(response.data["events"][0]["X"], 0.0)

    def test_post_missing_fields_returns_400(self):
        payload = {"doy": 126}
        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    @patch("simulation.services.random.choice", return_value=0.2)
    def test_successive_calls_update_existing_events(self, _mock_choice):
        first_payload = {
            "doy": 126,
            "temperature": 15.94,
            "bagnatura": 1,
            "humidity": 97.25,
            "rain": 0.0,
        }
        first_response = self.client.post(self.url, first_payload, format="json")

        second_payload = {
            "doy": 127,
            "temperature": 17.15,
            "bagnatura": 0,
            "humidity": 42.35,
            "rain": 0.0,
            "events": first_response.data["events"],
        }
        second_response = self.client.post(self.url, second_payload, format="json")

        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(second_response.data["events"]), 1)
        self.assertEqual(second_response.data["events"][0]["X"], 0.2)

    @patch("simulation.services.random.choice", side_effect=[0.2, 0.4, 0.6, 0.8, 1.0, 1.0])
    def test_x_is_monotonic_and_capped_at_one(self, _mock_choice):
        events = [{"index": 0, "X": 0.0}]
        previous_x = 0.0

        for doy in range(127, 133):
            payload = {
                "doy": doy,
                "temperature": 20.0,
                "bagnatura": 0,
                "humidity": 40.0,
                "rain": 0.0,
                "events": events,
            }
            response = self.client.post(self.url, payload, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            events = response.data["events"]
            current_x = events[0]["X"]

            self.assertGreaterEqual(current_x, previous_x)
            self.assertLessEqual(current_x, 1.0)
            previous_x = current_x

    @patch("simulation.services.random.choice", return_value=0.4)
    def test_new_event_is_appended_on_later_call(self, _mock_choice):
        payload = {
            "doy": 129,
            "temperature": 37.0,
            "bagnatura": 1,
            "humidity": 42.35,
            "rain": 10.0,
            "events": [{"index": 0, "X": 0.4}],
        }
        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["events"]), 2)
        self.assertEqual(response.data["events"][1]["index"], 1)
        self.assertEqual(response.data["events"][1]["X"], 0.0)