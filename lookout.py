#!/usr/bin/env python3
"""Lookout: watch public listing pages and report what is new on them.

Runs locally with no model involved. It reads a private state directory that
lives outside this repo (default ~/Documents/kobo-lookout, or $LOOKOUT_STATE),
fetches every page in that directory's watches.json, and writes report.md
there. The research-digest skill reads the report; nothing this script reads
or writes belongs in this repo, and the cron never runs it.

What it does per watch:
  - fetch the page, reduce it to lines of visible text plus JSON-LD event names
  - match the lines against a list of names derived at run time from the files
    named in the state directory's config.json
  - compare the lines with the snapshot from the last run and keep the new ones
  - record health: HTTP status, text size against the last run, runs since a
    new line appeared

State directory layout (all private):
  config.json    name sources, exclusions, limits
  watches.json   [{"id", "label", "url", "kind", "added", "why"}]
  state/<id>.json   last snapshot and health for one watch
  state/names.json  the name list from the last run, for the drift line
  report.md      this run's output, overwritten each run

Usage:
  python3 lookout.py                 # run every watch
  python3 lookout.py --only <id>     # run one
  python3 lookout.py --names         # print the derived name list and stop
"""

import glob
import html
import json
import os
import re
import subprocess
import sys
import unicodedata
import urllib.request
from datetime import date
from pathlib import Path

STATE = Path(os.environ.get("LOOKOUT_STATE", "~/Documents/kobo-lookout")).expanduser()
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Safari/605.1.15")
DEFAULTS = {
    "min_name_length": 5,         # shorter single-word names match too much
    "new_lines_per_watch": 40,    # cap on new lines reported per watch
    "report_char_budget": 24000,  # cap on the whole report, about 6k tokens
    "quiet_runs_flag": 8,         # runs with no new line before a watch is flagged
    "shrink_flag": 0.5,           # text under this share of last run is flagged
}


def fold(text):
    """Casefold and strip accents so 'Pärt' matches 'Part' consistently."""
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).casefold()


# ── Names ─────────────────────────────────────────────────────────────────────

