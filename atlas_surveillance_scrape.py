"""EFF Atlas of Surveillance — police surveillance technology by agency,
compiled from public records and news by EFF and University of Nevada,
Reno students and volunteers. Full dataset at download.csv (about 15,000
rows). Slow-moving: judge it on whether it would show a change, not on
week-to-week movement.

Counts by technology nationally and for Indiana.
"""
import csv
import io
from collections import Counter

from research_http import fetch, snapshot, today

CSV_URL = "https://atlasofsurveillance.org/download.csv"
PAGE_URL = "https://atlasofsurveillance.org/"


def fetch_items():
    body, _ = fetch(CSV_URL, timeout=120)
    rows = list(csv.DictReader(io.StringIO(body.decode("utf-8", errors="replace"))))
    if not rows:
        print("DEBUG: atlas_surveillance — CSV fetched but no rows")
        return []
    tech = Counter(r.get("Technology") or "Unknown" for r in rows)
    indiana = [r for r in rows if r.get("State") in ("IN", "Indiana")]
    in_tech = Counter(r.get("Technology") or "Unknown" for r in indiana)
    summary = (
        f"{len(rows)} records across {len({r.get('Agency') for r in rows})} agencies. "
        "Top technologies: " + ", ".join(f"{k} {v}" for k, v in tech.most_common(6))
        + f". Indiana: {len(indiana)} records; " + ", ".join(f"{k} {v}" for k, v in in_tech.most_common(4)) + "."
    )
    date = today()
    return [snapshot(f"Atlas of Surveillance — {date}", PAGE_URL, date, summary)]


if __name__ == "__main__":
    for item in fetch_items():
        print(item["summary"])
