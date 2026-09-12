---
name: research-digest
description: Weekly research-monitor session — repair broken scrapers, curate sources, and synthesize the digest that becomes research.html in the daily newspaper. Run this on Tuesdays (or whenever triggered manually) after research_pull.py's daily cron has been feeding research_data/. Use for "run the research digest", "do the Tuesday research check", "update the research page".
---

This is the judgment half of the research pipeline. `research_pull.py` (via a
daily GitHub Actions cron) does the mechanical fetching unattended — RSS
pulls and a couple of direct-API/structured-scrape sources, no Claude
involved, so there's no permission wall to hit. This skill is the interactive
half: repair what broke, curate what's worth tracking, and write the actual
synthesis a human should read. See `CLAUDE.md` for the fuller rationale if
you haven't read it yet.

## 0. Sync first

`research_data/` is committed straight to `main` by the cron workflow
(`.github/workflows/research-pull.yml`), not synced through gh-pages like
the rest of this project's generated content. Run `git pull` before anything
else — otherwise you're validating/curating against stale local data.

## 1. Repair — run the pre-flight, fix what it flags

```
python3 research_validate.py
```

This checks freshness (did the cron actually run in the last ~48h) and
schema (non-empty items, valid dates/links) per source, and lists any
discovery candidates. Exit code is non-zero if anything needs attention.

For each problem it reports:

- **Stale / error status** — first suspect is the cron itself, not the
  scraper: check recent runs of the `Research Pull` GitHub Action before
  assuming the site changed. If the site did change, fetch the live page
  yourself (WebFetch — you have it interactively, no reason to guess) and
  compare against what the scraper is currently producing. Fix the parser,
  then re-run `python3 research_pull.py` and re-run `research_validate.py`
  to confirm the fix actually holds, not just that it no longer crashes.
- **Bad schema (blank title/date, invalid link)** — same approach: look at
  the live source, figure out what changed, fix the specific scraper
  (`research_pull.py`'s `fetch_feed()` for RSS sources, or the relevant
  `*_scrape.py` module for the direct-fetch ones).
- Commit a genuine repair as its own commit, separate from this week's
  digest content — makes it easy to see later whether a given week's
  digest was affected by a mid-week fix.

If everything's healthy, say so briefly and move on — don't manufacture
concern where there isn't any.

## 2. Curate — evidence-based, not vibes-based

**Cuts:** A source looking quiet or low-value *this* week isn't enough on
its own — newsletters have slow weeks. Check `research_data/history/<id>.jsonl`
for a pattern across several weeks before proposing a cut. Log the
observation either way (even if you don't act on it yet) by appending a line
to `research_data/curation_log.jsonl`:
```json
{"date": "2026-09-16", "action": "flag_low_value", "target": "data_center_dynamics", "reason": "3 of last 4 weeks were sponsored/off-topic content with nothing DC-siting-relevant"}
```
Only recommend an actual cut to the user once the log shows a real pattern —
don't remove a source from `research_sources.json` unilaterally.

**Additions:** `research_validate.py`'s discovery-candidate list surfaces
domains cited repeatedly across multiple existing sources' own content
(footnotes/citations), pulled from `research_data/discovered_sources.json`.
A domain crossing that threshold is evidence worth a look, not an automatic
add — check what it actually is (some will be generic references like
`arxiv.org` or `wikipedia.org`, not newsletter-shaped sources worth
tracking) before proposing it. Log proposals the same way, `action:
"propose_add"`. If you and the user agree on a real addition, verify it has
an actual usable feed (same process as the original build: check for `/feed`,
`/rss`, or a structured JSON endpoint before committing to it — see
`research_sources.json`'s per-source `notes` fields for the gotchas already
found this way, e.g. Zitron's unreliable description field, the Drought
Monitor API needing a FIPS code not a state abbreviation).

## 3. Synthesize

Read `research_data/<id>.json` (latest pull) and, for sources worth checking
against their own past, `research_data/history/<id>.jsonl` (does this week's
claim/tone match what was said before, under what conditions — e.g. does a
sentiment reading make sense against what was actually happening at the time
of a past similar reading, not just "sounds similar").

Write `research_notes.json` at the repo root — a flat object keyed by source
id:
```json
{
  "epoch_ai": {"synthesis": "One or two sentences of real synthesis, not a restated headline.", "as_of": "2026-09-16"},
  "drought_monitor": {"synthesis": "...", "as_of": "2026-09-16"}
}
```
Only include sources you actually have something synthesized to say about —
`research_scrape.py` falls back to a plain raw-item link for anything
missing from this file, which is a fine outcome for a quiet source, not a
failure to paper over.

Self-check before finalizing: for every factual claim in a `synthesis`
string, could you point to the specific item/link in `research_data/` (or
`research_data/history/`) it came from? If not, it's either not verified
closely enough or drifting from what the source actually said — fix the
wording, don't ship it as-is. Flag explicitly (in the synthesis text itself)
if a source's latest item is older than its cadence implies — a weekly
source with a 3-week-old top item should say so, not be presented as
current.

## 4. Render and land

```
python3 research_scrape.py
```
writes `research.html` from `research_notes.json` + `research_data/`. Check
it rendered what you expect, then commit `research.html` and
`research_notes.json` together (this is editorial content, committed to
`main` directly — same pattern as `zoo-special.html`, unlike the routine
daily/kids builds which are pure generated artifacts that never get
committed). **Confirm with the user before pushing** — this becomes part of
the next daily build and gets sent to Instapaper, so it's not something to
push silently on autopilot.

## 5. Close with a short self-report

A few lines: sources checked, anything repaired, any curation flags logged
(even if not acted on), and the as-of dates in this week's synthesis. This
is the audit trail — there's no other feedback loop on this pipeline once
it's on the Kobo device, so this report is what lets a "was the digest
right" question get answered later.
