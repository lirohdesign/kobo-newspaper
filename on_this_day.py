import requests
from datetime import datetime

_HEADERS = {"User-Agent": "kobo-newspaper/1.0 (github.com/lirohdesign/kobo-newspaper)"}


def collect_on_this_day(today=None):
    if today is None:
        today = datetime.now()
    try:
        r = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/selected/{today.month}/{today.day}",
            headers=_HEADERS,
            timeout=15
        )
        events = r.json().get("selected", [])[:3]
        if not events:
            return ""
        items = "".join(
            f"<li><strong>{e['year']}</strong> — {e['text']}</li>"
            for e in events
        )
        return f"<ul class='otd-list'>{items}</ul>"
    except Exception as e:
        print(f"DEBUG: On This Day error: {e}")
        return ""
