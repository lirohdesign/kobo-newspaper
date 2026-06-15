# Framework — how the Reddit digest pipeline fits together

This describes the end-to-end shape of the system: what reads what, what gets
generated, and where state lives. `taste.md` is the rubric, `sources.json` is
the source map, `claude_scrape.md` is the runtime prompt that applies the
rubric to a day's candidates — this document is how those pieces connect into
a run (and an occasional second kind of run).

## The daily run, step by step

1. **Gather candidates.** For each subreddit in `sources.json`'s `daily`
   buckets, fetch via Reddit's unauthenticated `.json` endpoints (search or
   hot/top, depending on the bucket). Pull posts and their comment trees, and
   do a cheap pre-filter before anything reaches the API — drop one-line
   comments, sort by score, cap how many comments per thread get carried
   forward. This keeps the payload (and the token bill) reasonable and means
   the model spends its judgment on plausible candidates, not noise.

2. **Classify and summarize via the API.** One batched call (or one per
   bucket, whichever reads more cleanly in practice) hands the day's
   candidates to Claude along with `taste.md` (the rubric) and
   `claude_scrape.md` (the operating instructions for this specific task).
   For each candidate it returns:
   - a tier — **include** / **borderline** / **exclude**
   - a one-line reason for that call
   - for includes: a synthesized presentation — the post as brief context,
     plus the substantive comments worth carrying — not a raw dump

3. **Render.** Included items become a new section in the daily build,
   alongside weather / NYT / links — same `style.css`, same long-form HTML
   shape, organized by bucket so the structure stays legible.

4. **Persist.**
   - **Sent-hash log** (e.g. `sent_reddit.json`) — masked thread IDs, the
     same SHA-256 pattern used elsewhere in this project, so nothing repeats
     and nothing identifying ends up in logs.
   - **Near-miss log** (e.g. `reddit_near_misses.json`) — every
     **borderline** call: masked ID, subreddit, a one-line gist, the model's
     stated reason, timestamp. This is the calibration record. It's
     deliberately *not* a junk drawer of everything excluded — just the close
     calls, because that's where drift from your actual taste would show up
     first, long before the model started getting the easy calls wrong.

## Seasonal / triggered buckets

Each run also does a cheap check against `sources.json`'s `seasonal` entries —
is today inside (or near) one of the listed `windows`, or does a keyword match
("Booker," "Nobel," "IPCC") turn up live discussion? If so, that bucket runs
through the same classify-and-render path for this run only. Most days this
check costs almost nothing and finds nothing — that's expected, not a bug.

## The calibration digest — periodic, not daily

On a set cadence (weekly is a reasonable starting point; adjust once you see
how fast the near-miss log actually fills up), generate a short digest *from
the near-miss log*: a handful of the borderline calls and the model's stated
reasoning for each, presented the same long-form way as everything else, and
delivered to Instapaper like any other section.

This is the calibration mechanism, and it exists because of a real structural
gap: Instapaper is a one-way, static delivery surface — there's no
like/dismiss/engagement signal coming back. The only way to know whether the
model's threshold matches yours is to periodically *look at the close calls
and the reasoning behind them*. Putting that review inside the same long-form
reading habit you already have is what makes it likely to actually happen,
rather than turning into a JSON file you mean to open someday and don't.

## Access wall — Reddit data is currently blocked

This has been investigated and hit real structural limits, not code problems.

- **Unauthenticated `.json` endpoints** — hard 403 from Reddit's servers. This
  was broadly blocked after Reddit's 2023 API policy changes. No amount of
  User-Agent tuning fixes it.
- **OAuth API (script app)** — applied for personal/script access and was
  denied.
- **RSS feeds** (`.rss`)  — still serve, but give only titles, post text, and
  links. No comment data.

Without comments, the core value of this digest evaporates. The design in
`framework.md` is built around practitioner comments, corrections, and
on-the-ground reports — the post title alone isn't the signal, the thread is.
RSS-only would produce a link list indistinguishable from a Google alert.

Third-party options investigated:
- **Pullpush.io / Arctic Shift** — community Pushshift replacements; provide
  post and comment data but reliability has been inconsistent and they have
  no SLA.
- **Apify** — paid scraping platform with a Reddit actor; would work
  technically but adds cost and a dependency on a third party staying
  unblocked.
- **SerpApi / Google Custom Search** — surfaces Reddit threads via Google
  search; gives snippets and links, not full thread content or comments.
- **AI browsing (Perplexity API, etc.)** — could synthesize Reddit discussion
  from web search results, but you'd be getting the model's summary of a
  summary, not actual thread content. Drift from reality compounds quickly and
  there's no way to know when it's happening.

