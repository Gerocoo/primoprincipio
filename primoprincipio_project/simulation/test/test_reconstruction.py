# simulation/tests/test_reconstruction.py
from django.test import TestCase
from simulation.models import ModelRun, EventSnapshot
from datetime import date


class ReconstructionTests(TestCase):
    def test_can_reconstruct_single_event_history(self):
        run = ModelRun.objects.create(
            run_date=date.today(),
            first_doy=126,
            last_doy=128,
        )

        EventSnapshot.objects.create(run=run, doy=126, event_index=0, x_value=0.0)
        EventSnapshot.objects.create(run=run, doy=127, event_index=0, x_value=0.2)
        EventSnapshot.objects.create(run=run, doy=128, event_index=0, x_value=0.4)

        history = list(
            EventSnapshot.objects.filter(run=run, event_index=0)
            .order_by("doy")
            .values_list("doy", "x_value")
        )

        self.assertEqual(history, [(126, 0.0), (127, 0.2), (128, 0.4)])