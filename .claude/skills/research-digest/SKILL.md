---
name: research-digest
description: Weekly research-monitor session — repair broken scrapers, curate sources, and synthesize the digest that becomes research.html in the daily newspaper. Run this on Tuesdays (or whenever triggered manually) after research_pull.py's daily cron has been feeding research_data/. Use for "run the research digest", "do the Tuesday research check", "update the research page".
---

This is the judgment half of the research pipeline. `research_pull.py` (via a
daily GitHub Actions cron) does the mechanical fetching unattended — RSS
pulls and a couple of direct-API/structured-scrape sources, no Claude
involved, so there's no permission wall to hit. This skill is the interactive
half: repair what broke, curate what's worth tracking, and write the actual
synthesis a human should read. What the research section is for, and what
earns a source a place in it, is the next section; read it before curating.

## Purpose and admission standard

The section exists for consistent readings over time, not good prose: "the goal
is not NYT quality prose. the goal is consistent readings so after 10 years, I
feel the state of things and I know the indicators."

Admission is defined in the private file
`~/Documents/meta-ai/research-invariants.md`: the axiom and source classes
(§1), the declared concerns and the familiar places B (§2), and lead intake
(§3). Read it before curating. It governs; the notes below are the
maintainer's earlier words and give way to it where they differ.

- **The question is the criterion.** The maintainer's questions are not bounded
  by any repo. Their research repos "are only 'introductions' to the nagging
  questions" — "first attempts to poke at the available data myself (a
  non-expert)." A repo is never the criterion or ground truth for a source.
- **A well-formed source** is "written by experts studying the same things I am
  verifying on my own," "unlikely to be picked up by national or international
  news," and "designed for and read by industry/research experts." The Purdue
  sources are "good examples of well-formed"; "IPCC publications are also
  important sources."

**Not everything here is weekly.** `research_sources.json` now mixes
weekly-, monthly_digest-, and monthly-cadence sources (Stage 2), and
`research_calendar.json` holds a separate set of quarterly/annual,
calendar-triggered sources (Stage 3) rendered into research.html's
"Quarterly / annual watch" section via the same `collect_calendar()`
mechanism as `calendar.json`. Don't assume every source needs fresh
synthesis every single Tuesday:
- `research_validate.py`'s freshness check is now cadence-aware (reads each
  source's `cadence` field and sizes the allowed staleness window
  accordingly) — trust its output rather than eyeballing whether a
  monthly-cadence source's item "looks old"; a monthly source returning the
  same item for 3+ weeks is expected, not a problem, unless validate flags
  it stale for *its own* cadence.
- A `monthly_digest`-cadence source (e.g. Equitable Growth, Aspen FSP) is
  fine to skip a real synthesis update on a week where nothing new and
  notable has posted — same logic as `farmdoc_daily`'s weekly-digest
  treatment, just on a longer clock.
- Stage 3 (research_calendar.json) entries mostly have no scraper — they're
  a due-date reminder with a "check source" link, rendered by `main.py`'s
  `collect_calendar()`. A `research_notes.json` entry keyed by an event's
  `id` is never shown: `research_scrape.py` renders notes only for ids in
  `research_sources.json`, and `collect_calendar()` doesn't read notes. The
  same holds for `calendar.json`'s Purdue entries. When an event is active,
  read the actual release and record its reading in
  `research_data/curation_log.jsonl` — `{"date": ..., "action":
  "calendar_reading", "target": "<event id>", "reason": "<published figure,
  period it covers, link>"}` — so later sessions can walk back through the
  series. Mention it in the session report; it won't appear on the page.

## 0. Sync first

`research_data/` is committed straight to `main` by the cron workflow
(`.github/workflows/research-pull.yml`), not synced through gh-pages like
the rest of this project's generated content. Run `git pull` before anything
else — otherwise you're validating/curating against stale local data.

