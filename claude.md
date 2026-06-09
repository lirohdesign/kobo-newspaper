# claude.md — maintenance guide for the Reddit digest system

This orients a future Claude Code session (or future you) working on this
part of the project. Read this first — it tells you which file to change for
which kind of request, so a quick fix doesn't quietly undo work that took
real conversation to get right.

## The shape of the system
Five files define this feature; the pipeline code (built per `framework.md`'s
design) ties them together and runs alongside the existing daily build
(`main.py`, sharing `style.css` and the same long-form HTML pattern):

- **`taste.md`** — the rubric. What counts as signal, what to filter, format
  constraints. The single source of truth for "what does this person actually
  want." Everything else defers to it.
- **`sources.json`** — the source map. Which subreddits, in which bucket,
  daily vs. seasonal, and *why* each is placed (or deliberately not placed)
  where it is.
- **`framework.md`** — the architecture. How a run actually goes: gather,
  classify, render, persist — plus the seasonal-trigger and
  calibration-digest mechanisms.
- **`claude_scrape.md`** — the runtime prompt. The actual instructions handed
  to the API for the daily classification pass: the three-tier system and the
  output contract the Python code parses against.
- **this file** — how to maintain the above without breaking what's already
  been deliberately decided.

## Where a behavior-change request actually belongs
- *"Stop showing me X" / "I want more Y" / "this kind of thread isn't
  landing"* → **`taste.md`**. Almost always a rubric problem, not a
  prompt-engineering or code problem. Resist patching `claude_scrape.md` or
  bolting a special-case filter onto the Python side — fix the rubric, and
  the prompt that defers to it follows automatically.
- *"Add/remove this subreddit" / "this DRAFT source isn't working out"* →
  **`sources.json`**. Also where you graduate a `DRAFT` entry once it's
  proven itself over a few weeks of real runs, or retire one that hasn't.
- *New bucket type, new cadence, a new persisted log, anything structurally
  different about how a run works* → **`framework.md`** first, to keep the
  architecture document true, then the code to match it.
- *"The model's output is inconsistent / hard to parse / wrong shape"* →
  **`claude_scrape.md`**. The only file that should need to change for
  output-contract problems. If you're tempted to add Python post-processing
  to paper over inconsistent output, fix the prompt instead.

## The calibration loop is the maintenance signal
Because Instapaper gives no feedback, the **near-miss log** and the periodic
**calibration digest** (both in `framework.md`) are how drift gets caught. If
asked to "tune" the system, start by reading recent `borderline` calls and
their stated reasons — that's the actual evidence for whether `taste.md`
needs adjusting, and in which direction. Don't guess at a fix; read the log
first. A pile of correctly-rejected garbage proves nothing; the close calls
are where the real signal lives.

## Don't relitigate the dead ends
Two calls were already made deliberately, with real back-and-forth behind
them — don't reopen them without genuinely new information:

- **AI content is excluded from automation.** Not because it's
  uninteresting — because "rare, structurally significant AI event" is a
  detection problem that an LLM-scoring-Reddit-volume approach will reliably
  get wrong (high comment velocity tracks alarmist noise as readily as real
  signal). The Guardian/NYT sources already in this project carry that
  weight; this digest doesn't need to also try.
- **Booker/Nobel and major-report content is seasonal, not daily.** Forcing
  it into the daily rotation produces mostly-empty runs punctuated by floods.
  The `sources.json` `seasonal` entries plus a window/keyword check are the
  intended mechanism — don't "fix" an empty daily result by widening the
  daily net to cover this instead.

## One more standing lesson from this project
The Substack sync (`project_substack_sync_blocked.md`) died to IP-based bot
blocking from GitHub Actions runners — a hosting problem, not a code problem,
and no amount of retrying or proxy-juggling fixed it. If the Reddit fetch
ever starts returning blocks or 403s from Actions, don't assume it's the same
fixable-by-better-code situation the early Substack debugging looked like —
check whether it's the same structural wall first.
