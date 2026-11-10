# Lookout plan

Status: first slice built and run once on 2026-11-10, on branch
`feat/lookout`, unmerged. One interest area only. This doc is in a public
repo, so it names no interest, place, person or price; those are in the
private state directory.

## Changed after the first run (2026-11-10)

The maintainer's reactions the same day changed the target. Listing pages for
events were the wrong kind of watch and were all dropped: he wants
information, not outings. A second form replaced them and was kept on first
reading: a pack script in the private directory gathers candidates from his
own files and open data with no tokens, and the session writes one short
section from it. Kept ÷ brought now stands at 1 ÷ 7: six event finds dropped,
one section kept. The skill step describes the second form. The first-run
account below is left as it was written.

## Result first

- **Can kobo-loader take a document generated outside its own projects?**
  Yes. `docs_to_epub.py` converts every `.md` under any path listed in
  `projects.local.json`; it has no notion of where the file came from. Checked
  by calling its `build_epub()` on the generated list with the output sent to
  a scratch directory: it wrote a 120 KB `.kepub.epub`. kobo-loader was not
  changed. One row in `projects.local.json` is what remains, and that row is
  the maintainer's to add.
- **Does watching listing pages find things?** Ruled in, narrowly. 20 pages
  were tried; 12 returned readable text. Two names from the maintainer's own
  files appeared on them, both as dated, future events, neither searched for
  by name. The criteria were fixed and committed in the private directory
  before the run (one hit per eight readable pages; kill at zero).
- **Ruled out:** nothing.
- **Left open:**
  - Both name matches rest on the weakest signal the name list has. No
    high-weight name appeared anywhere. The earlier per-name searches covered
    four high-weight names and these matches are low-weight ones, so the two
    methods have not been compared on the same names.
  - No page showed a price. Whether a find is within budget is unverified for
    all six finds.
  - Eight pages gave no text (seven are drawn by script, one refuses the
    request). They were retired, not repaired.
  - Whether the session's own picks are any good. Four were brought; none has
    a reaction yet. Kept ÷ brought is 0 ÷ 6 with six awaiting a reaction.
  - The step has run once. Nothing here shows it improving over time.

Before this slice the agent had never brought a lead: all three `lead` lines
in `research_data/curation_log.jsonl` are `brought_by: maintainer`, so the
agent's precision was 0 ÷ 0.

## Design

Two stores, split by what may be public.

| | Public: this repo | Private: `~/Documents/kobo-lookout` |
|---|---|---|
| Holds | `lookout.py`, the skill step, calendar and source rows named for public things | name sources, watch list, snapshots, finds, reactions, lessons |
| Runs | GitHub Actions cron | `lookout.py`, by hand in the digest session, no tokens |
| Reaches the reader | Instapaper | `finds.md` → kobo-loader epub → USB sync |

`lookout.py` holds no interest of its own. It reads a config in the private
directory that says which of the maintainer's files to derive names from, and
derives them at every run; no copy is kept except the bare name list used to
report what changed since the last run.

A watch is a page that lists things. The script reduces it to text lines,
matches names by whole word, and reports only lines that were not there last
run. No per-site parser.

## The seven questions

**1. Persistence.** Per watch, one snapshot file, overwritten each run. One
`ledger.json` with the open finds and running counts; a find leaves it when
its date passes or it gets a reaction. One `lessons.md`, capped at 20 lines.
One `finds.md`, rewritten each session. History is the private directory's
git log. Nothing grows with age except the counts.

**2. Learning from the chat.** A reaction updates the ledger counts for the
find's kind and its watch, and adds or strengthens one line in `lessons.md`.
A lesson from one reaction is tentative and only changes rank. Two reactions
that agree make it a rule; two that contradict it delete it. The lesson is
written about the kind of thing, not the item.

**3. Measurement.** Hit: the maintainer says in the chat that the find was
worth having. Horizon: the end of the next session. No reaction is
`no_verdict`, counted apart and never as a hit. Counts are kept by kind (name
match, pick) and by watch. Kill: after six sessions, if kept ÷ brought is
under 0.2 the step is reported as failing and stops being run by default.

**4. Drift and decay.** Names are re-derived each run and the report states
how many were added and removed. A watch is flagged when it returns an error,
returns almost no text, loses half its text, or shows no new line for eight
runs. Measured churn between two runs minutes apart: zero lines across 12
pages once HTML comments were stripped.

**5. Budget.** The order is in the skill step. Smallest useful version: read
state, run the script, read the report. Measured in bytes, at about four
characters a token (an estimate, not a tokenizer count):

| Read | Bytes | About |
|---|---|---|
| `lessons.md` + `ledger.json` | 2,243 | 560 tokens |
| `report.md`, second run | 1,496 | 370 tokens |
| Start-of-session read for this step | 3,739 | 930 tokens |
| For scale: the skill's existing `tail -n 20` of the log | 13,512 | 3,400 tokens |
| First run only: six baseline listings read for picks, plus detail pages | about 23,000 | 5,800 tokens |

The report is capped at 24,000 characters and new lines at 40 per watch, so
the read cannot exceed about 6,000 tokens however many watches there are.

**6. Boundary and verdict load.** The agent decides and reports: adding,
repairing and retiring a private watch; excluding a name that matches
unrelated text; what goes in `finds.md`. A find asks nothing of the
maintainer; a reaction is welcome and not required. The maintainer decides:
anything entering this public repo's model (a source, a variable, a concern),
any change to the invariants, any change to another repo, any push. At most
three such questions are left per session, the same size as the skill's
2-3 standard reviews. The rest are held, ranked, for a later session. An
unanswered question means no action; it is asked once more, then dropped and
logged as dropped.

**7. Promotion.** A page becomes a private watch as soon as it is seen to
list more of a kind already found: the cost is one fetch a week and no
tokens. A watch is promoted to the public cron only if it is named for a
public thing, its timing matters between sessions, and the maintainer says
so; the cheapest form is a `research_calendar.json` row with no scraper. It
is verified as `CLAUDE.md` says: find the label in `old_issues/` on the
trigger date. A watch is retired at eight finds brought and none kept.

## What was built

- `lookout.py`: the watch runner. Stdlib only.
- `.claude/skills/research-digest/SKILL.md`: optional step 2b.
- Private directory, two commits: criteria before the run, results after.

Agent decisions in the run, all reversible: excluded 16 names (common words,
bare first names, and names the source data's own README calls a household
artifact); retired the eight unreadable watches.

## Not done

- Other interest areas, as asked.
- Surname-only matching. A person listed by surname alone is not matched.
- Pages drawn by script.
- The `projects.local.json` row in kobo-loader.
- `CLAUDE.md` says this repo is listed in kobo-loader's
  `projects.local.json`. It is not; the file lists one other project.
