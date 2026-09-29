# Substack sync — why it's gone, and what would have to change to bring it back

This project used to include a "Substack Private Sync" workflow that pulled posts
from a private Substack RSS feed and sent them to Instapaper alongside the daily
build. The code (`private_sync.py` and `.github/workflows/private_sync.yml`) has
been removed because it doesn't work and there's no cheap fix — keeping it around
just meant a daily cron job that failed every morning. This doc preserves *why*,
so a future attempt doesn't re-walk the same dead end.

## The blocker

Substack/Cloudflare blocks requests from GitHub Actions' datacenter IP ranges:

- A direct fetch of the private feed from a GitHub Actions runner returns **HTTP 403**.
  The same feed fetched from a residential/dev IP returns 200 with the full feed —
  this is IP-reputation-based bot blocking, not a User-Agent or auth problem.
- Routing around the 403 via a free CORS proxy (AllOrigins, codetabs, thingproxy)
  doesn't work either: the feed payload is large (~340KB+, full article HTML embedded
  in each item), and every free proxy tested either choked mid-transfer
  ("Response ended prematurely"), 500'd, or 522'd.
- Self-hosting a small proxy was considered and rejected: writing it is trivial, but
  hosting it in commodity cloud likely shares the same blocked datacenter-IP space,
  while hosting it at home requires a machine that's reliably on and reachable
  (tunneling / dynamic DNS) every morning at 6 AM — too much ongoing overhead for
  what this is worth.

## The live lead, if this gets revisited

**Email digest delivery** — have Substack email full posts/digests directly, sidestepping
RSS scraping (and the IP block) entirely, then bridge that email to Instapaper or the
Kobo some other way (e.g. a mail rule + a service that converts email to a read-later
link). Worth exploring if/when this becomes a priority again.
