"""USFS Forest Inventory and Analysis (FIA) — Indiana forest-health metrics,
via the FIADB-API EVALIDator "fullreport" endpoint (keyless JSON).

Endpoint (confirmed 2026-09-29, no API key required):
  https://apps.fs.usda.gov/fiadb-api/fullreport?rselected=State%20code
      &snum=<estimate id>&wc=<EVALID>&outputFormat=NJSON

  - wc is the EVALID: state FIPS + 4-digit evaluation year, so Indiana's
    2025 evaluation (annual panels 2019-2025) is 182025.
  - An unknown EVALID returns an HTML error page with HTTP 200, not JSON —
    so "latest evaluation" is found by probing years downward from the
    current year until a JSON estimate comes back.
  - Estimates used (snum): 2 forest land area (acres); 15 growing-stock net
    volume, forest land (cu ft); 214 average annual growing-stock mortality,
    forest land (cu ft/yr); 202 average annual net growth of growing stock,
    forest land (cu ft/yr). Mortality and growth need a growth-accounting
    evaluation (GROWTH_ACCT=Y in the wc table), which the annual Indiana
    evaluations are.

Ratios (mortality and net growth as a percent of standing volume) are
computed here from the agency's own estimates; sampling error (SE%) is
reported for mortality because it is the noisiest of the four.

Exposes fetch_items() in the shape research_pull.py expects. Links are
stamped per evaluation (#eval-<EVALID>) so the history ledger gains one
entry each time FIA publishes a new annual evaluation, and none on the
daily runs in between.
"""
import json
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = None

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
INDIANA_FIPS = "18"
API_URL = "https://apps.fs.usda.gov/fiadb-api/fullreport"
SITE_URL = "https://apps.fs.usda.gov/fiadb-api/evalidator"
SNUMS = {"area": 2, "volume": 15, "mortality": 214, "growth": 202}
MAX_PROBE_YEARS = 4


def _estimate(snum, evalid):
    """Indiana total for one estimate/evaluation, or None if the EVALID is
    unknown (HTML error page instead of JSON)."""
    url = f"{API_URL}?rselected=State%20code&snum={snum}&wc={evalid}&outputFormat=NJSON"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60, context=SSL_CONTEXT) as r:
        body = r.read()
    try:
        est = json.loads(body)["estimates"]
    except (ValueError, KeyError):
        return None
    if not est:
        return None
    return {"value": est[0]["ESTIMATE"], "se_pct": est[0].get("SE_PERCENT"), "plots": est[0].get("PLOT_COUNT")}


def _evaluation(year):
    """All four estimates for the Indiana evaluation of `year`, or None."""
    evalid = f"{INDIANA_FIPS}{year}"
    out = {"year": year, "evalid": evalid}
    for name, snum in SNUMS.items():
        est = _estimate(snum, evalid)
        if est is None:
            return None
        out[name] = est
    return out


def _latest_evaluation():
    year = datetime.now(timezone.utc).year
    for y in range(year, year - MAX_PROBE_YEARS, -1):
        ev = _evaluation(y)
        if ev:
            return ev
    return None


def _pct(part, whole):
    return 100.0 * part / whole


def _describe(cur, prior):
    vol = cur["volume"]["value"]
    mort = cur["mortality"]["value"]
    growth = cur["growth"]["value"]
    text = (
        f"Indiana FIA {cur['year']} evaluation: {cur['area']['value'] / 1e6:.2f}M acres of forest land, "
        f"{vol / 1e9:.2f}B cu ft growing-stock volume. Average annual growing-stock mortality "
        f"{mort / 1e6:.0f}M cu ft/yr ({_pct(mort, vol):.2f}% of standing volume; "
        f"SE {cur['mortality']['se_pct']:.1f}%), net growth {growth / 1e6:.0f}M cu ft/yr "
        f"({_pct(growth, vol):.2f}% of volume)"
    )
    if prior:
        p_rate = _pct(prior["mortality"]["value"], prior["volume"]["value"])
        c_rate = _pct(mort, vol)
        text += f". Mortality rate was {p_rate:.2f}% in the {prior['year']} evaluation ({c_rate - p_rate:+.2f} points)"
    return text + "."


def fetch_items():
    try:
        cur = _latest_evaluation()
        prior = _evaluation(cur["year"] - 1) if cur else None
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError) as e:
        print(f"DEBUG: fia_indiana fetch failed — {e}")
        return []

    if not cur:
        print("DEBUG: fia_indiana — no evaluation found in probe window")
        return []

    return [{
        "title": f"Indiana forest inventory — {cur['year']} evaluation (mortality, growth, volume)",
        "link": f"{SITE_URL}#eval-{cur['evalid']}",
        # The API carries no release date; the evaluation's reporting year is
        # the only date it gives, so use that year's end.
        "date": f"{cur['year']}-12-31",
        "summary": _describe(cur, prior),
        "content_links": [],
    }]


if __name__ == "__main__":
    for item in fetch_items():
        print(item["title"])
        print(item["link"], item["date"])
        print(item["summary"])
