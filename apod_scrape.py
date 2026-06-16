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
        if r.status_code != 200:
            print(f"DEBUG: APOD HTTP {r.status_code}: {r.text[:200]}")
            return ""
        data = r.json()
        if "code" in data:
            print(f"DEBUG: APOD API error {data.get('code')}: {data.get('msg', data)}")
            return ""
        title = data.get("title", "")
        words = data.get("explanation", "").split()
        explanation = " ".join(words[:120]) + ("..." if len(words) > 120 else "")
        media = data.get("media_type")
        print(f"DEBUG: APOD ok — {title} ({media})")
        if media == "image":
            img_url = data.get("url", "")
            img_html = f"<img src='{img_url}' alt='{title}' class='apod-img'>" if img_url else ""
        else:
            img_html = ""
        return (
            f"<p class='math-hint'>NASA astronomy picture of the day</p>"
            f"<p><strong>{title}</strong></p>"
            f"{img_html}"
            f"<p>{explanation}</p>"
        )
    except Exception as e:
        print(f"DEBUG: APOD error: {e}")
        return ""
