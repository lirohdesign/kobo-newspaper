import os
import requests

NWS_LAT = os.environ.get("NWS_LAT")
NWS_LON = os.environ.get("NWS_LON")

_HEADERS = {"User-Agent": "kobo-newspaper/1.0 (github.com/lirohdesign/kobo-newspaper)"}


def collect_kids_weather(ts):
    lat, lon = NWS_LAT, NWS_LON
    if not lat or not lon:
        print("DEBUG: Kids weather skipped — NWS_LAT/NWS_LON not set")
        return ""

    try:
        points_r = requests.get(
            f"https://api.weather.gov/points/{lat},{lon}",
            headers=_HEADERS, timeout=15
        )
        forecast_url = points_r.json()["properties"]["forecast"]

        forecast_r = requests.get(forecast_url, headers=_HEADERS, timeout=15)
        periods = forecast_r.json()["properties"]["periods"][:2]

        alerts_r = requests.get(
            f"https://api.weather.gov/alerts/active?point={lat},{lon}",
            headers=_HEADERS, timeout=15
        )
        alert_features = alerts_r.json().get("features", [])
    except Exception as e:
        print(f"DEBUG: Kids weather error: {e}")
        return ""

    period_html = []
    for period in periods:
        name = period.get("name", "")
        temp = period.get("temperature", "?")
        unit = period.get("temperatureUnit", "F")
        detail = period.get("detailedForecast", period.get("shortForecast", ""))
        precip_val = (period.get("probabilityOfPrecipitation") or {}).get("value") or 0
        rain_line = f"Rain chance: {precip_val}%." if precip_val else "No rain in the forecast."
        period_html.append(
            f"<p><strong>{name}:</strong> {detail} "
            f"<span class='math-hint'>{rain_line}</span></p>"
        )

    if alert_features:
        events = ", ".join(
            a["properties"].get("event", "Weather Alert") for a in alert_features[:2]
        )
        alert_html = f"<p class='weather-alert'><strong>Alert:</strong> {events}</p>"
    else:
        alert_html = "<p class='math-hint'>No weather alerts today.</p>"

    return "".join(period_html) + alert_html
