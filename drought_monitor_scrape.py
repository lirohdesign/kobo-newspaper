"""US Drought Monitor — Indiana weekly classification, via the USDM data
service's structured JSON API (no RSS/feed available for this source).

API note: the `aoi` (area of interest) parameter takes a numeric FIPS code,
not the state abbreviation ("18" for Indiana, not "IN") — the abbreviated
form silently returns an empty list rather than an error. Confirmed
2026-09-12 against live data.

Exposes fetch_items() in the same shape research_pull.py expects from an
RSS source (title/link/date/summary/content_links), so it can flow through
the same history-ledger/validation pipeline as the feed-driven sources.
"""
import json
import ssl
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = None

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
INDIANA_FIPS = "18"
API_URL = "https://usdmdataservices.unl.edu/api/StateStatistics/GetDroughtSeverityStatisticsByAreaPercent"
SITE_URL = "https://droughtmonitor.unl.edu/CurrentMap/StateDroughtMonitor.aspx?IN"


def _fetch_weeks(weeks_back=8):
    start = (datetime.now(timezone.utc) - timedelta(weeks=weeks_back)).strftime("%-m/%-d/%Y")
    end = datetime.now(timezone.utc).strftime("%-m/%-d/%Y")
    url = f"{API_URL}?aoi={INDIANA_FIPS}&startdate={start}&enddate={end}&statisticsType=1"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20, context=SSL_CONTEXT) as r:
        data = json.loads(r.read())
    # API returns newest first; keep that order.
    return data


def _describe(current, prior):
    d0_plus = current["d0"] + current["d1"] + current["d2"] + current["d3"] + current["d4"]
    parts = [
        f"Indiana as of {current['mapDate'][:10]}: {current['none']:.1f}% no classification, "
        f"{current['d0']:.1f}% D0 (abnormally dry), {current['d1']:.1f}% D1 (moderate drought)"
    ]
    if current["d2"] or current["d3"] or current["d4"]:
        parts.append(f", {current['d2']:.1f}% D2, {current['d3']:.1f}% D3, {current['d4']:.1f}% D4")
    if prior:
        prior_d0_plus = prior["d0"] + prior["d1"] + prior["d2"] + prior["d3"] + prior["d4"]
        delta = d0_plus - prior_d0_plus
        direction = "up" if delta > 0.5 else ("down" if delta < -0.5 else "little changed")
        parts.append(f". Any-dryness coverage (D0+) is {direction} from {prior_d0_plus:.1f}% "
                      f"the week of {prior['mapDate'][:10]}")
    return "".join(parts) + "."


def fetch_items():
    try:
        weeks = _fetch_weeks()
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError) as e:
        print(f"DEBUG: drought_monitor fetch failed — {e}")
        return []

    if not weeks:
        print("DEBUG: drought_monitor — API returned no data")
        return []

    current = weeks[0]
    prior = next((w for w in weeks if w["mapDate"] < current["mapDate"]), None)
    # Prior-comparison target: closest available week to ~2 weeks back, not just weeks[1].
    two_weeks_ago_target = (datetime.fromisoformat(current["mapDate"]) - timedelta(weeks=2)).isoformat()
    two_weeks_prior = min(weeks, key=lambda w: abs(datetime.fromisoformat(w["mapDate"]).timestamp()
                                                    - datetime.fromisoformat(two_weeks_ago_target).timestamp()))

    return [{
        "title": f"Indiana Drought Monitor — week of {current['mapDate'][:10]}",
        "link": SITE_URL,
        "date": current["mapDate"],
        "summary": _describe(current, two_weeks_prior),
        "content_links": [],
    }]


if __name__ == "__main__":
    for item in fetch_items():
        print(item["title"])
        print(item["summary"])
