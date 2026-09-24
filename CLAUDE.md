# kobo-newspaper CLAUDE.md

The full architecture is in `framework.md`. Read that too before touching
anything structural.

* * *

## Instances

- *"Model output is inconsistent / wrong shape"* → `claude_scrape.md`. Don't add Python post-processing to paper over bad output — fix the prompt. (T2)
- The Instapaper/Kobo rendering rules (under Conventions) were each learned by observing the pipeline fail on-device and confirming the fix the same way. (T2)
- If asked to "tune" the system, read recent `borderline` calls and their reasons first — a pile of correctly-rejected garbage proves nothing; the close calls are where real signal lives. (T2)
- Verifying the calendar system: check the archived page in `old_issues/` for the trigger date — don't test by re-running the scraper against today's page, which may have changed since. The archive is the ground truth. (T4)
- Dead ends and investigation history: see `framework.md` for the full record — not restated here. (T4)

## Extensions

- Kobo pipeline: listed in kobo-loader's `projects.local.json`; read `KOBO.md` at session start if present. (extensions/kobo.md)

## Conventions

### Standard build — what to change for what

- *"Stop showing me X" / "I want more Y" / "this thread isn't landing"* →
  `taste.md`. Rubric problem, not code. Fix the rubric; the prompt that
  defers to it follows automatically.
- *"Add/remove a subreddit" / "this DRAFT source isn't working"* →
  `sources.json`.
- *New bucket type, new cadence, new persisted log, anything structurally
  different* → `framework.md` first (keep the architecture true), then the
  code.
- *"Model output is inconsistent / wrong shape"* → `claude_scrape.md`.

### Kids build — what to change for what

- *"Section X isn't working / needs changing"* → the module for that
  section. See the section-to-module table in `framework.md`.
- *"I want to add a new section"* → write a module that returns an HTML
  string (or a `(content, answers)` tuple if there are answers), import it
  in `kids_main()`, add a `<section>` to the page template, add to answers
  assembly if needed.
- *"Change the math difficulty or style"* → `math_generator.py`. Subtraction
  is deliberately no-borrow (each digit of subtrahend ≤ matching digit of
  minuend). Addition allows carrying. Don't break this without re-reading
  the design intent.
- *"Add vocabulary words"* → `language_bank.json`. Follow the existing
  schema. Words with French articles (`l'`, `le`, `la`, `les`) or Portuguese
  articles (`o`, `a`, `os`, `as`) are handled automatically by
  `_with_article()` in `language.py`. Check the function before adding
  words with unusual article patterns.
- *"Change puzzle difficulty / appearance"* → `towers.py` or `guess.py`.
  Both use date-seeded RNG (seeds differ by +11 and +22). If you change
  `SHAPES`, `N`, or grid size, re-read the rendering pipeline in
  `framework.md` — font sizes, cell dimensions, and the 70% resize target
  interact.
- *"APOD isn't appearing"* → check `apod_scrape.py`. The API at
  `api.nasa.gov` is unreliable; the scraper has retries + web fallback. If
  the web fallback also fails, the page structure at `apod.nasa.gov` may
  have changed — fetch the URL manually and inspect it.

### One-off specials

For a same-day special edition, don't touch `main.py` or the daily
workflows. Instead:

1. **Static page** at repo root (e.g. `zoo-special.html`), committed to
   `main`, following the Instapaper/Kobo rendering rules below (explicit
   `<title>`, `<ul><li><strong>` for labelled lists, JPEG images at absolute
   URLs with date-stamped filenames).
2. **Images in a committed dir** (e.g. `zoo/`) — *not* `puzzles/`, which is
   untracked-on-main by convention. Wikipedia REST API
   (`/api/rest_v1/page/summary/{Page}`) gives a lead image per species;
   Wikimedia rate-limits (429) and rejects arbitrary thumb sizes (400) —
   retry with backoff and fall back to the original file URL, then resize
   to ≤560px wide JPEG via Pillow.
3. **One-off workflow** (`.github/workflows/zoo-special.yml` is the
   template) triggered `on: push: paths: [<the page>]` — this self-triggers
   on the push that adds it, so no `gh` CLI needed locally. Steps: checkout
   → sync `old_issues/` from gh-pages → peaceiris deploy → poll the live
   URL until it serves the new content → curl the Instapaper API with the
   repo secrets. The send-after-deploy ordering matters; the daily builds
   send before deploy and get away with it, but a brand-new URL must be
   live before Instapaper fetches it.
4. Trigger paths are scoped to the special page, so the workflow is inert
   afterward — safe to leave or delete.

### Instapaper / Kobo rendering — standing rules

Violating these causes silent failures that are only visible on the
physical device.

**Images:**
- Use **JPEG only**. PNG renders in browser and Instapaper web view but
  appears as a blank icon on Kobo via Instapaper offline delivery.
- Use **absolute URLs**
  (`https://lirohdesign.github.io/kobo-newspaper/puzzles/…`). Relative
  paths work in a browser but Instapaper's Kobo offline pipeline does not
  resolve them at cache time.
- **Date-stamp image filenames** (`towers-2026-06-16.jpg`). Instapaper
  caches by URL — a fixed filename serves the first day's image forever.

**Text formatting:**
- `<strong>` inside `<li>` **works** on Kobo. `<strong>` inside `<p>`
  **does not** reliably bold on Kobo — Instapaper strips CSS bold when
  delivering to device.
- Use `<ul><li>` structure for labelled lists where bold labels matter. The
  language module (`language.py`) does this deliberately — don't "simplify"
  it to `<div><p>`.
- **SVG is stripped by Instapaper entirely.** Never use inline SVG for
  content. Render to JPEG via Pillow instead.
- **CSS is stripped on Kobo.** Style-critical formatting must be in
  semantic HTML, not class-based CSS.
- **Flag emoji are stripped.** Don't use them for meaningful content.

**Cache busting:**
- Always append `?v={ts}` to page URLs sent to Instapaper. Without it,
  Instapaper may serve a stale cached version of the page.
- Every generated page needs an explicit `<title>` tag in `<head>`,
  matching the `<h1>`. Instapaper falls back to parsing the `<h1>` for its
  title when `<title>` is missing, and that fallback caches more
  stubbornly than body content — `?v={ts}` refreshes the displayed content
  but not a bookmark's title metadata pinned by the fallback.
