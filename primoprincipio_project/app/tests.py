from django.test import TestCase
class Smoke(TestCase):
    def test_home(self):
        self.assertEqual(self.client.get("/").status_code, 200)
