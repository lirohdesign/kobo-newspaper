# Backlog

Deferred work and open questions not yet promoted into `CLAUDE.md` or
dropped. See `/Users/b/Documents/meta-ai/extensions/backlog.md`.

* * *

## Pipedream NYT sync will go away

Pipedream feeds `nyt_morning.html` (raw NYT "The Morning" newsletter HTML)
into the repo via a workflow named "liroh nyt sync" (`p_ZJCaNBA`), on a
schedule, committing as `B <benjamin.j.shelby@gmail.com>`. That commit
author matches the user's own Gmail, consistent with a Gmail-based
trigger, but the actual trigger config lives only in the Pipedream
dashboard — unconfirmed from the repo.

Ben expects Pipedream to disappear and wants to wait until it breaks
rather than replace it now (2026-10-21).

Replacement candidate once it breaks: a scheduled GitHub Action that polls
the same Gmail account directly (Gmail API, OAuth token as a repo secret)
for the newsletter message, extracts its HTML body, and commits it as
`nyt_morning.html` in the same shape Pipedream does today — `collect_nyt()`
in `main.py` needs no change. First step when this breaks: confirm the
actual Pipedream trigger type before building the replacement.
