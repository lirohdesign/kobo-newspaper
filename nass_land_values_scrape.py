"""USDA NASS Quick Stats — annual Land Values & Cash Rents (Indiana),
calendar-triggered for the research_calendar.json 'nass_land_values' event
(released the first week of August; county cash rents late August).

Exposes collect() -> HTML string, matching the calendar.json scraper
convention (see barometer_scrape.py), not fetch_items() like the weekly
research_sources.json scrapers — this is invoked by main.py's
_run_scraper/collect_calendar path, not research_pull.py.

UNVERIFIED LIVE as of 2026-09-12: reuses the same Quick Stats API
(quickstats.nass.usda.gov/api) and NASS_API_KEY already proven working in
nass_crop_progress_scrape.py, but there was no key available in this local
session to test the LAND VALUES / CASH RENTS query params specifically
against live data. nass_crop_progress_scrape.py's own history is the reason
to be cautious here: a first guess at the disambiguating field
(class_desc) was wrong and silently produced duplicate/mislabeled output
until checked against a live raw-row dump. Before trusting this in
production, run it standalone in early August (`python3
nass_land_values_scrape.py`) with NASS_API_KEY set and compare the output
against https://quickstats.nass.usda.gov/ directly.
"""
import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = None

API_URL = "https://quickstats.nass.usda.gov/api/api_GET/"
SITE_URL = "https://quickstats.nass.usda.gov/"
STATE = "IN"

# Two separate Quick Stats query shapes — land asset value and cash rent
# are different commodity/category combinations, not two rows of the same
# query. Params below follow NASS's documented category codes; unverified
# against a live response (see module docstring).
QUERIES = [
    {
        "label": "Indiana Farm Real Estate Value",
        "params": {"commodity_desc": "AG LAND", "statisticcat_desc": "ASSET VALUE",
                   "unit_desc": "$ / ACRE", "agg_level_desc": "STATE"},
    },
    {
        "label": "Indiana Cropland Cash Rent",
        "params": {"commodity_desc": "RENT", "statisticcat_desc": "RENT, CASH, CROPLAND",
                   "unit_desc": "$ / ACRE", "agg_level_desc": "STATE"},
    },
]


def _query(key, extra_params, year):
    params = {
        "key": key,
        "source_desc": "SURVEY",
        "sector_desc": "ECONOMICS",
        "state_alpha": STATE,
        "year": year,
        "format": "JSON",
    }
    params.update(extra_params)
    url = API_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20, context=SSL_CONTEXT) as r:
        body = json.loads(r.read())
    return body.get("data", [])


def collect():
    key = os.environ.get("NASS_API_KEY")
    if not key:
        print("DEBUG: nass_land_values — no NASS_API_KEY set, skipping")
        return ""

    year = datetime.now(timezone.utc).year
    parts = []
    for q in QUERIES:
        try:
            rows = _query(key, q["params"], year)
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError) as e:
            print(f"DEBUG: nass_land_values — {q['label']} fetch failed — {e}")
            continue
        if not rows:
            # Try prior year — the current year's August release may not
            # have posted yet depending on exactly when this runs.
            try:
                rows = _query(key, q["params"], year - 1)
            except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError):
                rows = []
        usable = [r for r in rows if r.get("Value") not in (None, "", "(D)", "(NA)")]
        if not usable:
            print(f"DEBUG: nass_land_values — {q['label']}: no usable rows")
            continue
        latest = max(usable, key=lambda r: r.get("year", "0"))
        parts.append(f"<p><strong>{q['label']} ({latest.get('year')})</strong>: ${latest['Value']}/acre</p>")

    if not parts:
        return ""
    print("DEBUG: nass_land_values — OK")
    return (
        f"<p class='metadata'><a href='{SITE_URL}'>USDA NASS Quick Stats</a></p>"
        + "\n".join(parts)
    )


if __name__ == "__main__":
    print(collect())
