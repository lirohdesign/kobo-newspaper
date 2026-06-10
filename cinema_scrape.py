#!/usr/bin/env python3
"""Scrapes film listings from configured venues and generates cinema.html.

Reads venues.json for the venue list. Each venue has a matching parse_
function below. New venues get a new parse_ function — sites all differ
enough that a generic parser isn't worth the fragility.

Run standalone to preview the page before wiring into main.py:
    python3 cinema_scrape.py

Output: cinema.html (same style as weather.html, nyt.html, links.html).
"""

import json
import ssl
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = None  # GitHub Actions (Linux) has system certs; certifi only needed on macOS

HERE = Path(__file__).parent
VENUES_PATH = HERE / "venues.json"
OUTPUT_PATH = HERE / "cinema.html"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def fetch_html(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20, context=SSL_CONTEXT) as resp:
        return resp.read().decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Parsers — one per venue, returns list of film dicts
# ---------------------------------------------------------------------------

def parse_vickers(html):
    soup = BeautifulSoup(html, "html.parser")
    films = []

    for block in soup.find_all(class_="podsfilm"):
        title_el = block.find(class_="podsfilmtitlelink")
        if not title_el:
            continue

        series_el = block.find(class_="podsfilmseries")
        info_el = block.find(class_="showinfodiv")
        blurb_el = block.find(class_="arthouseblurb")
        showtime_els = block.find_all(class_="arthousebutton")

        films.append({
            "title": title_el.get_text(strip=True),
            "series": series_el.get_text(strip=True) if series_el else "",
            "info": info_el.get_text(strip=True) if info_el else "",
            "blurb": blurb_el.get_text(strip=True) if blurb_el else "",
            "showtimes": [s.get_text(strip=True) for s in showtime_els if s.get_text(strip=True)],
        })

    return films


PARSERS = {
    "vickers": parse_vickers,
    # add new venues here as: "venue_id": parse_venue_id
}


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

def render_film(film):
    series_badge = f"<p class='metadata'>{film['series'].upper()}</p>" if film["series"] else ""
    showtimes_html = ""
    if film["showtimes"]:
        times = " &nbsp;·&nbsp; ".join(film["showtimes"])
        showtimes_html = f"<p class='metadata'>{times}</p>"
    return f"""<div class='article-entry'>
{series_badge}
<h3>{film['title']}</h3>
<p class='metadata'>{film['info']}</p>
<p>{film['blurb']}</p>
{showtimes_html}
</div>"""


def render_venue_section(venue, films):
    if not films:
        return f"<h2>{venue['name']}</h2><p>No listings found.</p>"
    film_html = "\n".join(render_film(f) for f in films)
    return f"<h2>{venue['name']}</h2>\n{film_html}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def collect_cinema():
    venues_data = json.loads(VENUES_PATH.read_text())
    sections = []

    for venue in venues_data["venues"]:
        vid = venue["id"]
        parser = PARSERS.get(vid)
        if not parser:
            print(f"  {venue['name']}: no parser for id '{vid}', skipping")
            continue
        try:
            html = fetch_html(venue["url"])
            films = parser(html)
            print(f"  {venue['name']}: {len(films)} films")
            sections.append(render_venue_section(venue, films))
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            print(f"  {venue['name']}: fetch failed — {exc}")
            sections.append(f"<h2>{venue['name']}</h2><p>Unavailable.</p>")

    return "\n<hr>\n".join(sections)


def main():
    ts = datetime.now().strftime("%B %d, %Y")
    print(f"cinema_scrape — {ts}")
    content = collect_cinema()
    page = f"""<!DOCTYPE html>
<html>
<head><meta charset='UTF-8'><link rel='stylesheet' href='style.css'></head>
<body>
<h1>liroh cinema {ts}</h1>
{content}
</body>
</html>"""
    OUTPUT_PATH.write_text(page, encoding="utf-8")
    print(f"wrote {OUTPUT_PATH.name}")


if __name__ == "__main__":
    main()