**Current status: parked.** The Reddit digest spec (`taste.md`,
`claude_scrape.md`, `sources.json`) remains valid if access ever becomes
feasible. Don't re-investigate the unauthenticated endpoint or RSS-only paths
— those dead ends are documented above.

## Calendar and event scrapers

The daily build includes a **section 05 calendar**, driven by `calendar.json`.
This is how the project handles content that clusters around known events
rather than arriving daily — Purdue ag reports, literary prizes, major
institutional releases.

### How a run uses the calendar

Each run reads `calendar.json` and evaluates every entry against today's date.
Events fall into one of three states:

- **Due today** — rendered as an active card in section 05, with either scraped
  content or a fallback notice (see below). This is what gets read.
- **Upcoming within 14 days** — listed under an "upcoming" subhead. Serves as
  a heads-up so the next few days feel expected, not surprising.
- **Outside the window** — silently skipped.

### Trigger types

| Trigger | Fires when | Example |
| :--- | :--- | :--- |
| `first_tuesday_monthly` | First Tuesday of each month (±1 day) | Ag Economy Barometer |
| `annual_window` | Current month is in the `months` array | Booker longlist (July), Nobel (October) |
| `manual` | Today matches a date in the `dates` array (±1 day) | IPCC releases, FOMC dates |

For `manual` entries, add dates as `"YYYY-MM-DD"` strings to the `dates` array
in `calendar.json` when they become known. FOMC dates are published a year in
advance at federalreserve.gov; IPCC release dates are announced months ahead.

### Timing language

Due events always show a timing label — "today", "tomorrow", "in 3 days",
"next week", "this month" — so the reading context is always clear. The label
is generated from the trigger, not hardcoded, so it stays accurate.

### The fallback is the feature

Not every event has a scraper. For events that do, the scraped content
replaces the fallback. For events that don't — and for any event whose scraper
fails or returns empty — the calendar always surfaces a card that says:

> **Booker Prize Longlist** — this month  
> No automated fetch available. [Check thebookerprizes.com →]

This is intentional. The goal is to make sure the event reaches you even when
automation can't do the full job. A reliable reminder with a direct link is
more useful than silence. Don't remove the fallback path in pursuit of a
"cleaner" output when a scraper is present — the fallback is what makes the
system robust when scrapers break.

### Adding a scraper for a calendar entry

1. Write a Python module with a `collect()` function that returns an HTML
   string (or empty string on failure). Follow the pattern in
   `barometer_scrape.py`.
2. Set `"scraper": "your_scrape.py"` on the entry in `calendar.json`.
3. The calendar system dynamically imports and calls `collect()` when the
   trigger fires. No changes to `main.py` needed.

### Verifying the calendar is working

Because event triggers are date-dependent, they're hard to test in a dry run.
The most reliable verification is to check the archive after a trigger date
has passed:

1. Open `old_issues/` and find the file dated on or just after the expected
   trigger date (e.g. the first Tuesday of the month for the Barometer).
2. Search for the event label (e.g. "Purdue Ag Economy Barometer") in that
   file. If it's present with scraped content, the scraper ran. If it's
   present with "Check source →", the fallback fired (scraper failed or
   absent). If it's absent entirely, the trigger didn't fire — check the
   date logic and the `calendar.json` entry.

See `claude.md` for a specific verification checklist a future session can
follow.

## Future development

**Pipeline ideas** — music/listening guide as a newspaper section;
playlist pipeline to Spotify (highlights or vocabulary lookups → playlist);
multilingual vocabulary section (English / French / Portuguese); kids
newspaper edition for a 5-year-old (separate Instapaper account).

**Local venues — films and concerts** — scrape local venue calendars and
add upcoming films and concerts as a daily section. `cinema_scrape.py`
handles cinema; extend to concerts. Cinema entries should prioritize
showtime dates over description text.

**Crossword or word puzzle** — a format native to e-reader constraints
(text-based, no graphics dependency). Better than a standard crossword grid
for epub; to be scoped further.

**Delivery timing** — issues should arrive by 6:30 AM; currently arriving
at 10 AM or later. Check the cron schedule and whether the GitHub Actions
runner timezone is set correctly.

## What lives where

| Concern | Lives in |
| :--- | :--- |
| What counts as signal, what to filter, format constraints | `taste.md` |
| Which subreddits, which bucket, daily vs. seasonal, and why | `sources.json` |
| The runtime prompt — how to apply the rubric to a batch of candidates | `claude_scrape.md` |
| How the pieces connect into a run, end to end | this file |
| Maintenance guidance for future work on this system | `claude.md` |
