from django.urls import path
from .views import (
    simulation_api,
    oidio_batch_api,
    oidio_batch_openmeteo_today_api,
    alert_api,
    alert_list_api,
    runs_api,
    run_detail_api,
    map_page,
    model_page,
    dashboard_page,
)

urlpatterns = [
    path("api/simulation/", simulation_api, name="simulation_api"),
    path("api/oidio-batch/", oidio_batch_api, name="oidio_batch_api"),
    path("api/oidio-batch/openmeteo/today/", oidio_batch_openmeteo_today_api, name="oidio_batch_openmeteo_today_api"),
    path("api/alerts/", alert_api, name="alert_api"),
    path("api/alerts/list/", alert_list_api, name="alert_list_api"),
    path("api/runs/", runs_api, name="runs_api"),
    path("api/runs/<int:run_id>/", run_detail_api, name="run_detail_api"),
    path("map/", map_page, name="map_page"),
    path("model/", model_page, name="model_page"),
    path("", map_page, name="map_page"),
    path("dashboard/", dashboard_page, name="dashboard_page_alias"),
]