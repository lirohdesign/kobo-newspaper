# Framework — architecture of the kobo-newspaper system

Two editions run from one repo: a **standard** daily newspaper and a **kids** edition. Both deploy to GitHub Pages and sync to Instapaper. This document covers how the pieces fit together end to end — standard build, kids build, deployment, and the rendering contract that Instapaper and Kobo impose.

* * *

## Standard build

`python3 main.py` (default mode)

Reads and writes:

| Output | Purpose |
| :--- | :--- |
| `index.html` | Today's paper — linked to from Instapaper |
| `weather.html`, `nyt.html`, `links.html`, `cinema.html` | Separate pages sent as individual Instapaper items |
| `old_issues/YYYY-MM-DD.html` | Archive copy (CSS path rewritten to `../style.css`) |
| `archive.html` | Index of all archived issues (both editions) |

Sections: weather (NWS API), NYT morning briefing scrape, links (Reddit/RSS — currently parked), cinema (local venue scrape), calendar events (section 05, `calendar.json`-driven).

Timezone: `ZoneInfo("America/Chicago")` via `central_now()` — DST-aware. Never use `utcnow() - timedelta(hours=6)`; that hardcodes CST and breaks during CDT.

* * *

## Kids build

`python3 main.py --mode kids` → `kids_main()` in `main.py`

### Sections (in order)

| # | Section | Module | Returns |
| :--- | :--- | :--- | :--- |
| 01 | weather | `kids_weather.py` | HTML string or None |
| 02 | math challenge | `math_generator.py` | `(content, answers)` |
| 03 | would you rather | `would_you_rather.py` | HTML string |
| 04 | towers (skyscrapers) | `towers.py` | `(content, answers)` |
| 05 | code breaker (mastermind) | `guess.py` | `(content, answers)` |
| 06 | word of the day | `language.py` | HTML string or None |
| 07 | on this day | `dayinhistory.py` | HTML string or None |
| 08 | space (APOD) | `apod_scrape.py` | HTML string or None |
| 09 | answers | assembled in `main.py` | math + towers + guess answers |

Modules that return `(content, answers)` tuples: the `content` goes into its numbered section; the `answers` are assembled into section 09. All other modules return a single HTML string (or None on failure, which renders as `<p>unavailable</p>`).

### Outputs

| Output | Notes |
| :--- | :--- |
| `index-kids.html` | Generated, gitignored — not tracked in main branch |
| `old_issues/YYYY-MM-DD-kids.html` | Archive copy (CSS path rewritten to `../style-kids.css`) |
| `puzzles/YYYY-MM-DD-name.jpg` | Puzzle images — gitignored, persist on gh-pages via `keep_files: true` |

### Key constants in kids_main

```python
base_url = "https://lirohdesign.github.io/kobo-newspaper"
today = central_now()           # ZoneInfo("America/Chicago"), DST-aware
ts = get_timestamp()            # "16jun26 0030" (lower, ddmmmyy hhmm CST/CDT)
file_date = today.strftime("%Y-%m-%d")
kids_url = f"{base_url}/index-kids.html?v={ts}"  # ?v= cache-busts Instapaper
```

### Instapaper delivery

Kids URL is sent to both `INSTAPAPER_USER_KIDS` (the child's account) and `INSTAPAPER_USER` (the parent's account) if both sets of credentials are set.

### Math challenge

`math_generator.py` uses `random.Random(int(today.strftime("%Y%j")))` — deterministic from date.

- **Skip counting**: one blank in a 5-term sequence, varying step sizes (2, 3, 5, 10, 11, 25, 50, 100)
- **Mental math**: nines trick — `9/19/29/.../99 + other`, with `Think (n+1) + other − 1` hint
- **Quick facts**: 4 problems, mix of add/sub/multiply. Subtraction is **no-borrow**: each digit of subtrahend ≤ matching digit of minuend (e.g. 78 − 46, not 76 − 48). Addition allows carrying.

### Puzzle rendering pipeline

Both `towers.py` and `guess.py` render via Pillow. The pipeline:

```
logical layout (Python)
  → render at 2× (SS=2, all coords × SS)
  → LANCZOS downscale to 70% of logical size
  → save as JPEG quality 80
  → write to puzzles/{name}-{date}.jpg
  → HTML <img src="{base_url}/puzzles/{name}-{date}.jpg">
```

Towers (skyscrapers): 3×3 Latin square with edge visibility clues. RNG seed: `int(today.strftime("%Y%j")) * 100 + 11`.

