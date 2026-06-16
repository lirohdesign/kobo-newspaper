import json
from datetime import datetime
from pathlib import Path


def collect_dayinhistory(today=None):
    if today is None:
        today = datetime.now()
    key = f"{today.month:02d}-{today.day:02d}"
    try:
        bank = json.loads(Path("dayinhistory_bank.json").read_text())
        events = bank.get(key, [])[:4]
        if not events:
            return ""
        items = "".join(
            f"<li><strong>{e['year']}</strong> — {e['text']}</li>"
            for e in events
        )
        return f"<ul class='otd-list'>{items}</ul>"
    except FileNotFoundError:
        print("DEBUG: dayinhistory_bank.json not found — run scrape_dayinhistory.py first")
        return ""
    except Exception as e:
        print(f"DEBUG: Day in history error: {e}")
        return ""
