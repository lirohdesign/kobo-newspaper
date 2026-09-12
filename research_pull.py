"""Fetches raw items from feed-driven sources in research_sources.json and
writes them to research_data/<id>.json. Pure mechanical fetching — no
synthesis, no judgment. Curation and write-up happen in the Tuesday session,
not here. See CLAUDE.md for the split rationale.

Also maintains two accumulating records that a single day's pull can't see
on its own:
  - research_data/history/<id>.jsonl — every item ever seen for that source,
    deduped by link. Lets the Tuesday session check current claims/tone
    against what the same source said in the past, not just this week's
    snapshot (research_data/<id>.json only keeps the latest N items).
  - research_data/discovered_sources.json — outbound links found in each
    item's own content, tallied by domain across all runs. A domain that
    keeps getting cited from inside the content (not just a stray link)
    across multiple pulls is a candidate source addition — evidence for
    curation to weigh, not an automatic add.

Run standalone: python3 research_pull.py
"""
import json
import ssl
import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from html.parser import HTMLParser

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = None

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
DATA_DIR = Path("research_data")
HISTORY_DIR = DATA_DIR / "history"
DISCOVERED_PATH = DATA_DIR / "discovered_sources.json"
MAX_ITEMS_KEPT = 15

# Infra/social/platform domains that show up constantly in newsletter
# footers and carry no source-discovery signal. Not exhaustive — just cheap
# noise reduction; the Tuesday session is the real filter.
DOMAIN_DENYLIST = {
    "substack.com", "substackcdn.com", "twitter.com", "x.com", "youtube.com",
    "linkedin.com", "facebook.com", "instagram.com", "list-manage.com",
    "mailchi.mp", "spotify.com", "apple.com", "amazon.com", "paypal.com",
    "google.com", "outpost.pub",
}


class _ContentParser(HTMLParser):
    """Pulls both plain text and outbound <a href> links out of one pass
    over an item's HTML, so summary-cleaning and link-discovery share a
    single parse instead of two."""

    def __init__(self):
        super().__init__()
        self.chunks = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

    def handle_data(self, data):
        self.chunks.append(data)


def _parse_html(html_text):
    parser = _ContentParser()
    parser.feed(html_text or "")
    text = " ".join("".join(parser.chunks).split())
    return text, parser.links


def _truncate(text, max_len=300):
    if not text or len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "…"


def _domain_of(url):
    try:
        netloc = urllib.parse.urlparse(url).netloc.lower()
    except ValueError:
        return None
    return netloc[4:] if netloc.startswith("www.") else netloc


def fetch_feed(url):
    """Fetch and parse an RSS/Atom feed. Returns a list of item dicts, each
    with plain-text 'summary' plus raw 'content_links' (hrefs found in the
    item's full content, when the feed provides one via content:encoded)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20, context=SSL_CONTEXT) as r:
        data = r.read()
    root = ET.fromstring(data)
    content_ns = {"content": "http://purl.org/rss/1.0/modules/content/"}

    items = []
    # RSS 2.0
    for it in root.findall(".//item"):
        encoded = it.find("content:encoded", content_ns)
        full_html = (encoded.text if encoded is not None else None) or it.findtext("description") or ""
        text, links = _parse_html(full_html)
        items.append({
            "title": (it.findtext("title") or "").strip(),
            "link": (it.findtext("link") or "").strip(),
            "date": (it.findtext("pubDate") or "").strip(),
            "summary": _truncate(text),
            "content_links": links,
        })
    if items:
        return items

    # Atom fallback
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for it in root.findall(".//atom:entry", ns):
        link_el = it.find("atom:link", ns)
        full_html = it.findtext("atom:summary", default="", namespaces=ns) or ""
        text, links = _parse_html(full_html)
        items.append({
            "title": (it.findtext("atom:title", default="", namespaces=ns) or "").strip(),
            "link": link_el.get("href") if link_el is not None else "",
            "date": (it.findtext("atom:updated", default="", namespaces=ns) or "").strip(),
            "summary": _truncate(text),
            "content_links": links,
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


def append_history(source_id, items):
    """Append any items not already in this source's history ledger,
    deduped by link. Returns the count of genuinely new items."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    path = HISTORY_DIR / f"{source_id}.jsonl"

    known_links = set()
    if path.exists():
        with path.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    known_links.add(json.loads(line).get("link"))

    new_lines = []
    for item in items:
        if item["link"] in known_links:
            continue
        record = {k: v for k, v in item.items() if k != "content_links"}
        new_lines.append(json.dumps(record))
        known_links.add(item["link"])

    if new_lines:
        with path.open("a") as f:
            f.write("\n".join(new_lines) + "\n")
    return len(new_lines)


