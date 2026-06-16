import os
import re
import time
import requests

NASA_API_KEY = os.environ.get("NASA_API_KEY", "DEMO_KEY")
API_URL = "https://api.nasa.gov/planetary/apod"
WEB_URL = "https://apod.nasa.gov/apod/astropix.html"
WEB_BASE = "https://apod.nasa.gov/apod/"


def _fetch_api(attempts=3):
    """Fetch APOD JSON from the API, retrying transient failures.

    api.nasa.gov is intermittently flaky — timeouts, 5xx, and 429 rate-limits
    (the last especially on shared GitHub Actions IPs). A single attempt drops
    the section on any blip, so retry those. A non-429 4xx won't fix itself, so
    bail immediately on those.
    """
    last = None
    for i in range(attempts):
        try:
            r = requests.get(
                API_URL,
                params={"api_key": NASA_API_KEY, "thumbs": "true"},
                timeout=20,
            )
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code}"
            print(f"DEBUG: APOD API {last} (try {i+1}/{attempts}): {r.text[:160]}")
            if r.status_code != 429 and r.status_code < 500:
                break
        except Exception as e:
            last = str(e)
            print(f"DEBUG: APOD API error (try {i+1}/{attempts}): {e}")
        if i < attempts - 1:
            time.sleep(2 * (i + 1))
    print(f"DEBUG: APOD API giving up — {last}")
    return None


def _parse_api(data):
    title = data.get("title", "")
    explanation = data.get("explanation", "")
    # Image days use the picture itself; video days fall back to the thumbnail
    # (requested via thumbs=true) so the section still carries an image.
    if data.get("media_type") == "image":
        img_url = data.get("url", "")
    else:
        img_url = data.get("thumbnail_url", "")
    return title, img_url, explanation


def _fetch_web():
    """Scrape the APOD website as a fallback.

    apod.nasa.gov (the plain HTML page) is far more reliable than the API host,
    so when the API is down this still gets the picture and blurb. The page
    layout has been stable for years: first <b> is the title, the image is the
    first image/… src, and the blurb follows 'Explanation:'.
    """
    try:
        r = requests.get(WEB_URL, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            print(f"DEBUG: APOD web HTTP {r.status_code}")
            return None
        return r.text
    except Exception as e:
        print(f"DEBUG: APOD web error: {e}")
        return None


def _parse_web(html):
    tm = re.search(r"<b>\s*(.*?)\s*</b>", html, re.IGNORECASE | re.DOTALL)
    title = re.sub(r"<[^>]+>", "", tm.group(1)).strip() if tm else "Astronomy Picture of the Day"

    im = re.search(r'<img\s+src="(image/[^"]+)"', html, re.IGNORECASE)
    img_url = WEB_BASE + im.group(1) if im else ""

    em = re.search(r"Explanation:\s*</b>(.*?)(?:<p>\s*<center>|<hr>)", html,
                   re.IGNORECASE | re.DOTALL)
    explanation = ""
    if em:
        explanation = re.sub(r"<[^>]+>", "", em.group(1))
        explanation = re.sub(r"\s+", " ", explanation).strip()
    return title, img_url, explanation


def _render(title, img_url, explanation):
    # The API's explanation field sometimes over-captures trailing page nav;
    # cut it at the known markers so the blurb ends cleanly.
    explanation = re.split(r"\s*(?:Explore the Universe:|Tomorrow's picture:)",
                           explanation)[0].strip()
    words = explanation.split()
    explanation = " ".join(words[:120]) + ("..." if len(words) > 120 else "")
    img_html = f"<img src='{img_url}' alt='{title}' class='apod-img'>" if img_url else ""
    return (
        f"<p class='math-hint'>NASA astronomy picture of the day</p>"
        f"<p><strong>{title}</strong></p>"
        f"{img_html}"
        f"<p>{explanation}</p>"
    )


def collect_apod():
    data = _fetch_api()
    if data and "code" not in data:
        title, img_url, explanation = _parse_api(data)
        print(f"DEBUG: APOD ok via API — {title}")
        return _render(title, img_url, explanation)
    if data and "code" in data:
        print(f"DEBUG: APOD API error {data.get('code')}: {data.get('msg', data)}")

    # API unavailable — fall back to the website
    html = _fetch_web()
    if html:
        title, img_url, explanation = _parse_web(html)
        print(f"DEBUG: APOD ok via web fallback — {title}")
        return _render(title, img_url, explanation)

    return ""
