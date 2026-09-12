"""Fetches raw items from feed-driven sources in research_sources.json and
writes them to research_data/<id>.json. Pure mechanical fetching — no
synthesis, no judgment. Curation and write-up happen in the Tuesday session,
not here. See CLAUDE.md for the split rationale.

Run standalone: python3 research_pull.py
"""
import json
import ssl
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = None

from html.parser import HTMLParser


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.chunks = []

    def handle_data(self, data):
        self.chunks.append(data)


def _clean_summary(html_text, max_len=300):
    """Feed descriptions often carry raw HTML (nested <p>, promo links).
    Strip to plain text so it's safe to drop into an article-entry <p>."""
    if not html_text:
        return ""
    extractor = _TextExtractor()
    extractor.feed(html_text)
    text = " ".join("".join(extractor.chunks).split())
    return (text[:max_len].rsplit(" ", 1)[0] + "…") if len(text) > max_len else text

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
DATA_DIR = Path("research_data")
MAX_ITEMS_KEPT = 15


def fetch_feed(url):
    """Fetch and parse an RSS/Atom feed. Returns a list of item dicts."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20, context=SSL_CONTEXT) as r:
        data = r.read()
    root = ET.fromstring(data)

    items = []
    # RSS 2.0
    for it in root.findall(".//item"):
        items.append({
            "title": (it.findtext("title") or "").strip(),
            "link": (it.findtext("link") or "").strip(),
            "date": (it.findtext("pubDate") or "").strip(),
            "summary": _clean_summary(it.findtext("description") or ""),
        })
    if items:
        return items

    # Atom fallback
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for it in root.findall(".//atom:entry", ns):
        link_el = it.find("atom:link", ns)
        items.append({
            "title": (it.findtext("atom:title", default="", namespaces=ns) or "").strip(),
            "link": link_el.get("href") if link_el is not None else "",
            "date": (it.findtext("atom:updated", default="", namespaces=ns) or "").strip(),
            "summary": _clean_summary(it.findtext("atom:summary", default="", namespaces=ns) or ""),
        })
    return items


def pull_source(source):
    sid = source["id"]
    try:
        items = fetch_feed(source["feed_url"])
    except (urllib.error.URLError, urllib.error.HTTPError, ET.ParseError, OSError) as e:
        print(f"DEBUG: {sid} fetch failed — {e}")
        return {"id": sid, "status": "error", "error": str(e), "items": []}

    skip_prefix = source.get("filter", {}).get("skip_title_prefix")
    if skip_prefix:
        items = [i for i in items if not i["title"].startswith(skip_prefix)]

    if not items:
        print(f"DEBUG: {sid} — feed fetched but no usable items")
        return {"id": sid, "status": "empty", "items": []}

    print(f"DEBUG: {sid} — OK, {len(items)} items")
    return {"id": sid, "status": "ok", "items": items[:MAX_ITEMS_KEPT]}


def main():
    DATA_DIR.mkdir(exist_ok=True)
    manifest = json.loads(Path("research_sources.json").read_text())

    for source in manifest["sources"]:
        if source["type"] != "rss":
            continue
        result = pull_source(source)
        result["label"] = source["label"]
        result["area"] = source["area"]
        result["site_url"] = source["site_url"]
        result["fetched_at"] = datetime.now(timezone.utc).isoformat()
        result["description_unreliable"] = source.get("description_unreliable", False)
        out_path = DATA_DIR / f"{source['id']}.json"
        out_path.write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
