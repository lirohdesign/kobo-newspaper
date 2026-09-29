"""Epoch AI — AI data centers hub (global). Keyless CSV, CC-BY (credit Epoch
AI). Expert-built estimates of power, compute and cost for the world's
largest AI data centers from satellite imagery, permits and filings.

Endpoint: https://epoch.ai/data/data_centers/data_centers.csv (one row per
site, `Country` and `Address` columns). The hub page carries "Updated <date>"
text, read here for the dataset's own vintage.

Snapshot, not a feed: fetch_items() emits one dated summary per pull (sites,
total current power, H100-equivalents, split by country, Indiana sites) with
a date-fragmented link so the history ledger
(research_data/history/epoch_datacenters.jsonl) accumulates a series. An
unchanged dataset vintage across pulls is normal (Epoch updates roughly
weekly to monthly), not a failure.

Caveat kept in the summary: coverage is Epoch's selection of large sites
(the hub reports ~44% of global AI compute), skewed to the US, so shares
are shares of the covered set, not of world capacity.
"""
import csv
import io
import re
import ssl
import urllib.request
import urllib.error
from collections import defaultdict
from datetime import datetime, timezone

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = None

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
CSV_URL = "https://epoch.ai/data/data_centers/data_centers.csv"
PAGE_URL = "https://epoch.ai/data/ai-data-centers"
UPDATED_RE = re.compile(r"Updated ([A-Z][a-z]{2})\.? (\d{1,2}), (\d{4})")
INDIANA_RE = re.compile(r",\s*IN\s+\d{5}|,\s*Indiana\b")


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as r:
        return r.read().decode("utf-8-sig", errors="replace")


def _num(s):
    try:
        return float((s or "").strip() or 0)
    except ValueError:
        return 0.0


def _dataset_vintage():
    """Epoch's own 'Updated <date>' as YYYY-MM-DD, or None. Best-effort:
    a page change here must not sink the pull."""
    try:
        m = UPDATED_RE.search(_get(PAGE_URL))
        if m:
            return datetime.strptime(" ".join(m.groups()), "%b %d %Y").strftime("%Y-%m-%d")
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError):
        pass
    return None


def _summarize(rows, vintage):
    power_col, chip_col = "Current power (MW)", "Current H100 equivalents"
    if not rows or power_col not in rows[0] or chip_col not in rows[0]:
        raise ValueError("CSV columns changed — expected Current power (MW) / Current H100 equivalents")
    total_mw = sum(_num(r[power_col]) for r in rows)
    total_h = sum(_num(r[chip_col]) for r in rows)
    by_country = defaultdict(float)
    for r in rows:
        by_country[(r.get("Country") or "Unknown").strip() or "Unknown"] += _num(r[power_col])
    ranked = sorted(by_country.items(), key=lambda kv: -kv[1])
    operating = sum(1 for r in rows if _num(r[power_col]) > 0)
    countries = ", ".join(
        f"{c} {mw / 1000:.2f} GW ({100 * mw / total_mw:.0f}%)" for c, mw in ranked[:4] if mw > 0
    )
    text = (
        f"Epoch AI covers {len(rows)} large AI data centers ({operating} drawing power now): "
        f"{total_mw / 1000:.1f} GW current power, {total_h / 1e6:.1f}M H100-equivalents, "
        f"{sum(1 for c, mw in by_country.items() if mw > 0)} countries with capacity. By power: {countries}."
    )
    ind = [r for r in rows if INDIANA_RE.search(r.get("Address") or "")]
    if ind and total_mw:
        ind_mw = sum(_num(r[power_col]) for r in ind)
        names = ", ".join(f"{r['Name']} ({_num(r[power_col]):.0f} MW)" for r in ind)
        text += (
            f" Indiana: {len(ind)} sites, {ind_mw / 1000:.2f} GW = "
            f"{100 * ind_mw / total_mw:.1f}% of the covered global total ({names})."
        )
    text += " Covered set only, not world capacity; skewed to the US."
    if vintage:
        text += f" Dataset updated {vintage}."
    return text


def fetch_items():
    try:
        rows = list(csv.DictReader(io.StringIO(_get(CSV_URL))))
        summary = _summarize(rows, _dataset_vintage())
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError, OSError) as e:
        print(f"DEBUG: epoch_datacenters fetch failed — {e}")
        return []

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return [{
        "title": f"Epoch AI data centers (global) — {today}",
        "link": f"{PAGE_URL}#snapshot-{today}",
        "date": today,
        "summary": summary,
        "content_links": [],
    }]


if __name__ == "__main__":
    for item in fetch_items():
        print(item["title"])
        print(item["summary"])
