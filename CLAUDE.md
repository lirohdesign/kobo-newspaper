# CLAUDE.md — maintenance guide

This orients a future Claude Code session working on this project. Read it first — it tells you which file to change for which kind of request, and documents the decisions and dead ends that cost real time to arrive at.

The full architecture is in `framework.md`. Read that too before touching anything structural.

* * *

## Standard build — what to change for what

- *"Stop showing me X" / "I want more Y" / "this thread isn't landing"* → **`taste.md`**. Rubric problem, not code. Fix the rubric; the prompt that defers to it follows automatically.
- *"Add/remove a subreddit" / "this DRAFT source isn't working"* → **`sources.json`**.
- *New bucket type, new cadence, new persisted log, anything structurally different* → **`framework.md`** first (keep the architecture true), then the code.
- *"Model output is inconsistent / wrong shape"* → **`claude_scrape.md`**. Don't add Python post-processing to paper over bad output — fix the prompt.

* * *

## Kids build — what to change for what

- *"Section X isn't working / needs changing"* → the module for that section. See the section-to-module table in `framework.md`.
- *"I want to add a new section"* → write a module that returns an HTML string (or a `(content, answers)` tuple if there are answers), import it in `kids_main()`, add a `<section>` to the page template, add to answers assembly if needed.
- *"Change the math difficulty or style"* → **`math_generator.py`**. Subtraction is deliberately no-borrow (each digit of subtrahend ≤ matching digit of minuend). Addition allows carrying. Don't break this without re-reading the design intent.
- *"Add vocabulary words"* → **`language_bank.json`**. Follow the existing schema. Words with French articles (`l'`, `le`, `la`, `les`) or Portuguese articles (`o`, `a`, `os`, `as`) are handled automatically by `_with_article()` in `language.py`. Check the function before adding words with unusual article patterns.
- *"Change puzzle difficulty / appearance"* → **`towers.py`** or **`guess.py`**. Both use date-seeded RNG (seeds differ by +11 and +22). If you change `SHAPES`, `N`, or grid size, re-read the rendering pipeline in `framework.md` — font sizes, cell dimensions, and the 70% resize target interact.
- *"APOD isn't appearing"* → check `apod_scrape.py`. The API at `api.nasa.gov` is unreliable; the scraper has retries + web fallback. If the web fallback also fails, the page structure at `apod.nasa.gov` may have changed — fetch the URL manually and inspect it.

* * *

## One-off specials — confirmed working pattern (2026-07-08)

For a same-day special edition (first proof: the kids Indianapolis Zoo special, confirmed delivered to the device in under 12 minutes from request), don't touch `main.py` or the daily workflows. Instead:

1. **Static page** at repo root (e.g. `zoo-special.html`), committed to `main`, following all the Kobo rendering rules below (explicit `<title>`, `<ul><li><strong>` for labelled lists, JPEG images at absolute URLs with date-stamped filenames).
2. **Images in a committed dir** (e.g. `zoo/`) — *not* `puzzles/`, which is untracked-on-main by convention. Wikipedia REST API (`/api/rest_v1/page/summary/{Page}`) gives a lead image per species; Wikimedia rate-limits (429) and rejects arbitrary thumb sizes (400) — retry with backoff and fall back to the original file URL, then resize to ≤560px wide JPEG via Pillow.
3. **One-off workflow** (`.github/workflows/zoo-special.yml` is the template) triggered `on: push: paths: [<the page>]` — this self-triggers on the push that adds it, so no `gh` CLI needed locally. Steps: checkout → sync `old_issues/` from gh-pages → peaceiris deploy → **poll the live URL until it serves the new content** → curl the Instapaper API with the repo secrets. The send-after-deploy ordering matters; the daily builds send before deploy and get away with it, but a brand-new URL must be live before Instapaper fetches it.
4. Trigger paths are scoped to the special page, so the workflow is inert afterward — safe to leave or delete.

* * *

## Instapaper / Kobo rendering — standing rules

These were learned through repeated live testing. Violating them causes silent failures that are only visible on the physical device.

**Images:**
- Use **JPEG only**. PNG renders in browser and Instapaper web view but appears as a blank icon on Kobo via Instapaper offline delivery. APOD (JPEG) is the confirmed proof case.
- Use **absolute URLs** (`https://lirohdesign.github.io/kobo-newspaper/puzzles/…`). Relative paths work in a browser but Instapaper's Kobo offline pipeline does not resolve them at cache time.
- **Date-stamp image filenames** (`towers-2026-06-16.jpg`). Instapaper caches by URL — a fixed filename serves the first day's image forever.

