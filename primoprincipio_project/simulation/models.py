from django.db import models

class ModelRun(models.Model):
    run_date = models.DateField()
    first_doy = models.IntegerField()
    last_doy = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Run {self.id} [{self.first_doy}-{self.last_doy}]"

class EventSnapshot(models.Model):
    run = models.ForeignKey(ModelRun, related_name='snapshots', on_delete=models.CASCADE)
    doy = models.IntegerField()
    event_index = models.IntegerField()
    x_value = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('run', 'doy', 'event_index')
        ordering = ['doy', 'event_index']

class AlertThreshold(models.Model):
    threshold = models.FloatField()
    email = models.EmailField()
    active = models.BooleanField(default=True)
    last_triggered_doy = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
