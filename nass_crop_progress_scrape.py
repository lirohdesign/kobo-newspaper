"""USDA NASS Quick Stats — weekly Crop Progress (Indiana corn & soybeans).

UNVERIFIED as of 2026-09-13: built against the documented Quick Stats API
schema (https://quickstats.nass.usda.gov/api), but there was no working
NASS_API_KEY available to test against live. Confirmed only that the
endpoint exists and returns the expected {"error": [...]} shape on a bad
key (401). Once NASS_API_KEY is set, run this standalone
(`python3 nass_crop_progress_scrape.py`) and sanity-check the output
against https://quickstats.nass.usda.gov/ before trusting it in the
pipeline — see CLAUDE.md's "don't trust a fix without looking" rule and
apply the same standard to a first-run source.

Only meaningful during the growing season (roughly April-November); off
-season the API will simply return no PROGRESS rows for the current year,
which fetch_items() treats as a normal empty result, not an error.
"""
import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = None

API_URL = "https://quickstats.nass.usda.gov/api/api_GET/"
SITE_URL = "https://quickstats.nass.usda.gov/"
STATE = "IN"
COMMODITIES = ["CORN", "SOYBEANS"]


def _query(key, commodity, year):
    params = {
        "key": key,
        "source_desc": "SURVEY",
        "sector_desc": "CROPS",
        "commodity_desc": commodity,
        "statisticcat_desc": "PROGRESS",
        "state_alpha": STATE,
        "year": year,
        "freq_desc": "WEEKLY",
        "format": "JSON",
    }
    url = API_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20, context=SSL_CONTEXT) as r:
        body = json.loads(r.read())
    return body.get("data", [])


def _summarize(commodity, rows):
    if not rows:
        return None
    latest_week = max(r["end_code"] for r in rows if r.get("end_code"))
    latest_rows = [r for r in rows if r.get("end_code") == latest_week]
    parts = [f"{r['unit_desc'].replace('PCT ', '').title()}: {r['Value']}%"
             for r in latest_rows if r.get("Value") not in (None, "", "(D)", "(NA)")]
    if not parts:
        return None
    week_ending = latest_rows[0].get("week_ending", "")
    return f"Indiana {commodity.title()} as of week ending {week_ending}: " + ", ".join(parts) + "."


def fetch_items():
    key = os.environ.get("NASS_API_KEY")
    if not key:
        print("DEBUG: nass_crop_progress — no NASS_API_KEY set, skipping")
        return []

    year = datetime.now(timezone.utc).year
    items = []
    for commodity in COMMODITIES:
        try:
            rows = _query(key, commodity, year)
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError) as e:
            print(f"DEBUG: nass_crop_progress — {commodity} fetch failed — {e}")
            continue

        summary = _summarize(commodity, rows)
        if not summary:
            print(f"DEBUG: nass_crop_progress — {commodity}: no current-season data (likely off-season)")
            continue

        week_ending = next((r.get("week_ending") for r in rows if r.get("Value") not in (None, "")), "")
        items.append({
            "title": f"Indiana {commodity.title()} Progress — week ending {week_ending}",
            "link": SITE_URL,
            "date": week_ending or str(year),
            "summary": summary,
            "content_links": [],
        })

    return items


if __name__ == "__main__":
    for item in fetch_items():
        print(item["title"])
        print(item["summary"])
