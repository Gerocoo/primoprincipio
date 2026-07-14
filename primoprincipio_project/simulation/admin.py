from django.contrib import admin
from .models import ModelRun, EventSnapshot, AlertThreshold

admin.site.register(ModelRun)
admin.site.register(EventSnapshot)
admin.site.register(AlertThreshold)
