import os
from datetime import date, timedelta
from django.http import JsonResponse
from django.shortcuts import render
from .openmeteo import fetch_history, fetch_forecast
from .degree_days import hourly_to_daily_series
from .risk import classify, THRESHOLD
PIN_LAT = 45.657808639037725
PIN_LNG = 13.846673204128058

def demo_curve(s):
    if s == "green": return 70.0, [72,74,76,78,80,82,84,86,88,90]
    if s == "yellow": return 100.0, [101,102,103,104,105,107,109,111,113,115]
    if s == "red": return 130.0, [132,134,136,138,140,142,144,146,148,150]
    return None, None

def real_series():
    today = date.today()
    start = today.replace(month=1, day=1)
    hist = fetch_history(PIN_LAT, PIN_LNG, start.isoformat(), today.isoformat())
    fcast = fetch_forecast(PIN_LAT, PIN_LNG, 16)
    h = hourly_to_daily_series(hist.get("hourly", {}).get("time", []), hist.get("hourly", {}).get("temperature_2m", []))
    f = hourly_to_daily_series(fcast.get("hourly", {}).get("time", []), fcast.get("hourly", {}).get("temperature_2m", []))
    return h, f

def map_page(request):
    scenario = request.GET.get("scenario", "real")
    current_dd, future = demo_curve(scenario)
    if current_dd is None:
        hist, f = real_series()
        current_dd = hist[-1]["cumulative"] if hist else 0.0
        future = [x["cumulative"] for x in f]
    risk, label, action = classify(current_dd, [{"cumulative": x} for x in future])
    return render(request, "map.html", {"google_maps_api_key": os.getenv("GOOGLE_MAPS_API_KEY", ""), "pin_lat": PIN_LAT, "pin_lng": PIN_LNG, "current_dd": round(current_dd,1), "risk": risk, "label": label, "action": action, "threshold": THRESHOLD, "scenario": scenario})

def model_page(request):
    scenario = request.GET.get("scenario", "real")
    current_dd, future = demo_curve(scenario)
    if current_dd is None:
        hist, f = real_series()
        current_dd = hist[-1]["cumulative"] if hist else 0.0
        future = [x["cumulative"] for x in f]
    days = [{"date": (date.today() + timedelta(days=i)).isoformat(), "dd": current_dd if i == 0 else (future[i-1] if i-1 < len(future) else future[-1] if future else current_dd)} for i in range(max(1, len(future)+1))]
    return render(request, "model.html", {"current_dd": round(current_dd,1), "threshold": THRESHOLD, "days": days})

def degree_days_api(request):
    hist, f = real_series()
    return JsonResponse({"lat": PIN_LAT, "lng": PIN_LNG, "history": hist[:5], "forecast": f[:5]})

def problem1_api(request): return JsonResponse({"detail": "implement state machine API here"})
def problem2_api(request): return JsonResponse({"detail": "implement persistence and reconstruction here"})
