"""Renders research.html from the raw pulls in research_data/ (written by
research_pull.py) plus any curated synthesis written by the Tuesday session
into research_notes.json. Mirrors collect_cinema()'s shape in main.py.

This module does NOT fetch anything itself and does NOT write synthesis —
it only renders what's already on disk. See CLAUDE.md for the split
between mechanical pulls (research_pull.py, unattended), curation/synthesis
(the Tuesday session, interactive), and rendering (this file, either).
"""
import json
from pathlib import Path

AREA_LABELS = {
    "ai_market": "AI / data-center market risk",
    "grid_buildout": "Grid buildout & interconnection",
    "agriculture": "Agriculture",
    "climate_drought": "Climate / drought",
}


def _load_notes():
    """Optional curated synthesis written by the Tuesday session, keyed by
    source id: {"epoch_ai": {"synthesis": "...", "as_of": "2026-09-16"}}.
    Absent entirely between Tuesdays is normal — falls back to raw items."""
    path = Path("research_notes.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception as e:
        print(f"DEBUG: research_notes.json error: {e}")
        return {}


def _render_source(source_data, notes):
    label = source_data.get("label", source_data.get("id", "Unknown source"))
    site_url = source_data.get("site_url", "#")
    status = source_data.get("status")
    fetched_at = source_data.get("fetched_at", "")
    note = notes.get(source_data.get("id"), {})

    if status != "ok" or not source_data.get("items"):
        return (
            f"<div class='article-entry'><h3><a href='{site_url}'>{label}</a></h3>"
            f"<p class='metadata'>Fetch unavailable — check source directly.</p></div>"
        )

    if note.get("synthesis"):
        as_of = note.get("as_of", fetched_at[:10] if fetched_at else "")
        meta = f"as of {as_of}" if as_of else ""
        return (
            f"<div class='article-entry'><h3><a href='{site_url}'>{label}</a></h3>"
            f"<p class='metadata'>{meta}</p><p>{note['synthesis']}</p></div>"
        )

    # No curated synthesis yet — fall back to the raw latest item as a plain link.
    item = source_data["items"][0]
    trail = "" if source_data.get("description_unreliable") else item.get("summary", "")
    trail_html = f"<p class='trail-text'>{trail}</p>" if trail else ""
    return (
        f"<div class='article-entry'><h3><a href='{item['link']}'>{item['title']}</a></h3>"
        f"<p class='metadata'>{label} &nbsp;·&nbsp; {item.get('date', '')}</p>"
        f"{trail_html}</div>"
    )


def collect_research(ts):
    print("DEBUG: Collecting Research...")
    data_dir = Path("research_data")
    if not data_dir.exists():
        return ""

    try:
        manifest = json.loads(Path("research_sources.json").read_text())
    except Exception as e:
        print(f"DEBUG: research_sources.json error: {e}")
        return ""

    notes = _load_notes()
    order = [s["id"] for s in manifest["sources"]]

    by_area = {}
    for sid in order:
        data_path = data_dir / f"{sid}.json"
        if not data_path.exists():
            continue
        try:
            source_data = json.loads(data_path.read_text())
        except Exception as e:
            print(f"DEBUG: research_data/{sid}.json error: {e}")
            continue
        area = source_data.get("area", "other")
        by_area.setdefault(area, []).append(_render_source(source_data, notes))

    if not by_area:
        return "<p class='metadata'>No research data pulled yet.</p>"

    sections = []
    for area, entries in by_area.items():
        area_label = AREA_LABELS.get(area, area)
        sections.append(f"<h2>{area_label}</h2>" + "\n".join(entries))

    content = "\n<hr>\n".join(sections)
    with open("research.html", "w", encoding="utf-8") as f:
        f.write(
            f"<!DOCTYPE html><html><head><meta charset='UTF-8'>"
            f"<title>liroh research {ts}</title><link rel='stylesheet' href='style.css'></head>"
            f"<body><h1>liroh research {ts}</h1>{content}</body></html>"
        )
    return content


if __name__ == "__main__":
    print(collect_research("test"))