def update_discovered_sources(source_id, own_domains, tracked_domains, items):
    """Tally outbound-link domains found in each item's content against the
    cumulative discovered_sources.json record. Domains already tracked as a
    source (anywhere in research_sources.json, not just this one) are
    excluded — a citation of a source we already monitor isn't a discovery."""
    discovered = {}
    if DISCOVERED_PATH.exists():
        try:
            discovered = json.loads(DISCOVERED_PATH.read_text())
        except Exception as e:
            print(f"DEBUG: discovered_sources.json read error — {e}")
            discovered = {}

    exclude = own_domains | tracked_domains
    now = datetime.now(timezone.utc).isoformat()
    for item in items:
        seen_domains_this_item = set()
        for href in item.get("content_links", []):
            domain = _domain_of(href)
            if not domain or domain in exclude:
                continue
            if any(domain == d or domain.endswith("." + d) for d in DOMAIN_DENYLIST):
                continue
            if domain in seen_domains_this_item:
                continue  # count each domain once per item, not once per link
            seen_domains_this_item.add(domain)

            entry = discovered.setdefault(domain, {
                "first_seen": now,
                "count": 0,
                "seen_in_sources": [],
                "example_links": [],
            })
            entry["count"] += 1
            if source_id not in entry["seen_in_sources"]:
                entry["seen_in_sources"].append(source_id)
            if len(entry["example_links"]) < 3 and href not in entry["example_links"]:
                entry["example_links"].append(href)

    DISCOVERED_PATH.write_text(json.dumps(discovered, indent=2, sort_keys=True))


def main():
    DATA_DIR.mkdir(exist_ok=True)
    manifest = json.loads(Path("research_sources.json").read_text())

    tracked_domains = set()
    for s in manifest["sources"]:
        tracked_domains.update(d for d in (_domain_of(s.get("site_url", "")), _domain_of(s.get("feed_url", ""))) if d)

    for source in manifest["sources"]:
        if source["type"] != "rss":
            continue
        result = pull_source(source)
        result["label"] = source["label"]
        result["area"] = source["area"]
        result["site_url"] = source["site_url"]
        result["fetched_at"] = datetime.now(timezone.utc).isoformat()
        result["description_unreliable"] = source.get("description_unreliable", False)

        if result["status"] == "ok":
            own_domains = {d for d in (_domain_of(source["site_url"]), _domain_of(source["feed_url"])) if d}
            new_count = append_history(source["id"], result["items"])
            update_discovered_sources(source["id"], own_domains, tracked_domains, result["items"])
            print(f"DEBUG: {source['id']} — {new_count} new item(s) added to history ledger")

        out_path = DATA_DIR / f"{source['id']}.json"
        # content_links is pull-time-only scaffolding for discovery — don't
        # persist it into the per-source snapshot the digest renders from.
        out_result = dict(result)
        out_result["items"] = [{k: v for k, v in i.items() if k != "content_links"} for i in result["items"]]
        out_path.write_text(json.dumps(out_result, indent=2))


if __name__ == "__main__":
    main()
