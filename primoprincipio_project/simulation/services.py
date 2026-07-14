import random
from datetime import datetime, date, timedelta
import requests


def growth_rules(current_x):
    return [
        min(1.0, round(current_x + 0.1, 4)),
        min(1.0, round(current_x + 0.2, 4)),
        min(1.0, round(current_x + (1 - current_x) * 0.35, 4)),
    ]


def should_create_event(day):
    return (day["bagnatura"] == 1 and day["rain"] > 0) or (
        day["bagnatura"] == 1 and day["humidity"] > 80 and day["temperature"] > 15
    )


def update_events(previous_events):
    updated = []
    for event in previous_events:
        current_x = float(event["X"])

        if current_x >= 1.0:
            updated.append({"index": int(event["index"]), "X": 1.0})
            continue

        updated_x = random.choice(growth_rules(current_x))
        updated.append({"index": int(event["index"]), "X": updated_x})

    return updated


def process_single_day(day, previous_events=None):
    previous_events = previous_events or []
    updated = update_events(previous_events)
    next_index = 0 if not updated else max(ev["index"] for ev in updated) + 1

    if should_create_event(day):
        updated.append({"index": next_index, "X": 0.0})

    return {"doy": int(day["doy"]), "events": updated}


def run_problem1_blackbox(payload):
    day = {
        "doy": int(payload["doy"]),
        "temperature": float(payload["temperature"]),
        "bagnatura": int(payload["bagnatura"]),
        "humidity": float(payload["humidity"]),
        "rain": float(payload["rain"]),
    }
    previous_events = payload.get("events", [])
    return process_single_day(day, previous_events)


def derive_bagnatura(humidity, rain):
    return 1 if float(rain) > 0 or float(humidity) >= 80 else 0


def fetch_openmeteo_archive(lat, lon, start_date, end_date, timezone="Europe/Rome"):
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": [
            "temperature_2m_mean",
            "relative_humidity_2m_mean",
            "precipitation_sum",
        ],
        "start_date": start_date,
        "end_date": end_date,
        "timezone": timezone,
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_openmeteo_forecast(lat, lon, start_date, end_date, timezone="Europe/Rome"):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": [
            "temperature_2m_mean",
            "relative_humidity_2m_mean",
            "precipitation_sum",
        ],
        "start_date": start_date,
        "end_date": end_date,
        "timezone": timezone,
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def _build_days_from_daily_block(daily):
    times = daily.get("time", [])
    temperatures = daily.get("temperature_2m_mean", [])
    humidities = daily.get("relative_humidity_2m_mean", [])
    rains = daily.get("precipitation_sum", [])

    days = []

    for t, temp, hum, rain in zip(times, temperatures, humidities, rains):
        dt = datetime.strptime(t, "%Y-%m-%d").date()
        doy = dt.timetuple().tm_yday

        temperature = float(temp) if temp is not None else 0.0
        humidity = float(hum) if hum is not None else 0.0
        rain_value = float(rain) if rain is not None else 0.0

        days.append(
            {
                "doy": doy,
                "temperature": round(temperature, 2),
                "bagnatura": derive_bagnatura(humidity, rain_value),
                "humidity": round(humidity, 2),
                "rain": round(rain_value, 2),
            }
        )

    return days


def build_problem_days_from_openmeteo_archive(lat, lon, start_date, end_date, timezone="Europe/Rome"):
    data = fetch_openmeteo_archive(lat, lon, start_date, end_date, timezone=timezone)
    return _build_days_from_daily_block(data.get("daily", {}))


def build_problem_days_from_openmeteo_forecast(lat, lon, start_date, end_date, timezone="Europe/Rome"):
    data = fetch_openmeteo_forecast(lat, lon, start_date, end_date, timezone=timezone)
    return _build_days_from_daily_block(data.get("daily", {}))


def build_problem2_today_window(lat, lon, timezone="Europe/Rome", forecast_days=7):
    today = date.today()
    yesterday = today - timedelta(days=1)
    forecast_end = today + timedelta(days=forecast_days - 1)

    historical_days = build_problem_days_from_openmeteo_archive(
        lat=lat,
        lon=lon,
        start_date=yesterday.isoformat(),
        end_date=yesterday.isoformat(),
        timezone=timezone,
    )

    forecast_days_list = build_problem_days_from_openmeteo_forecast(
        lat=lat,
        lon=lon,
        start_date=today.isoformat(),
        end_date=forecast_end.isoformat(),
        timezone=timezone,
    )

    return historical_days + forecast_days_list