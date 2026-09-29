"""interconnection.fyi — national data-center tracker, the benchmark beside
the Indiana scrape (interconnection_fyi_scrape.py). Same __NEXT_DATA__
approach and same date-fragmented link, so the history ledger
(research_data/history/interconnection_fyi_national.jsonl) accumulates one
national snapshot per day.

The landing page (/data-center) embeds national status counts and the list
of state codes, but no per-state counts. Those come from the 48 state pages
(/data-center/state/<XX>, ~0.3s each, up to ~1MB for TX), fetched once per
pull. The tracker includes two Canadian provinces (AB, ON); they are counted
in the tracker's own total but excluded from the US state ranking.

fetch_items() emits one dated item: national counts by status, the top
states by active pipeline (Proposed + Construction), and Indiana's rank and
share on the same measure. If any state page fails, the national counts
still emit and the ranking is omitted (stated in the summary), rather than
ranking from a partial set.
"""
import json
import re
import ssl
import urllib.request
import urllib.error
from datetime import datetime, timezone

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = None

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
BASE_URL = "https://www.interconnection.fyi/data-center"
PAGE_URL = BASE_URL
NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
CANADIAN = {"AB", "ON"}
FOCUS = "IN"


def _page_props(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as r:
        html = r.read().decode("utf-8", errors="replace")
    m = NEXT_DATA_RE.search(html)
    if not m:
        raise ValueError(f"__NEXT_DATA__ script tag not found at {url}")
    return json.loads(m.group(1))["props"]["pageProps"]


def _state_counts(codes):
    """code -> {status: n}, from each state page. Raises on any failure so
    the caller can decide to drop the ranking."""
    out = {}
    for code in codes:
        projects = _page_props(f"{BASE_URL}/state/{code}")["projects"]
        counts = {}
        for p in projects:
            s = p.get("status") or "Unknown"
            counts[s] = counts.get(s, 0) + 1
        out[code] = counts
    return out


def _pipeline(counts):
    return counts.get("Proposed", 0) + counts.get("Construction", 0)


def _summarize(landing, states):
    """Two bases, kept apart: the state pages (project lists, the same basis
    as the Indiana scrape) and the landing page's headline records count.
    Checked 2026-09-29: the landing headline (12,538 records) is ~3x the sum
    of the state pages (3,922 projects) and their status splits differ, so
    they are not reconcilable from the pages. Ranks and shares use the state
    pages only, so Indiana is compared like with like."""
    sc = landing["statusCounts"]
    head = (
        f"Tracker headline: {landing['totalProjectCount']} records "
        f"({', '.join(f'{n} {s}' for s, n in sorted(sc.items(), key=lambda kv: -kv[1]))}); "
        "not reconcilable with the state-page project lists used above."
    )
    if states is None:
        return head + " State ranking unavailable this pull (a state page failed to fetch)."

    us = {c: v for c, v in states.items() if c not in CANADIAN}
    ranked = sorted(us, key=lambda c: (-_pipeline(us[c]), c))
    totals = {}
    for v in us.values():
        for k, n in v.items():
            totals[k] = totals.get(k, 0) + n
    tot_line = ", ".join(f"{n} {k}" for k, n in sorted(totals.items(), key=lambda kv: -kv[1]))
    top = ", ".join(f"{c} ({_pipeline(us[c])})" for c in ranked[:5])
    text = (
        f"{sum(totals.values())} projects across {len(us)} US state pages: {tot_line}. "
        f"Top states by active pipeline (Proposed + Construction): {top}."
    )
    if FOCUS in us:
        us_pipe = _pipeline(totals)
        us_op = totals.get("Operational", 0)
        ind = us[FOCUS]
        op_rank = sorted(us, key=lambda c: (-us[c].get("Operational", 0), c)).index(FOCUS) + 1
        text += (
            f" Indiana: {_pipeline(ind)} in pipeline (rank {ranked.index(FOCUS) + 1} of {len(us)}, "
            f"{100 * _pipeline(ind) / us_pipe:.1f}% of {us_pipe}); "
            f"{ind.get('Operational', 0)} operational (rank {op_rank}, "
            f"{100 * ind.get('Operational', 0) / us_op:.1f}% of {us_op})."
        )
    return text + " " + head


def fetch_items():
    try:
        landing = _page_props(PAGE_URL)
        landing["statusCounts"], landing["totalProjectCount"]
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError, OSError) as e:
        print(f"DEBUG: interconnection_fyi_national fetch failed — {e}")
        return []

    if not landing["totalProjectCount"]:
        print("DEBUG: interconnection_fyi_national — landing page has no projects")
        return []

    try:
        states = _state_counts(landing.get("statesWithProjects") or [])
        if not states:
            states = None
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError, OSError) as e:
        print(f"DEBUG: interconnection_fyi_national state fetch failed, ranking omitted — {e}")
        states = None

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return [{
        "title": f"US data-center tracker — {today}",
        "link": f"{PAGE_URL}#snapshot-{today}",
        "date": today,
        "summary": _summarize(landing, states),
        "content_links": [],
    }]


if __name__ == "__main__":
    for item in fetch_items():
        print(item["title"])
        print(item["summary"])