The cron runs 4:30 PM CT so Monday's pull includes NASS Crop Progress
(posted Mondays 4 PM ET). Check that it actually ran since then:
`gh run list --workflow=research-pull.yml -L 1`. If the latest run started
before Monday 20:00 UTC (GitHub's scheduler can slip or skip), trigger one
with `gh workflow run research-pull.yml`, wait for it
(`gh run watch`), then `git pull` again.

Then read the recent tail of `research_data/curation_log.jsonl`
(`tail -n 20`), including prior `session_report` lines and any
`maintainer_correction` and `lead_verdict` lines, before repairing or curating. The log is how
one session's lessons reach the next.

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
- Commit a genuine repair on its own `fix/` branch off `main`, separate from
  this week's digest content — makes it easy to see later whether a given
  week's digest was affected by a mid-week fix. Land it as in step 4.

If everything's healthy, say so briefly and move on — don't manufacture
concern where there isn't any.

Known cases, so they don't get re-diagnosed each week:

- **epoch_ai 403** — Substack blocks GitHub Actions IPs. Not a scraper bug;
  fetch `https://epochai.substack.com/feed` directly this session and
  synthesize from that.
- **API-key sources (NASS, NOAA)** — keys live only in GitHub secrets, not
  locally. To inspect raw API rows, add a temporary `workflow_dispatch`
  workflow that prints them, run it with `gh workflow run` / `gh run watch`,
  then delete the workflow in the same session.
- **NASS week looks stale** — check whether Quick Stats actually has the
  week before touching the scraper (past weeks loaded Mondays 16:00; some
  weeks post late). If the API doesn't have it, say so in the synthesis.
- **Local Python has no certifi** — ad-hoc fetch scripts should use plain
  `urllib` without it.

## 2. Curate — evidence-based, not vibes-based

**Standard reviews:** each week, review 2–3 sources against
`research-invariants.md` §1–2 — the ones whose latest `standard_review` line in the log is
oldest, or that have none (`grep standard_review research_data/curation_log.jsonl`).
This is sized for a token-limited session, not a full audit. Log each:
```json
{"date": "2026-09-29", "action": "standard_review", "target": "<id>", "reason": "<verdict>: <class>; <qualities met / missed>"}
```
The reason gives the verdict (keep / cut candidate / needs maintainer view),
the source's class (witness / feed / compiled / check / excluded), and which qualities it meets or
misses. For the honest-null check, read
`research_data/history/<id>.jsonl` for weeks when the underlying thing was
quiet: did the source report the metrics plainly, or fill space?

**Slow-moving sources.** For a source whose underlying thing changes slowly
(e.g. interconnection_fyi's Indiana project counts), an unchanged snapshot is
the source doing its job, not a low-value flag. Judge it on whether it would
show the change when it comes, not on week-to-week movement.

**Scope:** `calendar.json`'s Purdue research entries (`ag_barometer`,
`purdue_farmland`, `purdue_crop_costs`) are in scope for standard reviews, and
for reading when active, even though they render in the daily paper's calendar
section, not research.html.

**Cuts:** A source looking quiet or low-value *this* week isn't enough on
its own — newsletters have slow weeks. Check `research_data/history/<id>.jsonl`
for a pattern across several weeks before proposing a cut. Log the
observation either way (even if you don't act on it yet) by appending a line
to `research_data/curation_log.jsonl`:
```json
{"date": "2026-09-16", "action": "flag_low_value", "target": "data_center_dynamics", "reason": "3 of last 4 weeks were sponsored/off-topic content with nothing DC-siting-relevant"}
```
Only recommend an actual cut to the user once the log shows a real pattern and
the user agrees — don't remove a source from `research_sources.json`
unilaterally.

**Additions:** `research_validate.py`'s discovery-candidate list surfaces
domains cited repeatedly across multiple existing sources' own content
(footnotes/citations), pulled from `research_data/discovered_sources.json`.
A domain crossing that threshold is evidence worth a look, not an automatic
add — judge it against the admission standard, not just whether it's
newsletter-shaped. If the list is all generic press/corporate/academic hosts
(`arxiv.org`, `wikipedia.org`), one log line saying so is enough. Log
proposals the same way, `action: "propose_add"`; additions need the user's
agreement. If you and the user agree on a real addition, verify it has an
actual usable feed (same process as the original build: check for `/feed`,
`/rss`, or a structured JSON endpoint before committing to it — see
`research_sources.json`'s per-source `notes` fields for the gotchas already
found this way, e.g. Zitron's unreliable description field, the Drought
Monitor API needing a FIPS code not a state abbreviation).

**Leads:** when the maintainer brings a lead, or you find one, run §3 of
`research-invariants.md`. First read the earlier lead lines
(`grep '"action": "lead' research_data/curation_log.jsonl`). Classify, scout,
log, then stop: collecting, classifying and scouting need no verdict; adding a
source, a variable, a method change or a concern does. Log the scouting:
```json
{"date": "...", "action": "lead", "target": "<lead-slug>", "brought_by": "maintainer | agent", "link": "<url>", "kind": "trend | framework", "inventory": [{"source": "...", "measures": "...", "cadence": "...", "class": "witness | feed | compiled | check | excluded"}], "gaps": ["..."], "reason": "<what the lead proposes to change>"}
```
A framework lead has an empty `inventory` and `gaps`; its `reason` names the
repo or method it changes. Log the maintainer's verdict when given:
```json
{"date": "...", "action": "lead_verdict", "target": "<lead-slug>", "verdict": "kept | dropped", "reason": "<the maintainer's one-line reason>"}
```
Your hit rate is kept ÷ brought, over leads with `"brought_by": "agent"`.

## 3. Synthesize

Read `research_data/<id>.json` (latest pull) and, for sources worth checking
against their own past, `research_data/history/<id>.jsonl` (does this week's
claim/tone match what was said before, under what conditions — e.g. does a
sentiment reading make sense against what was actually happening at the time
of a past similar reading, not just "sounds similar").

Write `research_notes.json` at the repo root — a flat object keyed by source
id (only ids in `research_sources.json` render; calendar events are recorded
in the log instead, see the Stage 3 note above):
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

Stored `summary` fields are truncated (~300 chars), which is enough to
triage but not to synthesize. Fetch the actual article for anything you
write more than a headline about.

`as_of` is the date of the newest source item the note is built on, not
today's date — the page renders it as "N days ago · synthesized <date>" so
the reader can tell at a glance whether they've already read it. Monthly
data uses `YYYY-MM`.

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
`research_notes.json` together (this is editorial content, unlike the routine
daily/kids builds which are pure generated artifacts that never get
committed). Commit on a fresh branch off `main` (e.g.
`docs/research-digest-YYYY-MM-DD`), squash-merge to `main`, then push.
**Confirm with the user before pushing** — this
becomes part of the next daily build and gets sent to Instapaper, so it's not
something to push silently on autopilot.

## 5. Publish

After the user confirms the push, start the daily build rather than waiting
for GitHub's scheduler (which has been starting it 3-5 hours late):

```
gh workflow run daily.yml
gh run watch $(gh run list --workflow=daily.yml -L1 --json databaseId -q '.[0].databaseId')
```

Only the first build of each day sends to Instapaper (main.py skips the send
if `old_issues/<today>.html` already exists on gh-pages). Check
`gh run list --workflow=daily.yml -L1` first: if today's build already ran,
this one only refreshes the website, and the digest reaches the Kobo with
tomorrow's issue. Tell the user which case applies.

## 6. Close with a short self-report

A few lines to the user: sources checked, anything repaired, any curation flags,
standard reviews and leads logged (even if not acted on), and the as-of dates in this
week's synthesis. Also append it to `research_data/curation_log.jsonl` as one
line with `"action": "session_report"`, and append each correction the
maintainer made during the session as its own `"action":
"maintainer_correction"` line. The log is what the next session reads, and
there's no other feedback loop on this pipeline once it's on the Kobo device.

If a correction is a standing rule, propose the exact skill-text edit to the
maintainer in-session and, if they agree, make it on a `docs/` branch.
