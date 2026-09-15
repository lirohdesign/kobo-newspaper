"""Mechanical pre-flight check, meant to run first thing in the Tuesday
research session — before any curation/synthesis judgment. Turns "did the
pipeline silently break" into a yes/no instead of something the skill has
to eyeball feed-by-feed.

Checks per source:
  - freshness: was research_data/<id>.json actually refreshed recently, or
    did the daily cron quietly stop running?
  - schema: non-empty items, each with a title/link/date that isn't blank,
    and a link that resolves to a real absolute URL.
  - status: did the fetch itself report ok/empty/error last run?

Also surfaces discovered_sources.json entries that have crossed a simple
repetition threshold — candidates for the Tuesday session to evaluate as
new sources, not automatic additions.

Run standalone: python3 research_validate.py
Exit code 0 if everything looks healthy, 1 if anything needs attention —
usable as a quick gate before starting synthesis.
"""
import json
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA_DIR = Path("research_data")
SOURCES_MANIFEST = Path("research_sources.json")

# research_pull.py's daily cron fetches every rss/scrape source on every run
# regardless of how often the underlying content actually changes — so
# fetched_at staleness is fundamentally a "did the cron run recently" check,
# not a "is this source's content current" check. But it still needs to be
# sized per cadence family: a monthly-cadence source is documented as
# expected to return the same latest item for weeks at a time (that's
# normal, not a problem), and if the pipeline is ever changed to pull
# monthly/quarterly-tier sources less often than daily, a flat 48h limit
# would wrongly flag every one of them as stale on day 3. Falls back to the
# default bucket for any cadence string not listed here (including an
# empty/missing cadence field).
FRESHNESS_LIMITS = {
    "weekly": timedelta(hours=48),
    "weekly_digest": timedelta(hours=48),
    "weekly_in_season": timedelta(hours=48),
    "monthly": timedelta(days=10),
    "monthly_digest": timedelta(days=10),
}
DEFAULT_FRESHNESS_LIMIT = timedelta(hours=48)  # daily cron; 2x slack for a missed run
DISCOVERY_MIN_COUNT = 3
DISCOVERY_MIN_SOURCES = 2


def _load_cadences():
    """id -> cadence, read from research_sources.json so the freshness
    window can be sized per source without hardcoding a second copy of the
    manifest here."""
    try:
        manifest = json.loads(SOURCES_MANIFEST.read_text())
    except Exception as e:
        print(f"DEBUG: {SOURCES_MANIFEST} unreadable, falling back to default freshness window for all sources — {e}")
        return {}
    return {s["id"]: s.get("cadence", "") for s in manifest.get("sources", [])}


def _is_valid_url(url):
    try:
        parsed = urllib.parse.urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except ValueError:
        return False


def check_source(source_id, path, cadences):
    problems = []
    try:
        data = json.loads(path.read_text())
    except Exception as e:
        return [f"{source_id}: unreadable JSON — {e}"]

    status = data.get("status")
    if status != "ok":
        problems.append(f"{source_id}: last pull status was '{status}'" +
                         (f" — {data.get('error')}" if data.get("error") else ""))

    cadence = data.get("cadence") or cadences.get(source_id, "")
    limit = FRESHNESS_LIMITS.get(cadence, DEFAULT_FRESHNESS_LIMIT)

    fetched_at = data.get("fetched_at")
    if not fetched_at:
        problems.append(f"{source_id}: no fetched_at timestamp on record")
    else:
        try:
            ts = datetime.fromisoformat(fetched_at)
            age = datetime.now(timezone.utc) - ts
            if age > limit:
                hours = age.total_seconds() / 3600
                problems.append(f"{source_id}: stale — last pulled {hours:.0f}h ago (limit {limit.total_seconds()/3600:.0f}h for cadence '{cadence or 'default'}'). Cron may have broken.")
        except ValueError:
            problems.append(f"{source_id}: fetched_at is not a valid ISO timestamp: {fetched_at!r}")

    items = data.get("items", [])
    if status == "ok" and not items:
        problems.append(f"{source_id}: status ok but items list is empty")

    for i, item in enumerate(items):
        if not item.get("title", "").strip():
            problems.append(f"{source_id}: item {i} has a blank title")
        if not item.get("date", "").strip():
            problems.append(f"{source_id}: item {i} has a blank date")
        if not _is_valid_url(item.get("link", "")):
            problems.append(f"{source_id}: item {i} has an invalid link: {item.get('link')!r}")

    return problems


def check_discovery_candidates():
    path = DATA_DIR / "discovered_sources.json"
    if not path.exists():
        return []
    discovered = json.loads(path.read_text())
    candidates = []
    for domain, info in discovered.items():
        if info["count"] >= DISCOVERY_MIN_COUNT and len(info["seen_in_sources"]) >= DISCOVERY_MIN_SOURCES:
            candidates.append((domain, info))
    candidates.sort(key=lambda x: -x[1]["count"])
    return candidates


def main():
    if not DATA_DIR.exists():
        print("research_data/ doesn't exist — has research_pull.py ever run?")
        sys.exit(1)

    cadences = _load_cadences()
    all_problems = []
    source_files = sorted(p for p in DATA_DIR.glob("*.json") if p.name != "discovered_sources.json")
    if not source_files:
        print("No source data files found in research_data/.")
        sys.exit(1)

    for path in source_files:
        all_problems.extend(check_source(path.stem, path, cadences))

    print(f"Checked {len(source_files)} source(s).")
    if all_problems:
        print(f"\n{len(all_problems)} issue(s) found:")
        for p in all_problems:
            print(f"  - {p}")
    else:
        print("All sources fresh and well-formed.")

    candidates = check_discovery_candidates()
    if candidates:
        print(f"\n{len(candidates)} candidate new source(s) (cited {DISCOVERY_MIN_COUNT}+ times, "
              f"across {DISCOVERY_MIN_SOURCES}+ existing sources):")
        for domain, info in candidates:
            print(f"  - {domain}: cited {info['count']}x, seen in {info['seen_in_sources']}")
            for link in info["example_links"]:
                print(f"      e.g. {link}")

    sys.exit(1 if all_problems else 0)


if __name__ == "__main__":
    main()