Code Breaker (Mastermind): secret = 3 shapes chosen without repeats from [circle, square, triangle, diamond]. Up to 5 AI-generated guesses shown with black/white dot scores. RNG seed: `int(today.strftime("%Y%j")) * 100 + 22`.

Each puzzle generates two files: `{name}-{date}.jpg` (puzzle) and `{name}-{date}-answer.jpg` (answer, shown in section 09). Date-stamped filenames defeat Instapaper's per-URL image cache — without the date, the same URL would serve the first day's image forever.

Font loading (both modules):

```python
def _font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf"):
        try: return ImageFont.truetype(p, size)
        except Exception: pass
    return ImageFont.load_default(size=size)  # returns scalable FreeTypeFont in Pillow ≥10.1
```

CI ubuntu has DejaVu on disk. The fallback `load_default(size=...)` returns a scalable font (not the old bitmap default) in Pillow ≥10.1 — safe to rely on.

### Language module

`language.py` picks a daily word from `language_bank.json` using `random.Random(int(today.strftime("%Y%j")))`.

Article sound merging: French and Portuguese vocabulary entries carry their article (e.g. `l'ami`, `o amigo`). The displayed word includes the article; the phonetic guide must too. `_with_article(word, sounds, articles)` handles two cases:

- **Elided** (`l'`): article sound attaches directly — `"l" + "ah-mee"` → `"lah-mee"`
- **Spaced** (`le`, `o`, etc.): article sound prepended with space — `"oo" + "ah-mee-goo"` → `"oo ah-mee-goo"`
- **No article** (bare word): phonetics pass through unchanged

`FR_ARTICLES` and `PT_ARTICLES` dicts map article string → `(sound, elided_bool)`. Words not matching any article key pass through. If you add vocabulary where the article sound would collide with the noun sound, check `_with_article` logic first.

HTML output uses `<ul class='lang-block'>` with `<li><strong>en:</strong> …</li>` — **not** `<div><p>`. This is intentional for Kobo rendering (see below).

### APOD

