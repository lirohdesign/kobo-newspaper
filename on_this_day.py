import re
import requests
from datetime import datetime

_HEADERS = {"User-Agent": "kobo-newspaper/1.0 (github.com/lirohdesign/kobo-newspaper)"}

_BLOCKLIST = {
    "killed", "kills", "kill", "killing",
    "bomb", "bombing", "bombed", "detonated", "explosion", "exploded",
    "attack", "attacked", "attacks", "attacking",
    "murder", "murdered", "murders",
    "assassination", "assassinated", "assassinate",
    "massacre", "genocide",
    "shooting", "gunfire",
    "died", "death", "deaths",
    "earthquake", "tsunami", "hurricane",
    "war", "battle", "invasion", "invaded",
    "terrorist", "terrorism",
    "injured", "injuring", "injuries",
    "wounded", "wounding",
    "riot", "riots",
    "lynched", "lynching",
    "hanged", "executed", "execution",
    "hostage", "kidnapped", "kidnapping",
    "suicide", "overdose",
}


def _kid_friendly(text):
    words = set(re.findall(r"\w+", text.lower()))
    return not words.intersection(_BLOCKLIST)


def collect_on_this_day(today=None):
    if today is None:
        today = datetime.now()
    try:
        r = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/selected/{today.month}/{today.day}",
            headers=_HEADERS,
            timeout=15
        )
        all_events = r.json().get("selected", [])
        events = [e for e in all_events if _kid_friendly(e.get("text", ""))][:3]
        print(f"DEBUG: On This Day — {len(all_events)} events, {len(events)} after filter")
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
