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
        if "code" in data:
            print(f"DEBUG: APOD API error {data.get('code')}: {data.get('msg', data)}")
            return ""
        media = data.get("media_type")
        if media != "image":
            print(f"DEBUG: APOD skipped — media_type is '{media}'")
            return ""
        title = data.get("title", "")
        words = data.get("explanation", "").split()
        explanation = " ".join(words[:120]) + ("..." if len(words) > 120 else "")
        print(f"DEBUG: APOD ok — {title}")
        return (
            f"<p class='math-hint'>NASA astronomy picture of the day</p>"
            f"<p><strong>{title}</strong></p>"
            f"<p>{explanation}</p>"
        )
    except Exception as e:
        print(f"DEBUG: APOD error: {e}")
        return ""