def _walk_json(node, keys, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in keys:
                for item in (v if isinstance(v, list) else [v]):
                    if isinstance(item, str):
                        out.append(item)
                    elif isinstance(item, dict) and isinstance(item.get("name"), str):
                        out.append(item["name"])
            _walk_json(v, keys, out)
    elif isinstance(node, list):
        for v in node:
            _walk_json(v, keys, out)


def _latest(paths):
    """Of dated files (name-YYYY-MM-DD.ext), keep only the newest date's set."""
    dated = {}
    for p in paths:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", Path(p).name)
        dated.setdefault(m.group(1) if m else "", []).append(p)
    if not dated:
        return []
    if list(dated) == [""]:
        return dated[""]
    return dated[max(k for k in dated if k)] + dated.get("", [])


def derive_names(config):
    """Return {folded name: {"name", "weight", "sources"}} from the live files."""
    names = {}
    exclude = {fold(n) for n in config.get("exclude_names", [])}
    for src in config.get("name_sources", []):
        paths = _latest(sorted(glob.glob(os.path.expanduser(src["glob"]))))
        for p in paths:
            found = []
            try:
                if src["type"] == "json":
                    data = json.loads(Path(p).read_text())
                    if src.get("top_level_name") and isinstance(data, list):
                        found += [d["name"] for d in data
                                  if isinstance(d, dict) and isinstance(d.get("name"), str)]
                    _walk_json(data, set(src.get("keys", [])), found)
                elif src["type"] == "regex":
                    for m in re.finditer(src["pattern"], Path(p).read_text(), re.M):
                        found += [s.strip() for s in re.split(src.get("split", r"$^"), m.group(1))]
            except (OSError, ValueError, KeyError) as e:
                print(f"  name source unreadable: {p} ({e})", file=sys.stderr)
                continue
            for n in set(found):
                key = fold(n)
                if not key or key in exclude:
                    continue
                entry = names.setdefault(key, {"name": n, "weight": 0, "sources": []})
                entry["weight"] += src.get("weight", 1)
                entry["sources"].append(Path(p).name)
    min_len = config["min_name_length"]
    return {k: v for k, v in names.items() if len(k) >= min_len}


# ── Pages ─────────────────────────────────────────────────────────────────────

def fetch(url):
    """Return (status, body). Falls back to curl when urllib is refused."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception as first:
        try:
            out = subprocess.run(
                ["curl", "-sL", "-m", "30", "-A", UA, "-w", "\n%{http_code}", url],
                capture_output=True, timeout=40)
            body, _, code = out.stdout.decode("utf-8", "replace").rpartition("\n")
            return int(code or 0), body
        except Exception:
            return 0, f"fetch failed: {first}"


def _ld_events(node, out):
    if isinstance(node, dict):
        t = node.get("@type", "")
        t = " ".join(t) if isinstance(t, list) else str(t)
        if "Event" in t and node.get("name"):
            when = str(node.get("startDate", ""))[:10]
            price = ""
            offers = node.get("offers")
            offers = offers[0] if isinstance(offers, list) and offers else offers
            if isinstance(offers, dict):
                price = str(offers.get("price") or offers.get("lowPrice") or "")
            line = " · ".join(x for x in (when, html.unescape(str(node["name"])),
                                           f"${price}" if price else "") if x)
            out.append(line)
        for v in node.values():
            _ld_events(v, out)
    elif isinstance(node, list):
        for v in node:
            _ld_events(v, out)


def page_lines(body):
    """Visible text lines plus one line per JSON-LD event, de-duplicated."""
    lines = []
    for block in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', body, re.S | re.I):
        try:
            _ld_events(json.loads(block), lines)
        except ValueError:
            pass
    text = re.sub(r"(?s)<!--.*?-->", " ", body)   # comments carry timestamps that read as news
    text = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer)\b.*?</\1>", " ", text)
    text = re.sub(r"(?i)<(br|/p|/div|/li|/h[1-6]|/tr|/article|/section|/a)\s*/?>", "\n", text)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    seen, out = set(), []
    for raw in lines + text.split("\n"):
        line = re.sub(r"\s+", " ", raw).strip()
        if 4 <= len(line) <= 240 and line not in seen:
            seen.add(line)
            out.append(line)
    return out


def match_names(lines, names):
    hits = []
    for line in lines:
        folded = fold(line)
        for key, entry in names.items():
            if key in folded and re.search(rf"(?<!\w){re.escape(key)}(?!\w)", folded):
                hits.append({"name": entry["name"], "weight": entry["weight"], "line": line})
    return hits


# ── Run ───────────────────────────────────────────────────────────────────────

def run_watch(watch, names, config, today):
    path = STATE / "state" / f"{watch['id']}.json"
    prev = json.loads(path.read_text()) if path.exists() else {}
    status, body = fetch(watch["url"])
    lines = page_lines(body) if status == 200 else []
    size = sum(len(x) for x in lines)
    first_run = "lines" not in prev
    old = set(prev.get("lines", []))
    new = [x for x in lines if x not in old]

    flags = []
    if status != 200:
        flags.append(f"HTTP {status}")
    elif size < 500:
        flags.append("almost no text; the page may be drawn by script")
    elif prev.get("size") and size < prev["size"] * config["shrink_flag"]:
        flags.append(f"text shrank from {prev['size']} to {size} characters")
    quiet = 0 if (new or first_run) else prev.get("quiet_runs", 0) + 1
    if quiet >= config["quiet_runs_flag"]:
        flags.append(f"no new line in {quiet} runs")

    state = {
        "last_run": today, "status": status, "size": size, "quiet_runs": quiet,
        "runs": prev.get("runs", 0) + 1,
        "last_ok": today if status == 200 and size >= 500 else prev.get("last_ok"),
    }
    # A failed or empty fetch keeps the old snapshot, so recovery does not replay
    # the page as new. A watch that has never returned text keeps no snapshot,
    # so its first good fetch is still treated as a baseline.
    if status == 200 and size >= 500:
        state["lines"] = lines
    elif "lines" in prev:
        state["lines"] = prev["lines"]
    path.write_text(json.dumps(state, ensure_ascii=False, indent=0))
    return {
        "watch": watch, "status": status, "size": size, "flags": flags,
        "first_run": first_run, "new": new,
        "hits": match_names(lines, names),
        "new_hit_lines": {h["line"] for h in match_names(new, names)},
    }


def write_report(results, names, drift, config, today):
    budget = config["report_char_budget"]
    out = [f"# Lookout report {today}", ""]
    out.append(f"{len(results)} watches run, {len(names)} names derived. "
               f"Names since last run: +{len(drift['added'])} −{len(drift['removed'])}.")
    if drift["added"]:
        out.append("Added: " + ", ".join(drift["added"][:40]))
    if drift["removed"]:
        out.append("Removed: " + ", ".join(drift["removed"][:40]))

    out += ["", "## Health"]
    flagged = [r for r in results if r["flags"]]
    if not flagged:
        out.append("Every watch returned text.")
    for r in flagged:
        out.append(f"- {r['watch']['id']}: {'; '.join(r['flags'])}")

    out += ["", "## Name matches"]
    any_hit = False
    for r in results:
        if not r["hits"]:
            continue
        any_hit = True
        out.append(f"### {r['watch']['label']} <{r['watch']['url']}>")
        seen = set()
        for h in sorted(r["hits"], key=lambda h: -h["weight"]):
            if (h["name"], h["line"]) in seen:
                continue
            seen.add((h["name"], h["line"]))
            tag = "new" if h["line"] in r["new_hit_lines"] or r["first_run"] else "seen before"
            out.append(f"- [{tag}] {h['name']} (weight {h['weight']}): {h['line']}")
    if not any_hit:
        out.append("None. No derived name appears on any watched page.")

    out += ["", "## New lines since last run"]
    for r in results:
        if r["first_run"]:
            out.append(f"### {r['watch']['label']}: first run, {len(r['new'])} lines "
                       f"taken as the baseline and not listed")
            continue
        if not r["new"]:
            continue
        cap = config["new_lines_per_watch"]
        out.append(f"### {r['watch']['label']} <{r['watch']['url']}> "
                   f"({len(r['new'])} new, showing {min(cap, len(r['new']))})")
        out += [f"- {x}" for x in r["new"][:cap]]

    text = "\n".join(out) + "\n"
    if len(text) > budget:
        text = text[:budget] + f"\n\n[cut at {budget} characters; run with --only <id> for the rest]\n"
    (STATE / "report.md").write_text(text)
    return text


def main():
    if not (STATE / "config.json").exists():
        sys.exit(f"No config.json in {STATE}. Lookout has nothing to run.")
    config = {**DEFAULTS, **json.loads((STATE / "config.json").read_text())}
    names = derive_names(config)
    if "--names" in sys.argv:
        for e in sorted(names.values(), key=lambda e: (-e["weight"], e["name"])):
            print(f"{e['weight']:>3}  {e['name']}")
        return

    watches = json.loads((STATE / "watches.json").read_text())
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
        watches = [w for w in watches if w["id"] == only]
    (STATE / "state").mkdir(exist_ok=True)
    today = date.today().isoformat()

    names_path = STATE / "state" / "names.json"
    before = set(json.loads(names_path.read_text())) if names_path.exists() else set()
    now = {e["name"] for e in names.values()}
    drift = {"added": sorted(now - before) if before else [],
             "removed": sorted(before - now)}
    names_path.write_text(json.dumps(sorted(now), ensure_ascii=False, indent=0))

    results = [run_watch(w, names, config, today) for w in watches]
    print(write_report(results, names, drift, config, today))


if __name__ == "__main__":
    main()
