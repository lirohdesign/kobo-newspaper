"""OCHA oPt — Gaza Strip reported impact snapshots and humanitarian
situation reports, listed on ochaopt.org/publications. No RSS (the
/rss.xml path 404s, ReliefWeb's API needs an approved appname and its RSS
returns an empty 202 to scripts; checked 2026-10-21).

The figures themselves are in each snapshot's PDF, so this lists the items
and the PDF link; the session reads the PDF. OCHA's own disclaimer, carried
into every summary: casualty numbers come from the Gaza Ministry of Health
and the Israeli authorities and are not yet verified by the UN.
"""
import re
from datetime import datetime

from research_http import fetch_text

SITE = "https://www.ochaopt.org"
LIST_URL = f"{SITE}/publications"
ITEM_RE = re.compile(
    r'<a href="(/content/(?:reported-impact-snapshot-gaza-strip|humanitarian-situation-report)[^"]*)"[^>]*>([^<]{10,200})</a>'
)
DATE_RE = re.compile(r"(\d{1,2} [A-Z][a-z]+ 20\d\d)")
DISCLAIMER = "Casualty figures are Gaza MoH and Israeli-authority figures, not yet UN-verified (OCHA's disclaimer)."


def _pdf_link(path):
    html = fetch_text(SITE + path)
    m = re.search(r'href="([^"]+\.pdf)"', html)
    if not m:
        return None
    return m.group(1) if m.group(1).startswith("http") else SITE + m.group(1)


def fetch_items(max_items=6):
    html = fetch_text(LIST_URL)
    items, seen = [], set()
    for path, title in ITEM_RE.findall(html):
        title = " ".join(title.split())
        if path in seen or title.lower().startswith("read more"):
            continue
        seen.add(path)
        m = DATE_RE.search(title)
        if not m:
            continue
        date = datetime.strptime(m.group(1), "%d %B %Y").strftime("%Y-%m-%d")
        summary = DISCLAIMER
        if "snapshot" in path:
            pdf = _pdf_link(path)
            summary = f"Figures in the PDF: {pdf}. {DISCLAIMER}" if pdf else summary
        items.append({"title": title, "link": SITE + path, "date": date, "summary": summary, "content_links": []})
        if len(items) >= max_items:
            break
    if not items:
        print("DEBUG: ochaopt_gaza — publications page fetched but no Gaza items matched")
    return items


if __name__ == "__main__":
    for item in fetch_items():
        print(item["date"], item["title"], "\n  ", item["summary"])
