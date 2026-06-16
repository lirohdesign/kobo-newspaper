"""
One-shot scraper: fetches all 365 days from Factmonster Day in History
and saves to dayinhistory_bank.json.

Run once locally:  python3 scrape_dayinhistory.py
Commit the resulting dayinhistory_bank.json to the repo.
Refresh annually or when content feels stale.
"""

import json
import re
import time
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.factmonster.com/dayinhistory"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
OUTPUT = "dayinhistory_bank.json"

MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]


def fetch_day(month_name, day):
    url = f"{BASE_URL}/{month_name}-{day}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            print(f"  HTTP {r.status_code}")
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        for ul in soup.find_all("ul"):
            texts = [li.get_text(separator=" ", strip=True) for li in ul.find_all("li")]
            year_items = [t for t in texts if re.match(r"^\d{4}", t)]
            if len(year_items) >= 3:
                events = []
                for t in year_items:
                    m = re.match(r"^(\d{4})\s*(.*)", t)
                    if m:
                        text = re.sub(r'\s+([.,;:!?])', r'\1', m.group(2)).strip()
                        events.append({"year": m.group(1), "text": text})
                return events
        print(f"  no event list found")
        return []
    except Exception as e:
        print(f"  error — {e}")
        return []


def main():
    bank = {}
    start = date(2025, 1, 1)
    for i in range(365):
        d = start + timedelta(days=i)
        key = f"{d.month:02d}-{d.day:02d}"
        month_name = MONTHS[d.month - 1]
        print(f"Fetching {month_name}-{d.day}...", end=" ", flush=True)
        events = fetch_day(month_name, d.day)
        bank[key] = events
        print(f"{len(events)} events")
        time.sleep(1.5)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(bank, f, indent=2, ensure_ascii=False)
    total = sum(len(v) for v in bank.values())
    print(f"\nDone — {total} events across 365 days saved to {OUTPUT}")


if __name__ == "__main__":
    main()
