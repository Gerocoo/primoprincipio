import requests

def fetch_history(lat, lon, start_date, end_date):
    return requests.get("https://archive-api.open-meteo.com/v1/archive", params={"latitude": lat, "longitude": lon, "hourly": "temperature_2m,relative_humidity_2m,precipitation", "start_date": start_date, "end_date": end_date, "timezone": "Europe/Rome"}, timeout=30).json()

def fetch_forecast(lat, lon, forecast_days=16):
    return requests.get("https://api.open-meteo.com/v1/forecast", params={"latitude": lat, "longitude": lon, "hourly": "temperature_2m,relative_humidity_2m,precipitation", "forecast_days": forecast_days, "timezone": "Europe/Rome"}, timeout=30).json()