**Text formatting:**
- `<strong>` inside `<li>` **works** on Kobo. `<strong>` inside `<p>` **does not** reliably bold on Kobo — Instapaper strips CSS bold when delivering to device.
- Use `<ul><li>` structure for labelled lists where bold labels matter. The language module (`language.py`) does this deliberately — don't "simplify" it to `<div><p>`.
- **SVG is stripped by Instapaper entirely.** Never use inline SVG for content. Render to JPEG via Pillow instead.
- **CSS is stripped on Kobo.** Style-critical formatting must be in semantic HTML, not class-based CSS.
- **Flag emoji are stripped.** Don't use them for meaningful content.

**Cache busting:**
- Always append `?v={ts}` to page URLs sent to Instapaper. Without it, Instapaper may serve a stale cached version of the page.
- Every generated page needs an explicit `<title>` tag in `<head>`, matching the `<h1>`. None of them had one — Instapaper fell back to parsing the `<h1>` for its title, and that fallback appears to cache more stubbornly than body content: `?v={ts}` refreshed the displayed content correctly but the bookmark's title metadata stayed pinned to a previous day's value. Fixed across all 7 page builders in `main.py` 2026-06-18.

* * *

## The calibration loop (Reddit digest, when active)

Because Instapaper gives no feedback, the **near-miss log** and periodic **calibration digest** (both described in `framework.md`) are how drift gets caught. If asked to "tune" the system, read recent `borderline` calls and their reasons first — that's the evidence. A pile of correctly-rejected garbage proves nothing; the close calls are where real signal lives.

* * *

## Dead ends — don't re-investigate

**Reddit data access** — unauthenticated `.json` endpoints are hard-blocked (403) since Reddit's 2023 API changes. OAuth script app was applied for and denied. RSS works but gives no comment data, which is the entire signal. Third-party scrapers (Pullpush, Apify, SerpApi) have reliability or depth problems. The spec remains valid; the access problem does not have a code fix. See `framework.md` for the full investigation record.

**Substack sync** (`project_substack_sync_blocked.md`) — died to IP-based bot blocking from GitHub Actions runners. Cloudflare 403s the runner IPs regardless of headers or retry logic. This is a hosting problem, not a code problem. If the Reddit fetch ever starts returning 403s from Actions, check for the same structural wall before assuming it's fixable.

**AI content in the Reddit digest** — excluded from automation. "Rare, structurally significant AI event" is a detection problem an LLM-scoring-Reddit-volume approach gets wrong: high comment velocity tracks alarmist noise as readily as real signal. Guardian/NYT sources carry this. Don't reopen without genuinely new information.

**Booker/Nobel/major-report as daily content** — seasonal, not daily. Forcing it into the daily rotation produces mostly-empty runs punctuated by floods. The `seasonal` entries in `sources.json` plus window/keyword check are the intended mechanism.

* * *

## Verifying the calendar system

Calendar triggers are date-dependent and can't be tested in a dry run. To verify:

1. Find the expected trigger date (first Tuesday of month for Barometer; first day of window month for annual events; listed date for manual entries).
2. Open `old_issues/` and find the `.html` file dated on or just after that date.
3. Search for the event `label` from `calendar.json`. Three outcomes:
   - **Scraped content present** — working.
   - **"Check source →" fallback** — trigger fired, scraper failed or returned empty. Check the scraper and source URL.
   - **Label absent** — trigger didn't fire. Check `calendar.json` date logic and whether the archive file exists at all.

Don't test by running the scraper in isolation against today's page — the page may have changed since the trigger date. The archive is the ground truth.

* * *

<!-- kobo-loader:start -->
## Kobo pipeline

This project's `.md` files are converted to epub by kobo-loader and synced
to a Kobo e-reader; any `.pdf` found anywhere in this tree is symlinked in
and synced unconverted (Kobo renders PDFs natively). One formatting rule
applies to all `.md` files here:

**Use `* * *` for horizontal rules — never `---` in the document body.**
Pandoc treats standalone `---` as a YAML block opener; `*bold*` or `*italic*`
after it triggers a parse error. YAML front matter at the very top is fine.

To exclude a file or folder from the sync, list it in `.koboignore` at this
project's root — gitignore-style, one glob pattern per line, `#` for
comments. kobo-loader only reads this file; it's yours to edit.

If `KOBO.md` is present in this directory, read it at session start.
Generated by kobo-loader (`python3 kobo_notes.py kobo-newspaper`), it contains
pending notes captured while reading this project's docs on the Kobo
device. Gitignored and regenerated on each run — do not edit it. To
resolve a note: add its ID to `.kobo_resolved.json` (also gitignored).
<!-- kobo-loader:end -->
