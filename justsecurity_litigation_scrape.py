"""Just Security litigation tracker — count of court challenges to Trump
administration actions. The page (about 5 MB of HTML) states the running
total as 'Total number of cases currently tracked: N.' Counting rules are
the tracker's own: appeals are not separate cases, and some groups of
related suits are counted as one. No download exists, so the count is the
reading; the session can open the page for case detail.
"""
import re

from research_http import fetch_text, snapshot, today

PAGE_URL = "https://www.justsecurity.org/107087/tracker-litigation-legal-challenges-trump-administration/"
COUNT_RE = re.compile(r"Total number of cases currently tracked\W*([\d,]+)")


def fetch_items():
    html = fetch_text(PAGE_URL, timeout=90)
    text = re.sub(r"<[^>]+>", " ", html)
    m = COUNT_RE.search(" ".join(text.split()))
    if not m:
        print("DEBUG: justsecurity_litigation — case count not found on the page")
        return []
    modified = re.search(r'"dateModified":"(\d{4}-\d{2}-\d{2})', html)
    page_date = modified.group(1) if modified else "unknown"
    date = today()
    summary = f"{m.group(1)} cases currently tracked (page modified {page_date})."
    return [snapshot(f"Litigation tracker — {date}", PAGE_URL, date, summary)]


if __name__ == "__main__":
    for item in fetch_items():
        print(item["summary"])