`apod_scrape.py` tries NASA's API first (`api.nasa.gov/planetary/apod`), falls back to scraping `apod.nasa.gov` directly. The API is unreliable (frequent timeouts, 429s, 5xx) — the web page is stable. Three retry attempts with backoff before falling back. Explanation text is sanitized to strip trailing nav copy ("`Explore the Universe:`", "`Tomorrow's picture:`").

Video days return a thumbnail via `thumbs=true` API param; the web scraper finds `<img>` in the page directly.

* * *

## Instapaper and Kobo rendering contract

This section documents what the delivery chain strips, ignores, or breaks — learned through live testing. Read this before adding any new content type.

### What Instapaper strips
- **Inline SVG** — completely removed. Never use inline SVG for content.
- **CSS** — mostly stripped when delivering to Kobo. Assume zero styling survives.
- **CSS transforms, flexbox, grid** — stripped.
- **Flag emoji** — stripped (platform rendering issues).
- **`<div>` class attributes** — the div itself may survive but class-based CSS won't apply on Kobo.

### What survives to Kobo
- **Semantic HTML tags**: `<strong>`, `<em>`, `<ul>`, `<li>`, `<h1>`–`<h3>`, `<p>`, `<img>`
- **`<img>` with absolute URLs** pointing to publicly accessible JPEGs — confirmed working
- **Inline `style=` attributes** — partially, but don't rely on them for anything critical

### Image rules (critical)
1. **JPEG only.** PNG images render correctly in browser and in Instapaper's web UI, but appear as blank icons on Kobo via Instapaper offline delivery. APOD (JPEG) is the proof case. Always use JPEG for puzzle images.
2. **Absolute URLs only.** Relative paths (`puzzles/name.jpg`) work in a browser because the browser resolves them against the page URL. Instapaper's Kobo offline pipeline does not resolve relative URLs at cache time — the image is silently skipped. Use `{base_url}/puzzles/{name}.jpg` always.
3. **Date-stamp filenames.** Instapaper caches images by URL. A puzzle image at a fixed URL (`towers-puzzle.jpg`) would serve the first day's image forever. Include the date: `towers-2026-06-16.jpg`.

### Bold/emphasis rules (critical)
- `<strong>` inside `<li>` — **renders as bold on Kobo.** Confirmed working (matches "on this day" dates pattern).
- `<strong>` inside `<p>` — **does not reliably bold on Kobo.** CSS bold works in browser but the Kobo Instapaper app strips it.
- Use `<ul><li>` structure for any labelled list where bold labels matter (language module does this deliberately).

### Cache busting
Add `?v={timestamp}` to page URLs sent to Instapaper. Without this, Instapaper may serve a cached version of the page rather than re-fetching. The `kids_url` and all per-section page URLs include `?v={ts}`.

* * *

## Deployment

Two independent GitHub Actions workflows, each with their own schedule and deploy step. They were split so the kids build never waits behind the standard build's external scraper steps (NYT, weather, cinema, calendar).

### Standard build (`.github/workflows/daily.yml`)

Runs weekday 6:29 AM CST / weekend 7:43 AM CST, plus `workflow_dispatch`.

1. Clone gh-pages branch → restore `old_issues/` and `nyt_morning.html` into workspace
2. Install: `pip install requests beautifulsoup4 certifi pillow`
3. Run standard build (`python main.py`)
4. Deploy: `peaceiris/actions-gh-pages@v4` with `publish_dir: ./`, `keep_files: true`

### Kids build (`.github/workflows/kids-daily.yml`)

Runs daily at 5:50 AM CST, plus `workflow_dispatch`. No dependency on the standard build's content or schedule.

1. Clone gh-pages branch → restore `old_issues/` only (kids build doesn't need `nyt_morning.html`)
2. Install: `pip install -r requirements.txt`
3. Run kids build (`python main.py --mode kids`)
4. Deploy: same `peaceiris/actions-gh-pages@v4` step, `keep_files: true`

Both workflows write into the same `old_issues/` and `archive.html` on gh-pages. Since the kids run completes well before the standard run starts, there's no overlap/race on the gh-pages branch.

`keep_files: true` means files already on gh-pages are not deleted when new content is deployed. This is how `puzzles/*.jpg` accumulate across days — each build adds new date-stamped files without removing old ones. It also preserves archived `old_issues/` across builds, and preserves each workflow's output (e.g. `index.html`) when the *other* workflow deploys.

### DST drift (known limitation)

GitHub Actions cron is fixed UTC and does not adjust for daylight saving time. All three schedule entries (standard weekday/weekend, kids daily) are written assuming CST (UTC-6) — during CDT (UTC-5, roughly March–November) actual delivery is an hour later than the comment states. This is a known, accepted imprecision, not a bug to "fix" by chasing DST-aware cron syntax (GitHub Actions doesn't support it). If delivery timing actually matters more precisely, the fix is two cron lines per schedule (one for each DST period) with no automatic switching — would need manual updates twice a year, or a date-gated job condition.

### GitHub Pages base URL

`https://lirohdesign.github.io/kobo-newspaper`

All image `src` attributes must use this absolute base. It's set as `base_url` in both `main()` and `kids_main()`.

### What is and isn't tracked in main branch

Tracked (source):
- All `.py` modules, `.json` banks, `.css`, `.md` docs, `calendar.json`, `daily.yml`

Not tracked on `main`, but **must not be gitignored**:
- `index-kids.html`, `archive.html`, `old_issues/`, `puzzles/` — generated by the build and deployed to gh-pages. They're untracked on `main` only because nothing ever `git add -A`'s the repo root — never add them to `.gitignore` to enforce that (see the pitfall below).

Gitignored (truly excluded everywhere, never deployed):
- `KOBO.md`, `.kobo_resolved.json` — kobo-loader annotation files, never present in CI anyway
- `__pycache__/`

### Pitfall: don't gitignore generated/deployed paths

`peaceiris/actions-gh-pages` deploys by copying `publish_dir` (`./`, the whole post-build working tree — including `.gitignore`) into the gh-pages worktree, then running `git add -A` there. Git's `add -A` skips any path matching a `.gitignore` rule **unless that path is already tracked** on that branch's history.

This created a real outage: a cleanup pass once added `index-kids.html`, `archive.html`, `old_issues/`, and `puzzles/` to `.gitignore` for tidiness on `main`. The next deploy, every *new* date-stamped file (`puzzles/towers-2026-06-17.jpg`, `old_issues/2026-06-17-kids.html`) silently failed to reach gh-pages — git saw them as gitignored-and-untracked and skipped them. Already-tracked files like `index-kids.html` (tracked on gh-pages from years of prior deploys) kept updating fine, which made the failure look smaller than it was: the page refreshed, but new images and new archive snapshots quietly stopped shipping.

If you want a path excluded from `main`'s tracking without risking this, just don't `git add` it — don't add it to `.gitignore`.

* * *

## Reddit digest pipeline (parked)

The spec for a Claude-scored Reddit digest lives in `taste.md`, `sources.json`, and `claude_scrape.md`. The pipeline is described below but is **currently not running** — Reddit data access is blocked (see "Access wall" section).

### Daily run design

1. **Gather.** Fetch from subreddits in `sources.json` `daily` buckets via unauthenticated `.json` endpoints. Pre-filter: drop one-line comments, sort by score, cap comments per thread.
2. **Classify.** One batched API call with `taste.md` (rubric) and `claude_scrape.md` (instructions). Per candidate: tier (include/borderline/exclude), one-line reason, synthesized presentation for includes.
3. **Render.** Included items → new section in daily build, alongside existing sections.
4. **Persist.** Sent-hash log (SHA-256 masked IDs, no repeats) + near-miss log (borderline calls only — the calibration record).

### Seasonal buckets

Each run checks `sources.json` `seasonal` entries — is today inside a `windows` range, or does a keyword match? If yes, that bucket runs once for this build. Most days: no match, no cost.

### Calibration digest

On a set cadence, generate a short digest from the near-miss log (borderline calls + reasoning) and deliver it to Instapaper. This is how drift gets caught — Instapaper gives no engagement signal back, so the only feedback loop is reviewing close calls periodically. See `taste.md` and `claude_scrape.md` for the rubric and prompt contract.

### Access wall

- **Unauthenticated `.json` endpoints** — hard 403 since Reddit's 2023 API changes
- **OAuth script app** — applied, denied
- **RSS** — serves only titles and post text, no comments; comment thread is the signal, not the title

Third-party options (Pullpush, Apify, SerpApi) all have reliability, cost, or depth tradeoffs that make them poor substitutes. **Status: parked.** Spec remains valid if access becomes feasible — don't re-investigate the dead ends above.

* * *

## Calendar and event scrapers

The standard build includes a **section 05 calendar** driven by `calendar.json`. Handles content that clusters around known events (Purdue ag reports, literary prizes, institutional releases).

### Trigger types

| Trigger | Fires when |
| :--- | :--- |
| `first_tuesday_monthly` | First Tuesday of each month (±1 day) |
| `annual_window` | Current month is in the `months` array |
| `manual` | Today matches a date in the `dates` array (±1 day) |

Events due today → rendered as active card. Events within 14 days → listed under "upcoming." Outside window → skipped.

### Scraper contract

Write a module with a `collect()` function returning an HTML string (or empty string on failure). Set `"scraper": "your_scrape.py"` on the `calendar.json` entry. `main.py` dynamically imports and calls `collect()` when the trigger fires — no changes to `main.py` needed.

### The fallback is the feature

When no scraper exists, or a scraper fails, the calendar still surfaces a card with a direct link ("Check thebookerprizes.com →"). A reliable reminder beats silence. Don't remove the fallback path in pursuit of a cleaner output.

### Verifying

Calendar triggers are date-dependent — can't be tested with a dry run. Check the archive instead: open `old_issues/` and find the file dated on or after the expected trigger date. Search for the event `label` from `calendar.json`. Three outcomes: scraped content present (working), fallback "Check source →" (trigger fired, scraper failed), label absent (trigger didn't fire — check `calendar.json` date logic).

* * *

## What lives where

| Concern | File |
| :--- | :--- |
| Kids section content and scoring rubric | `taste.md` (for Reddit); section-specific modules for kids |
| Reddit subreddits, buckets, daily vs. seasonal | `sources.json` |
| Reddit runtime prompt and output contract | `claude_scrape.md` |
| Calendar events and scrapers | `calendar.json` |
| Architecture (this document) | `framework.md` |
| Maintenance guidance, dead ends, standing lessons | `CLAUDE.md` |
| Kids section ideas, build/future status | `kids_planning_docs/ideas.md` |
| Kids build original architecture plan | `kids_planning_docs/plan-kidsEdition.prompt.md` |
| One-shot bank generation scripts (keep, not for CI) | `fetch_phonetics.py`, `scrape_dayinhistory.py` |

* * *

## Future development

**Word scramble** — text-only, fully deterministic. Local JSON bank (~365 words + definitions). WordNet via NLTK auto-generates brief definitions locally. Renders as scrambled letter blocks + blank underline. See `kids_planning_docs/ideas.md`.

**Music** — LilyPond lead sheets (Mutopia Project) require LilyPond compiler in CI. Ukulele tabs need vertical measure-by-measure layout to avoid horizontal overflow on narrow e-ink.

**Spot the Difference** — clone a master SVG, hide 2–3 elements in the copy. Instapaper strips SVG, so PNG export via Pillow would be required (same pipeline as towers/guess).

**Local concerts** — extend `cinema_scrape.py` pattern to venue concert calendars.

**Delivery timing** — adjust cron if issues aren't arriving before wakeup time. CI runner is UTC; cron is written in UTC, converted to CST/CDT mentally.
