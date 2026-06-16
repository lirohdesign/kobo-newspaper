import os
import requests

NASA_API_KEY = os.environ.get("NASA_API_KEY", "DEMO_KEY")


def collect_apod():
    try:
        r = requests.get(
            "https://api.nasa.gov/planetary/apod",
            params={"api_key": NASA_API_KEY},
            timeout=15
        )
        data = r.json()
        if data.get("media_type") != "image":
            return ""
        title = data.get("title", "")
        words = data.get("explanation", "").split()
        explanation = " ".join(words[:120]) + ("..." if len(words) > 120 else "")
        return (
            f"<p class='math-hint'>NASA astronomy picture of the day</p>"
            f"<p><strong>{title}</strong></p>"
            f"<p>{explanation}</p>"
        )
    except Exception as e:
        print(f"DEBUG: APOD error: {e}")
        return ""
