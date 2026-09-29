"""Indiana DNR Division of Water — Monthly Water Resource Summary.

Expert-written monthly synthesis (precipitation and SPI classes, Drought
Monitor status, streamflow vs normal, Lake Michigan, reservoirs, and the
groundwater-level classification of the state's observation wells). The
categories ("above normal", "well below normal") are the Division's own
judgement, not raw gauge readings. No RSS or API, and no keyless
alternative: USGS WaterWatch and Groundwater Watch are decommissioned.

The page is a single server-rendered HTML document that always shows the
latest month under an <h2> like "August 2026", with <h3> sections beneath.
Older months are not kept on the page, so fetch_items() emits one dated
item per pull and the history ledger accumulates the series. Link is
date-stamped (#month-YYYY-MM) so the ledger keeps every month (see
drought_monitor_scrape.py).

Exposes fetch_items() in the shape research_pull.py expects from a scraper.
"""
import html
import re
import ssl
import urllib.error
import urllib.request
from calendar import monthrange
from datetime import datetime

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = None

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
SITE_URL = "https://www.in.gov/dnr/water/water-availability-use-rights/water-resource-updates/monthly-water-resource-summary/"

# Sections that make the summary line, in order. Others (Lake Michigan,
# reservoirs) stay on the page for the reader.
SUMMARY_SECTIONS = [("Precipitation", "Precipitation", 1), ("U. S. Drought Monitor", "Drought Monitor", 2),
                    ("Streamflow", "Streamflow", 2), ("Groundwater Levels", "Groundwater", 3)]


def _text(fragment):
    fragment = re.sub(r"<(script|style).*?</\1>", "", fragment, flags=re.S)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    return html.unescape(re.sub(r"\s+", " ", fragment)).strip()


def _first_sentences(text, n):
    text = re.sub(r"U\. ?S\.", "U.S.", text)
    text = re.sub(r"\s*Detailed information on \w+\s*$", "", text)  # link caption
    # Don't split after the "U.S." abbreviation.
    parts = re.split(r"(?<=[a-z0-9%)][.!?])\s+(?=[A-Z])", text)
    return " ".join(parts[:n])


def parse_summary(page):
    """Returns (month_label, {section: text}) or (None, {}) if the layout
    changed. month_label is like 'August 2026'."""
    m = re.search(r"<main.*?</main>", page, re.S)
    body = m.group(0) if m else page
    month = re.search(r"<h2[^>]*>\s*([A-Z][a-z]+ \d{4})\s*</h2>", body)
    if not month:
        return None, {}
    parts = re.split(r"<h3[^>]*>", body[month.end():])
    sections = {}
    for part in parts[1:]:
        head, _, rest = part.partition("</h3>")
        sections[_text(head)] = _text(rest.split("<h2")[0])
    return month.group(1), sections


def fetch_items():
    req = urllib.request.Request(SITE_URL, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=25, context=SSL_CONTEXT) as r:
            page = r.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        print(f"DEBUG: indiana_dnr_water fetch failed — {e}")
        return []

    label, sections = parse_summary(page)
    if not label or not sections:
        print("DEBUG: indiana_dnr_water — layout changed, no month heading/sections found")
        return []
    dt = datetime.strptime(label, "%B %Y")
    # Groundwater/streamflow figures are as of month end; date the item then.
    date = f"{dt.year}-{dt.month:02d}-{monthrange(dt.year, dt.month)[1]:02d}"

    summary = " ".join(
        f"{label_}: {_first_sentences(sections[name], n)}"
        for name, label_, n in SUMMARY_SECTIONS if sections.get(name)
    )
    if not summary:
        print("DEBUG: indiana_dnr_water — expected sections missing")
        return []
    return [{
        "title": f"Indiana Monthly Water Resource Summary — {label}",
        "link": f"{SITE_URL}#month-{dt.year}-{dt.month:02d}",
        "date": date,
        "summary": summary,
        "content_links": [],
    }]


if __name__ == "__main__":
    for item in fetch_items():
        for k in ("title", "link", "date", "summary"):
            print(f"{k}: {item[k]}")
