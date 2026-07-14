import logging
from datetime import date, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Count
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import ModelRun, EventSnapshot, AlertThreshold
from .services import (
    run_problem1_blackbox,
    build_problem_days_from_openmeteo_archive,
    build_problem_days_from_openmeteo_forecast,
    build_problem2_today_window,
)


logger = logging.getLogger(__name__)


PIN_LAT = 45.657808639037725
PIN_LNG = 13.846673204128058
DEFAULT_SORDIDUS_THRESHOLD = 106.8


def real_degree_days_series(lat, lon):
    today = date.today()
    start = today.replace(month=1, day=1)
    yesterday = today - timedelta(days=1)

    hist_days = build_problem_days_from_openmeteo_archive(
        lat=lat,
        lon=lon,
        start_date=start.isoformat(),
        end_date=yesterday.isoformat(),
    )

    forecast_days = build_problem_days_from_openmeteo_forecast(
        lat=lat,
        lon=lon,
        start_date=today.isoformat(),
        end_date=(today + timedelta(days=15)).isoformat(),
    )

    cumulative = 0.0
    series = []
    seen_doys = set()

    for day in hist_days + forecast_days:
        doy = int(day["doy"])
        if doy in seen_doys:
            continue
        seen_doys.add(doy)

        dd = max(0.0, float(day["temperature"]) - 8.0)
        cumulative += dd
        series.append({
            "doy": doy,
            "degree_day": round(cumulative, 2),
        })

    return series


def degree_days_from_input_days(days, threshold=8.0):
    cumulative = 0.0
    series = []
    for day in days:
        dd = max(0.0, float(day["temperature"]) - threshold)
        cumulative += dd
        series.append({"doy": int(day["doy"]), "degree_day": round(cumulative, 2)})
    return series


def risk_from_degree_days(series, threshold):
    current = series[-1]["degree_day"] if series else 0.0
    next_10 = series[-10:] if len(series) >= 10 else series
    will_exceed = any(item["degree_day"] > threshold for item in next_10)

    if current > threshold:
        return {"level": "alto", "color": "red", "action": "AGISCI"}
    if will_exceed:
        return {"level": "medio", "color": "yellow", "action": "SVEGLIATI"}
    return {"level": "assente", "color": "green", "action": "DORMI"}


def serialize_alert(alert):
    return {
        "id": alert.id,
        "threshold": alert.threshold,
        "email": alert.email,
        "active": alert.active,
        "last_triggered_doy": alert.last_triggered_doy,
    }


