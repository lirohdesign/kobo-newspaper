"""Kiel Institute Ukraine Support Tracker — government aid to Ukraine by
donor. Releases come about every two months as an XLSX; this reads the
release number and update date off the tracker page so a new release shows
up as a new item. The figures are read from the release itself in session.

One item per release (link keyed by release number), so the history ledger
only grows when Kiel publishes.
"""
import re
from datetime import datetime

from research_http import fetch_text

PAGE_URL = "https://www.kielinstitut.de/topics/war-against-ukraine/ukraine-support-tracker/"
SITE = "https://www.kielinstitut.de"


def fetch_items():
    html = fetch_text(PAGE_URL)
    upd = re.search(r"Update ([A-Z][a-z]+ \d{1,2}, 20\d\d)", html)
    rel = re.search(r'href="([^"]*Release_(\d+)\.xlsx)"', html)
    if not (upd and rel):
        print("DEBUG: kiel_tracker — update date or release file not found on the page")
        return []
    date = datetime.strptime(upd.group(1), "%B %d, %Y").strftime("%Y-%m-%d")
    xlsx = rel.group(1) if rel.group(1).startswith("http") else SITE + rel.group(1)
    return [{
        "title": f"Ukraine Support Tracker — Release {rel.group(2)} (updated {upd.group(1)})",
        "link": f"{PAGE_URL}#release-{rel.group(2)}",
        "date": date,
        "summary": f"Release {rel.group(2)}, page updated {upd.group(1)}. Data file: {xlsx}",
        "content_links": [],
    }]


if __name__ == "__main__":
    for item in fetch_items():
        print(item["title"], "\n  ", item["summary"])
