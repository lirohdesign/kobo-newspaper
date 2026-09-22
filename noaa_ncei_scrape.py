"""NOAA NCEI monthly climate summary — Indiana, via the CDO (Climate Data
Online) API v2 GSOM (Global Summary of the Month) dataset.

Verified live 2026-09-15 (temperatures) and 2026-09-22 (precipitation,
after adding pagination — see _query).

API notes (from NOAA's own CDO documentation, not yet confirmed against a
live response):
  - Auth is a `token` HTTP header, not a query param.
  - locationid for a whole state is `FIPS:<2-digit code>` (Indiana = 18,
    Michigan = 26) — same FIPS-not-abbreviation gotcha already confirmed
    for the Drought Monitor API in drought_monitor_scrape.py; using that
    same code here on the assumption it generalizes, not because this
    endpoint has been separately confirmed to need it.
  - GSOM datasetid gives one record per station per month; TMAX/TMIN/PRCP
    are the datatypeids of interest for a temperature/precip summary.
  - CDO data lags roughly 1-3 months behind the current date (stations
    report on a delay), so "most recent available month" is usually not
    the current calendar month — fetch_items() reports whatever the latest
    available month actually is rather than assuming today's month.
"""
import json
import ssl
import os
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = None

API_BASE = "https://www.ncdc.noaa.gov/cdo-web/api/v2/data"
SITE_URL = "https://www.ncei.noaa.gov/access/monitoring/monthly-report/"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# state label -> FIPS code, mirroring the pattern already confirmed for
# drought_monitor_scrape.py's Indiana lookup.
STATES = {"Indiana": "18", "Michigan": "26"}
DATATYPES = ["TAVG", "TMAX", "TMIN", "PRCP"]
UNITS = {"TAVG": "°F", "TMAX": "°F", "TMIN": "°F", "PRCP": "in"}


def _query(token, state_fips, datatype, start, end):
    """One datatype per call, not all four combined. Confirmed live
    2026-09-15: combining datatypeid=[TAVG,TMAX,TMIN,PRCP] in a single
    request hits the CDO API's 1000-row-per-request cap before reaching
    the temperature types — NOAA appears to return rows ordered such that
    PRCP/precip-derived types (DP01, DP10, EMXP, ...) fill the cap first,
    alphabetically ahead of T*. Four separate single-datatype requests
    each stay comfortably under the cap instead of silently losing data.

    Even one datatype can exceed it: PRCP has far more reporting stations
    than temperature (Indiana: 2,045 rows over 150 days vs 304 for TAVG,
    confirmed live 2026-09-22), and rows come back oldest-first, so the
    first page held only May-June and the latest month was silently lost.
    Pages via `offset` until the reported resultset count is reached."""
    params = {
        "datasetid": "GSOM",
        "locationid": f"FIPS:{state_fips}",
        "datatypeid": datatype,
        "startdate": start,
        "enddate": end,
        "units": "standard",
        "limit": 1000,
    }
    rows = []
    while True:
        params["offset"] = len(rows) + 1  # CDO offsets are 1-based
        url = API_BASE + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"token": token, "User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=20, context=SSL_CONTEXT) as r:
            body = json.loads(r.read())
        page = body.get("results", [])
        rows.extend(page)
        total = body.get("metadata", {}).get("resultset", {}).get("count", 0)
        if not page or len(rows) >= total:
            return rows


def _summarize(state, rows):
    """Average each datatype across all reporting stations in the state for
    the most recent month present, since GSOM returns one row per station
    per month, not a pre-aggregated state value."""
    if not rows:
        return None, None

    by_month = defaultdict(list)
    for r in rows:
        by_month[r["date"][:7]].append(r)  # "YYYY-MM"

    latest_month = max(by_month)
    latest_rows = by_month[latest_month]

    by_type = defaultdict(list)
    for r in latest_rows:
        by_type[r["datatype"]].append(r["value"])

    parts = []
    for dt in DATATYPES:
        vals = by_type.get(dt)
        if not vals:
            continue
        avg = sum(vals) / len(vals)
        label = {"TAVG": "Avg temp", "TMAX": "Avg high", "TMIN": "Avg low", "PRCP": "Total precip"}[dt]
        parts.append(f"{label}: {avg:.1f}{UNITS[dt]}")

    if not parts:
        return None, None
    return f"{state} climate summary, {latest_month} (station-average, {len(latest_rows)} station-months): " + ", ".join(parts) + ".", latest_month


def fetch_items():
    token = os.environ.get("NOAA_TOKEN")
    if not token:
        print("DEBUG: noaa_ncei — no NOAA_TOKEN set, skipping")
        return []

    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=150)  # generous window given GSOM's reporting lag
    items = []
    for state, fips in STATES.items():
        rows = []
        try:
            for datatype in DATATYPES:
                rows.extend(_query(token, fips, datatype, start.isoformat(), end.isoformat()))
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError) as e:
            print(f"DEBUG: noaa_ncei — {state} fetch failed — {e}")
            continue

        summary, month = _summarize(state, rows)
        if not summary:
            print(f"DEBUG: noaa_ncei — {state}: no usable GSOM rows in window")
            continue

        items.append({
            "title": f"{state} Monthly Climate Summary — {month}",
            "link": SITE_URL,
            "date": month or start.isoformat(),
            "summary": summary,
            "content_links": [],
        })

    return items


if __name__ == "__main__":
    for item in fetch_items():
        print(item["title"])
        print(item["summary"])
