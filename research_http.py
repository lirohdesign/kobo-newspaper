"""Shared fetch helper for the c4/c5 scrapers (conflict and visibility
sources, added 2026-10-21). Network errors are left to propagate so
research_pull.pull_source() records the source as status 'error' rather
than 'empty' — a blocked fetch and a quiet source should not look alike.
"""
import ssl
import urllib.request
from datetime import datetime, timezone

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = None

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as r:
        return r.read(), r.headers


def fetch_text(url, timeout=60):
    body, _ = fetch(url, timeout)
    return body.decode("utf-8", errors="replace")


def today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def snapshot(title, page_url, date, summary):
    """One dated item per pull. The link carries the date so each day's
    reading gets its own history line (see interconnection_fyi_scrape.py)."""
    return {
        "title": title,
        "link": f"{page_url}#snapshot-{date}",
        "date": date,
        "summary": summary,
        "content_links": [],
    }
