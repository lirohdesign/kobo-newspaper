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


def _label_of(row):
    """Confirmed via a live raw-row dump (2026-09-12): CORN's harvest
    progress splits into GRAIN and SILAGE sub-series distinguished by
    util_practice_desc, not class_desc (which doesn't even appear in these
    rows — an earlier guess at the disambiguating field was wrong and
    caused a silent duplicate-label bug in production). Only surface the
    qualifier when it's not the generic 'ALL PRODUCTION PRACTICES' bucket
    that most stages (denting, dough, etc.) report under."""
    stage = row.get("unit_desc", "").replace("PCT ", "").title()
    practice = (row.get("util_practice_desc") or row.get("prodn_practice_desc") or "").strip()
    if practice and practice.upper() not in ("ALL PRODUCTION PRACTICES", "ALL UTILIZATION PRACTICES"):
        return f"{stage} ({practice.title()})"
    return stage


def _summarize(commodity, rows):
    """Returns (summary_text, week_ending) for the most recent reporting
    week that actually has data, or (None, None) if there's nothing usable
    (e.g. off-season)."""
    usable = [r for r in rows if r.get("end_code") and r.get("Value") not in (None, "", "(D)", "(NA)")]
    if not usable:
        return None, None

    latest_week = max(r["end_code"] for r in usable)
    latest_rows = [r for r in usable if r["end_code"] == latest_week]
    week_ending = latest_rows[0].get("week_ending", "")

    seen = set()
    parts = []
    for r in latest_rows:
        label = _label_of(r)
        key = (label, r["Value"])
        if key in seen:
            continue
        seen.add(key)
        parts.append(f"{label}: {r['Value']}%")

    if not parts:
        return None, None
    return f"Indiana {commodity.title()} as of week ending {week_ending}: " + ", ".join(parts) + ".", week_ending


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

        summary, week_ending = _summarize(commodity, rows)
        if not summary:
            print(f"DEBUG: nass_crop_progress — {commodity}: no current-season data (likely off-season)")
            continue

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
