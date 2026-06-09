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

## What lives where

| Concern | Lives in |
| :--- | :--- |
| What counts as signal, what to filter, format constraints | `taste.md` |
| Which subreddits, which bucket, daily vs. seasonal, and why | `sources.json` |
| The runtime prompt — how to apply the rubric to a batch of candidates | `claude_scrape.md` |
| How the pieces connect into a run, end to end | this file |
| Maintenance guidance for future work on this system | `claude.md` |
