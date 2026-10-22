"""U.S. Press Freedom Tracker (Freedom of the Press Foundation) — incidents
against journalists, from its open API (CC BY 4.0). Reports are published
after verification; incidents often carry the journalist's own account.

Year-to-date counts by category, against the same span of the previous
year. 'Chilling Statement' is shown but left out of the headline total: a
former director has described inclusion in that category as editorial
judgement, so it is the tracker's interpretation, not an event (A1).
"""
import json
from collections import Counter
from datetime import datetime, timezone

from research_http import fetch, snapshot

API = "https://pressfreedomtracker.us/api/edge/incidents/?fields=date,categories&limit=5000"
PAGE_URL = "https://pressfreedomtracker.us/"
JUDGEMENT_CATEGORIES = {"Chilling Statement"}


def _incidents(lower, upper):
    body, _ = fetch(f"{API}&date_lower={lower}&date_upper={upper}", timeout=90)
    return json.loads(body)


def _headline(incidents):
    return sum(1 for i in incidents if set(i["categories"]) - JUDGEMENT_CATEGORIES)


def fetch_items():
    now = datetime.now(timezone.utc)
    date = now.strftime("%Y-%m-%d")
    this_year = _incidents(f"{now.year}-01-01", date)
    last_year = _incidents(f"{now.year - 1}-01-01", f"{now.year - 1}-{now:%m-%d}")
    if not this_year:
        print("DEBUG: press_freedom_tracker — API returned no incidents for this year")
        return []
    cats = Counter(c for i in this_year for c in i["categories"])
    latest = max(i["date"] for i in this_year)
    summary = (
        f"{_headline(this_year)} incidents Jan 1 to {now:%b %-d}, {now.year} excluding chilling statements "
        f"({_headline(last_year)} in the same span of {now.year - 1}); latest incident dated {latest}. "
        "By category: " + ", ".join(f"{k} {v}" for k, v in cats.most_common()) + "."
    )
    return [snapshot(f"Press Freedom Tracker year to date — {date}", PAGE_URL, date, summary)]


if __name__ == "__main__":
    for item in fetch_items():
        print(item["summary"])
