"""interconnection.fyi — Indiana data-center project tracker. No RSS/API;
the page is a Next.js app whose initial data ships embedded in a
<script id="__NEXT_DATA__"> JSON blob, so this reads that directly rather
than an HTML scrape (more stable against styling/markup changes).

This is a live snapshot (current project list), not a chronological feed —
there's no per-project "published date" to key off. So instead of trying
to diff project-by-project here, fetch_items() emits one dated summary
item per pull (counts by status/county), and relies on the history ledger
(research_data/history/interconnection_fyi.jsonl) to give the Tuesday
session a week-over-week record to compare — same principle as reading
back through old_issues/ for the Ag Barometer. The link is date-fragmented
so each day's snapshot gets its own history entry instead of colliding as
a duplicate of the same page URL.
"""
import json
import re
import ssl
import urllib.request
import urllib.error
from collections import Counter
from datetime import datetime, timezone

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = None

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
PAGE_URL = "https://www.interconnection.fyi/data-center/state/IN"
NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def _fetch_projects():
    req = urllib.request.Request(PAGE_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20, context=SSL_CONTEXT) as r:
        html = r.read().decode("utf-8", errors="replace")
    m = NEXT_DATA_RE.search(html)
    if not m:
        raise ValueError("__NEXT_DATA__ script tag not found — page structure may have changed")
    payload = json.loads(m.group(1))
    return payload["props"]["pageProps"]["projects"]


def _summarize(projects):
    status_counts = Counter(p.get("status") or "Unknown" for p in projects)
    county_counts = Counter(p.get("county") or "Unknown" for p in projects)
    top_counties = ", ".join(f"{c} ({n})" for c, n in county_counts.most_common(5))
    status_line = ", ".join(f"{n} {s}" for s, n in sorted(status_counts.items(), key=lambda kv: -kv[1]))
    return (
        f"{len(projects)} tracked Indiana data-center projects: {status_line}. "
        f"Top counties by project count: {top_counties}."
    )


def fetch_items():
    try:
        projects = _fetch_projects()
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError, OSError) as e:
        print(f"DEBUG: interconnection_fyi fetch failed — {e}")
        return []

    if not projects:
        print("DEBUG: interconnection_fyi — page fetched but no projects found")
        return []

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return [{
        "title": f"Indiana data-center tracker — {today}",
        "link": f"{PAGE_URL}#snapshot-{today}",
        "date": today,
        "summary": _summarize(projects),
        "content_links": [],
    }]


if __name__ == "__main__":
    for item in fetch_items():
        print(item["title"])
        print(item["summary"])
