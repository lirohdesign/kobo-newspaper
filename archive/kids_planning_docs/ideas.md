# Kids edition — ideas

## Built

- **Math challenge** — skip counting, nines trick, quick facts (`math_generator.py`)
- **Would You Rather** — local question bank (`would_you_rather.py`)
- **Towers** (skyscrapers puzzle) — deterministic daily JPEG rendered via Pillow (`towers.py`)
- **Code Breaker** (Mastermind variant) — deterministic daily JPEG rendered via Pillow (`guess.py`)
- **Word of the Day** — French/Portuguese vocabulary with phonetics (`language.py`, `language_bank.json`)
- **On This Day** — pre-scraped local bank of Wikipedia-sourced events (`dayinhistory.py`, `dayinhistory_bank.json`)
- **Space** — NASA Astronomy Picture of the Day with fallback to apod.nasa.gov (`apod_scrape.py`)

* * *

## Future ideas

### Word Scramble
Text-only, fully deterministic — zero scraping risk.
Local JSON bank of ~365 words + short definitions.
WordNet via NLTK is a good definition source: `wn.synsets(word)[0].definition()`.
Renders as scrambled letter blocks + blank underline track.

### Music
Two approaches explored:

**Lead sheets** (simplest, most readable)
- Source: Mutopia Project (LilyPond `.ly` files, public domain)
- Requires LilyPond compiler in CI; produces SVG or image output
- Override page width + staff size in the `.ly` header before compiling

**Ukulele tabs**
- Horizontal continuous text breaks on narrow e-ink — needs vertical measure-by-measure format
- Higher layout engineering cost than lead sheets

### Spot the Difference
Clone a master line-art SVG, hide 2–3 elements in the copy via `display="none"`.
Instapaper strips inline SVG — would need PNG export via Pillow (same pipeline as towers/guess).
Good SVG sources: Lucide Icons (uniform 2px stroke, no fills), FontAwesome Free solid/regular.