def send_threshold_email(alert, current, connection=None):
    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    send_mail(
        subject=f"Allarme {alert.threshold}",
        message=(
            f"Timestamp superamento soglia: {timestamp}\n"
            f"Valore soglia impostata: {alert.threshold}\n"
            f"Valore Gradi Giorno al momento del superamento: {current['degree_day']}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[alert.email],
        fail_silently=False,
        connection=connection,
    )


def trigger_alerts_if_needed(series):
    if not series:
        return []

    current = series[-1]
    triggered = []

    for alert in AlertThreshold.objects.filter(active=True):
        if current["degree_day"] >= alert.threshold and alert.last_triggered_doy != current["doy"]:
            try:
                send_threshold_email(alert, current)
            except Exception:
                logger.exception("Invio email fallito per allarme id=%s", alert.id)
                continue

            alert.last_triggered_doy = current["doy"]
            alert.save(update_fields=["last_triggered_doy"])
            triggered.append(serialize_alert(alert))

    return triggered


@transaction.atomic
def run_batch_and_persist(days, initial_events=None):
    initial_events = initial_events or []

    all_outputs = []
    current_events = initial_events

    run = ModelRun.objects.create(
        run_date=date.today(),
        first_doy=int(days[0]["doy"]),
        last_doy=int(days[-1]["doy"]),
    )

    for day in days:
        day_payload = {
            "doy": day["doy"],
            "temperature": day["temperature"],
            "bagnatura": day["bagnatura"],
            "humidity": day["humidity"],
            "rain": day["rain"],
            "events": current_events,
        }

        output = run_problem1_blackbox(day_payload)
        current_events = output["events"]
        all_outputs.append(output)

        for event in current_events:
            EventSnapshot.objects.update_or_create(
                run=run,
                doy=output["doy"],
                event_index=event["index"],
                defaults={"x_value": event["X"]},
            )

    degree_days = degree_days_from_input_days(days)
    risk = risk_from_degree_days(degree_days, DEFAULT_SORDIDUS_THRESHOLD)
    triggered = trigger_alerts_if_needed(degree_days)

    return {
        "run_id": run.id,
        "outputs": all_outputs,
        "degree_days": degree_days,
        "risk": risk,
        "threshold": DEFAULT_SORDIDUS_THRESHOLD,
        "alerts_triggered": triggered,
    }


@api_view(["POST"])
def simulation_api(request):
    payload = request.data
    required = ["doy", "temperature", "bagnatura", "humidity", "rain"]
    missing = [field for field in required if field not in payload]
    if missing:
        return Response({"error": f"Missing fields: {', '.join(missing)}"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = run_problem1_blackbox(payload)
    except Exception:
        logger.exception("Errore in run_problem1_blackbox")
        return Response({"error": "Errore durante l'esecuzione del modello"}, status=status.HTTP_502_BAD_GATEWAY)

    return Response(result, status=status.HTTP_200_OK)


@api_view(["POST"])
def oidio_batch_api(request):
    payload = request.data
    days = payload.get("days", [])
    initial_events = payload.get("events", [])

    if not isinstance(days, list) or not days:
        return Response({"error": "days is required"}, status=status.HTTP_400_BAD_REQUEST)

    for day in days:
        for field in ["doy", "temperature", "bagnatura", "humidity", "rain"]:
            if field not in day:
                return Response(
                    {"error": f"Missing field in days item: {field}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

    try:
        result = run_batch_and_persist(days, initial_events=initial_events)
    except Exception:
        logger.exception("Errore in run_batch_and_persist (oidio_batch_api)")
        return Response({"error": "Errore durante l'elaborazione del batch"}, status=status.HTTP_502_BAD_GATEWAY)

    return Response(result, status=status.HTTP_200_OK)


@api_view(["POST"])
def oidio_batch_openmeteo_today_api(request):
    payload = request.data

    try:
        lat = float(payload.get("lat", PIN_LAT))
        lon = float(payload.get("lon", PIN_LNG))
    except (TypeError, ValueError):
        return Response({"error": "lat/lon non validi"}, status=status.HTTP_400_BAD_REQUEST)

    events = payload.get("events")

    if events is None:
        return Response(
            {
                "error": (
                    "events is required. "
                    "Pass the model state of the day before the first input day, "
                    "as required by Problem 2."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        days = build_problem2_today_window(lat=lat, lon=lon, forecast_days=7)
    except Exception as e:
        logger.exception("Open-Meteo fetch fallito")
        return Response(
            {"error": f"Open-Meteo fetch failed: {str(e)}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if not days:
        return Response(
            {"error": "No meteorological data returned by Open-Meteo"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        result = run_batch_and_persist(days, initial_events=events)
    except Exception:
        logger.exception("Errore in run_batch_and_persist (oidio_batch_openmeteo_today_api)")
        return Response({"error": "Errore durante l'elaborazione del batch"}, status=status.HTTP_502_BAD_GATEWAY)

    result["source"] = "open-meteo-problem2-today-window"
    result["days"] = days
    result["input_contract"] = {
        "historical_days": 1,
        "forecast_days": 7,
        "requires_previous_events_state": True,
    }

    return Response(result, status=status.HTTP_200_OK)


@api_view(["GET"])
def runs_api(request):
    runs = (
        ModelRun.objects.all()
        .order_by("-created_at")
        .annotate(snapshot_count=Count("snapshots"))
    )

    data = [
        {
            "id": run.id,
            "run_date": run.run_date.isoformat(),
            "first_doy": run.first_doy,
            "last_doy": run.last_doy,
            "created_at": run.created_at.isoformat(),
            "snapshot_count": run.snapshot_count,
        }
        for run in runs
    ]
    return Response(data)


@api_view(["GET"])
def run_detail_api(request, run_id):
    try:
        run = ModelRun.objects.get(pk=run_id)
    except ModelRun.DoesNotExist:
        raise Http404("Run not found")

    snapshots = EventSnapshot.objects.filter(run=run).order_by("doy", "event_index")

    snapshot_rows = [
        {
            "doy": s.doy,
            "event_index": s.event_index,
            "x_value": s.x_value,
            "created_at": s.created_at.isoformat(),
        }
        for s in snapshots
    ]

    doys = sorted({row["doy"] for row in snapshot_rows})
    event_indexes = sorted({row["event_index"] for row in snapshot_rows})

    event_series = []
    for event_index in event_indexes:
        values_by_doy = {
            row["doy"]: row["x_value"]
            for row in snapshot_rows
            if row["event_index"] == event_index
        }
        event_series.append(
            {
                "event_index": event_index,
                "points": [
                    {"doy": doy, "x_value": values_by_doy.get(doy)}
                    for doy in doys
                ],
            }
        )

    summary_by_day = []
    for doy in doys:
        day_snapshots = [r for r in snapshot_rows if r["doy"] == doy]
        active_events = len(day_snapshots)
        matured_events = len([r for r in day_snapshots if float(r["x_value"]) >= 1.0])
        mean_x = round(sum(float(r["x_value"]) for r in day_snapshots) / active_events, 4) if active_events else 0.0

        summary_by_day.append(
            {
                "doy": doy,
                "active_events": active_events,
                "matured_events": matured_events,
                "mean_x": mean_x,
            }
        )

    return Response(
        {
            "run": {
                "id": run.id,
                "run_date": run.run_date.isoformat(),
                "first_doy": run.first_doy,
                "last_doy": run.last_doy,
                "created_at": run.created_at.isoformat(),
            },
            "snapshots": snapshot_rows,
            "event_series": event_series,
            "summary_by_day": summary_by_day,
        }
    )


def dashboard_page(request):
    return render(request, "dashboard.html")


def _get_all_alerts_serialized():
    return [serialize_alert(a) for a in AlertThreshold.objects.all().order_by("-created_at")]


@api_view(["GET", "POST", "PATCH", "DELETE"])
def alert_api(request):
    if request.method == "GET":
        alert_id = request.GET.get("id")
        if alert_id:
            try:
                alert = AlertThreshold.objects.get(pk=alert_id)
            except (AlertThreshold.DoesNotExist, ValueError):
                raise Http404("Alert not found")
            return Response(serialize_alert(alert))

        return Response(_get_all_alerts_serialized())

    if request.method == "POST":
        try:
            threshold = float(request.data["threshold"])
            email = request.data["email"]
        except (KeyError, TypeError, ValueError):
            return Response(
                {"error": "threshold (numero) e email sono richiesti"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_email(email)
        except ValidationError:
            return Response({"error": "email non valida"}, status=status.HTTP_400_BAD_REQUEST)

        alert = AlertThreshold.objects.create(
            threshold=threshold,
            email=email,
            active=True,
        )

        degree_days = real_degree_days_series(PIN_LAT, PIN_LNG)
        if degree_days:
            current = degree_days[-1]
            if current["degree_day"] >= alert.threshold:
                try:
                    send_threshold_email(alert, current)
                except Exception:
                    logger.exception("Invio email fallito per nuovo allarme id=%s", alert.id)
                else:
                    alert.last_triggered_doy = current["doy"]
                    alert.save(update_fields=["last_triggered_doy"])

        return Response(serialize_alert(alert), status=status.HTTP_201_CREATED)

    if request.method == "PATCH":
        alert_id = request.data.get("id")
        if not alert_id:
            return Response({"error": "id richiesto"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            alert = AlertThreshold.objects.get(pk=alert_id)
        except (AlertThreshold.DoesNotExist, ValueError):
            raise Http404("Alert not found")

        was_active = alert.active

        if "active" in request.data:
            alert.active = bool(request.data["active"])

        if "threshold" in request.data:
            try:
                alert.threshold = float(request.data["threshold"])
            except (TypeError, ValueError):
                return Response({"error": "threshold non valido"}, status=status.HTTP_400_BAD_REQUEST)

        if "email" in request.data:
            new_email = request.data["email"]
            try:
                validate_email(new_email)
            except ValidationError:
                return Response({"error": "email non valida"}, status=status.HTTP_400_BAD_REQUEST)
            alert.email = new_email

        just_deactivated = was_active is True and alert.active is False
        if just_deactivated:
            alert.last_triggered_doy = None

        alert.save()

        just_reactivated = was_active is False and alert.active is True
        if just_reactivated:
            degree_days = real_degree_days_series(PIN_LAT, PIN_LNG)
            if degree_days:
                current = degree_days[-1]
                if current["degree_day"] >= alert.threshold and alert.last_triggered_doy != current["doy"]:
                    try:
                        send_threshold_email(alert, current)
                    except Exception:
                        logger.exception("Invio email fallito per riattivazione allarme id=%s", alert.id)
                    else:
                        alert.last_triggered_doy = current["doy"]
                        alert.save(update_fields=["last_triggered_doy"])

        return Response(serialize_alert(alert))

    # DELETE
    alert_id = request.data.get("id")
    if not alert_id:
        return Response({"error": "id richiesto"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        alert = AlertThreshold.objects.get(pk=alert_id)
    except (AlertThreshold.DoesNotExist, ValueError):
        raise Http404("Alert not found")

    if alert.active:
        return Response({"error": "Disattivare la soglia prima di cancellarla"}, status=status.HTTP_400_BAD_REQUEST)

    alert.delete()
    return Response({"deleted": True})


@api_view(["GET"])
def alert_list_api(request):
    return Response(_get_all_alerts_serialized())


def map_page(request):
    degree_days = real_degree_days_series(PIN_LAT, PIN_LNG)
    risk = risk_from_degree_days(degree_days, DEFAULT_SORDIDUS_THRESHOLD)

    context = {
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
        "pin_lat": PIN_LAT,
        "pin_lng": PIN_LNG,
        "risk": risk,
        "current_dd": degree_days[-1]["degree_day"] if degree_days else 0.0,
        "threshold": DEFAULT_SORDIDUS_THRESHOLD,
    }
    return render(request, "map.html", context)


def model_page(request):
    degree_days = real_degree_days_series(PIN_LAT, PIN_LNG)
    risk = risk_from_degree_days(degree_days, DEFAULT_SORDIDUS_THRESHOLD)
    trigger_alerts_if_needed(degree_days)

    context = {
        "degree_days": degree_days,
        "threshold": DEFAULT_SORDIDUS_THRESHOLD,
        "risk": risk,
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
    }
    return render(request, "model.html", context)