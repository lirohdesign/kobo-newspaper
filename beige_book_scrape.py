"""Federal Reserve Beige Book — latest edition, Chicago (Seventh) District
plus the national summary.

Expert-synthesized, practitioner-facing qualitative read on the economy,
published 8 times a year (about two weeks before each FOMC meeting), and it
says plainly when little has changed ("flat on balance", "no change").
No RSS exists for it (the Fed's feeds list has none), but edition URLs are
stable: beigebookYYYYMM-summary.htm (national) and
beigebookYYYYMM-chicago.htm (district), where YYYYMM is the end of the
reporting period (the Sep 2, 2026 release is 202608). The landing page
links every 2026 edition, so the newest is the highest YYYYMM linked.

One item per edition; the link is the edition's own URL, so the history
ledger accumulates one entry per release. Item date is the page's "Last
Update" stamp, which equals the release date until the Fed revises the page.

Exposes fetch_items() in the shape research_pull.py expects from a scraper.
"""
import html
import re
import ssl
import urllib.error
import urllib.request
from datetime import datetime

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = None

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
BASE = "https://www.federalreserve.gov/monetarypolicy/"
LANDING_URL = BASE + "publications/beige-book-default.htm"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=25, context=SSL_CONTEXT) as r:
        return r.read().decode("utf-8", errors="replace")


def _text(fragment):
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    return html.unescape(re.sub(r"\s+", " ", fragment)).strip()


def latest_edition(landing_html):
    """Highest YYYYMM among beigebookYYYYMM-summary.htm links, or None."""
    editions = re.findall(r"beigebook(\d{6})-summary\.htm", landing_html)
    return max(editions) if editions else None


def first_paragraph_after(page, heading):
    """Text of the first <p> after an <h4> whose text is `heading`."""
    m = re.search(r"<h4[^>]*>\s*" + re.escape(heading) + r"\s*</h4>\s*<p>(.*?)</p>", page, re.S)
    return _text(m.group(1)) if m else ""


def release_date(page):
    m = re.search(r'id="lastUpdate"[^>]*>\s*Last Update:\s*([A-Z][a-z]+ \d{1,2}, \d{4})', page)
    if not m:
        return None
    return datetime.strptime(m.group(1), "%B %d, %Y").strftime("%Y-%m-%d")


def fetch_items():
    try:
        edition = latest_edition(_get(LANDING_URL))
        if not edition:
            print("DEBUG: beige_book — no edition links on landing page (layout changed?)")
            return []
        summary_url = f"{BASE}beigebook{edition}-summary.htm"
        national_page = _get(summary_url)
        chicago_page = _get(f"{BASE}beigebook{edition}-chicago.htm")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        print(f"DEBUG: beige_book fetch failed — {e}")
        return []

    national = first_paragraph_after(national_page, "Overall Economic Activity")
    chicago = first_paragraph_after(chicago_page, "Summary of Economic Activity")
    date = release_date(national_page)
    if not (national and chicago and date):
        print("DEBUG: beige_book — expected sections/date missing (layout changed?)")
        return []

    return [{
        "title": f"Beige Book — {datetime.strptime(date, '%Y-%m-%d').strftime('%B %-d, %Y')} (Chicago District and national)",
        "link": summary_url,
        "date": date,
        "summary": f"Chicago District: {chicago} National: {national}",
        "content_links": [],
    }]


if __name__ == "__main__":
    for item in fetch_items():
        for k in ("title", "link", "date", "summary"):
            print(f"{k}: {item[k]}")
