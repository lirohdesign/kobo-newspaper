# Kids edition plan

## Objective
Build a second edition of `kobo-newspaper` for kids inside the existing repository, using a separate Instapaper account and a kid-friendly stylesheet, while preserving the standard edition and keeping all archive history in `old_issues`.

## Design principles
- Keep shared scrapers, helper code, and overall pipeline logic together in this repo.
- Add a second build mode in `main.py` rather than duplicating the entire project.
- Store kids archive files in `old_issues` alongside standard issues, with clear naming that makes kids issues obvious.
- Use a separate stylesheet for the kids edition so the presentation can be child-friendly without changing the standard edition.

## Build mode
The project should support two modes:
- `standard` — current daily newspaper build
- `kids` — new kids edition build

The build mode should control:
- output file naming
- archive file naming
- Instapaper credentials
- stylesheet selection
- any content source or section differences

## Output strategy
- Standard build remains `index.html` and related pages (`weather.html`, `nyt.html`, `links.html`, `cinema.html`, `archive.html`).
- Kids build should write separate files such as `index-kids.html`, `weather-kids.html`, `nyt-kids.html`, `links-kids.html`, `cinema-kids.html` as needed.
- Archive files should live in `old_issues`, named to show edition type:
  - `2026-06-15.html` for standard issues
  - `2026-06-15-kids.html` for kids issues

This preserves the same archive folder while making kids issues clearly distinguishable.

## Environment variables
Add a second Instapaper credential pair for the kids edition:
- `INSTAPAPER_USER_KIDS`
- `INSTAPAPER_PASS_KIDS`

Keep the existing standard edition variables:
- `INSTAPAPER_USER`
- `INSTAPAPER_PASS`

If the kids edition needs separate content configuration later, consider adding:
- `GUARDIAN_API_KEY_KIDS`
- `KIDS_SOURCE_CONFIG`

## Styling
- Add `style-kids.css` for the kids build.
- The kids HTML pages should reference `style-kids.css`.
- Preserve `style.css` for the standard edition.

## Main implementation points
1. Refactor `main.py` to accept a mode argument and build either edition.
2. Generalize Instapaper sending to accept credentials at call time.
3. Add output name generation based on mode.
4. Add archive file writing logic that includes a mode suffix for kids files.
5. Add a mode-specific page header/title and stylesheet reference.
6. Document the new mode and environment variables in `README.md` and `framework.md`.

## Archive naming conventions
- Standard issue: `old_issues/2026-06-15.html`
- Kids issue: `old_issues/2026-06-15-kids.html`
- Use `archive.html` to link to all issues; it can include both standard and kids entries if desired.

## Verification
- Run the standard build and confirm standard outputs are unchanged.
- Run the kids build and confirm separate kids outputs are generated with `style-kids.css` and a kids-specific title.
- Confirm archive files for both modes coexist in `old_issues` with mode-specific filenames.
- Confirm separate Instapaper credentials are selectable and used for the kids edition.

## Next discussion: sources
After this shape is locked in, the next step is to choose kid-appropriate sources to scrape or curate, focusing on content that is safer and simpler for a child reader.
