# Scheduled Research Monitor Tasks — Review Copy

Set up 2026-09-08 in this session, based on the "Monitorable Source List for a Recurring Claude Scheduled Task: Five Research Threads" report. Three scheduled tasks, tiered by cadence. All times below are Central Time (America/Chicago); cron expressions are stored in UTC using the offset in effect at creation (UTC-5 / CDT) — they will read one hour "early" in local-time terms once Central switches to CST in November, since cron doesn't auto-adjust for DST.

Sources: all five research threads from the report are covered (AI/data-center market risk, farmland values & ag economics, forest & tree health, climate/dust/drought, and inequality/capital ownership), split across the three tiers below. Left out by design: Indiana farmland-conversion/foreign-ownership policy tracking and the commercial/ASFMRA-style land-market reports the source report itself flagged as too irregular and non-RSS to schedule reliably.

Each task runs in a **fresh, memoryless session** — it has no memory of previous firings, so it reports current/latest status each time rather than a true diff against the last run. Output is a markdown digest file written to that run's own session and delivered via SendUserFile (no connected folder, so files land in the chat, not on a local drive).

---

## 1. Weekly Research Monitor — AI/Grid/Drought

- **Trigger ID:** `trig_011wsyyzPtGnJNVHtRU8Czui`
- **Schedule:** Fridays, ~4:00 PM Central — cron `0 21 * * 5`
- **Next run:** 2026-09-11

**Prompt sent each firing:**

> You are running a recurring weekly research-monitoring task for the user (a photographer researching farmland economics and an AI-market-adjustment thesis). This is a fresh, memoryless session — you have no record of prior runs, so report the CURRENT/LATEST status of each source as of today (clearly state the as-of date for each item) rather than trying to diff against a previous report.
>
> Check these fast-moving sources and summarize what's notable from the past week or two. Use WebSearch/WebFetch as needed. Skip a source cleanly (one line: "nothing new") if there's nothing worth flagging — don't pad.
>
> AI / data-center / market risk (the priority thread):
> 1. Epoch AI — Gradient Updates & Data Insights (https://epoch.ai/, https://epochai.substack.com/): notable new posts/data this week.
> 2. SemiAnalysis (https://semianalysis.com/, https://newsletter.semianalysis.com/): notable free posts this week — semiconductor/data-center supply chain analysis.
> 3. Ed Zitron, Where's Your Ed At (https://www.wheresyoured.at/): this week's free newsletter — his bear-case take on AI-company unit economics.
> 4. Grid/buildout: interconnection.fyi (https://www.interconnection.fyi/, especially the Indiana page https://www.interconnection.fyi/data-center/state/IN) and Data Center Dynamics (https://www.datacenterdynamics.com/) — new data-center siting, power deals, or interconnection-queue news, especially Indiana/Midwest.
>
> Climate/drought (Midwest):
> 5. U.S. Drought Monitor (https://droughtmonitor.unl.edu/) — current classification for Indiana and the wider Midwest, and how it's changed from a couple weeks ago. If it's actively dust-storm season (roughly March–May) and conditions look dry/windy, also check NASA Worldview (https://worldview.earthdata.nasa.gov/) for visible aerosol/dust plume activity over the Midwest; otherwise skip Worldview.
>
> Agriculture:
> 6. USDA NASS Crop Progress (https://quickstats.nass.usda.gov/ / https://www.nass.usda.gov/) — only relevant April–November (growing season); this week's planting/progress percentages for the Corn Belt if in season, otherwise note it's off-season and skip.
> 7. farmdoc daily (https://farmdocdaily.illinois.edu/) — treat as a weekly digest: briefly summarize the most notable 1-3 articles from the past week rather than listing every daily post.
>
> Write the findings as a single markdown digest file (filename like weekly-research-digest-YYYY-MM-DD.md) into /mnt/user-data/outputs/, organized by source with brief prose (not a wall of nested bullets), then deliver it with SendUserFile. Keep the accompanying chat message to one or two sentences — the file is the deliverable. If a source's site or feed is unreachable, note that plainly rather than guessing at content.

---

## 2. Monthly Research Monitor — Ag/Climate/AI

- **Trigger ID:** `trig_01VcBPPstunqhMAVpsWFMwEY`
- **Schedule:** 15th of each month, ~7:00 AM Central — cron `0 12 15 * *`
- **Next run:** 2026-09-15

**Prompt sent each firing:**

> You are running a recurring monthly research-monitoring task for the user (a photographer researching farmland economics and an AI-market-adjustment thesis). This is a fresh, memoryless session — you have no record of prior runs, so report the CURRENT/LATEST status of each source as of today (state the as-of date/period for each item) rather than trying to diff against a previous report.
>
> Check these monthly-cadence sources and summarize what's notable since roughly the start of last month. Use WebSearch/WebFetch as needed. Skip a source cleanly (one line: "nothing new this month") if there's nothing worth flagging.
>
> Climate:
> 1. NOAA NCEI monthly climate report (https://www.ncei.noaa.gov/access/monitoring/monthly-report/) — latest Indiana/Michigan state temperature and precipitation summary vs. normal.
> 2. USDA Midwest Climate Hub (https://www.climatehubs.usda.gov/hubs/midwest) — new posts/assessments.
> 3. drought.gov Midwest Drought Status Update (https://www.drought.gov/drought-status-updates) — latest Midwest narrative (soil moisture, streamflow, Mississippi River navigation).
>
> AI / energy:
> 4. Epoch AI monthly "Epoch Brief" digest (https://epoch.ai/, https://epochai.substack.com/) — monthly synthesis.
> 5. EIA Electric Power Monthly (https://www.eia.gov/electricity/) — latest U.S. electricity demand/generation data, especially anything tying to data-center load growth.
> 6. LBNL data-center energy report page (https://eta.lbl.gov/publications/2024-lbnl-data-center-energy-usage-report and the broader https://eta.lbl.gov) — check whether a successor report/update beyond the 2025 Update has been published.
>
> Agriculture:
> 7. Iowa State Ag Decision Maker newsletter (https://www.extension.iastate.edu/agdm/) — this month's issue highlights.
> 8. Kansas City Fed — Ag Credit Survey / Agricultural Bulletin articles (https://www.kansascityfed.org/agriculture/) — any new quarterly survey or rolling article published this month.
> 9. Purdue Extension "Got Nature?" blog (https://www.purdue.edu/fnr/extension/) — roundup of this month's notable posts (woodland management, invasive species, wildlife).
>
> Inequality / capital ownership:
> 10. Washington Center for Equitable Growth (https://equitablegrowth.org/) and Aspen Institute Financial Security Program insights (https://www.aspeninstitute.org/programs/financial-security-program/) — notable new research posts this month.
> 11. NCEO free content (https://www.nceo.org/research, https://ownershipeconomy.org, https://esopinfo.org) — any new open (non-paywalled) statistics or announcements.
>
> Write the findings as a single markdown digest file (filename like monthly-research-digest-YYYY-MM-DD.md) into /mnt/user-data/outputs/, organized by source with brief prose (not a wall of nested bullets), then deliver it with SendUserFile. Keep the accompanying chat message to one or two sentences — the file is the deliverable. If a source's site or feed is unreachable, note that plainly rather than guessing at content.

---

## 3. Quarterly/Annual Research Calendar Check

- **Trigger ID:** `trig_01RH3pU4Fb1wNr1L8HwwB99n`
- **Schedule:** 15th of each month, ~8:00 AM Central — cron `0 13 15 * *`
- **Next run:** 2026-09-15
- **Design note:** This fires monthly (like task 2, but one hour later to avoid collision) rather than on exact one-off dates, because several of the source report's release windows are approximate ("early August," "mid-December," "roughly spring") and drift year to year. Each run checks the calendar below and only digs into whatever's actually due within a ~2-week window of the current month; other months it just confirms nothing is due.

**Prompt sent each firing:**

> You are running a recurring monthly "calendar check" for a set of research sources that only release new content a few times a year, on the user's behalf (a photographer researching farmland economics and an AI-market-adjustment thesis). This is a fresh, memoryless session — you have no record of prior runs. Your job each month is to check which of the items below are due to have released new content around THIS calendar month (allow about a 2-week buffer on either side of the stated window), fetch/search for those specific items, and report on them. For anything not due this month, just list it briefly as "not due this month" — do not do a deep search for it.
>
> Calendar of date-driven releases to watch for:
> - February, May, August, November: Federal Reserve Bank of Chicago — AgLetter, Seventh District farmland values & credit survey (https://www.chicagofed.org/publications/agletter/index).
> - Roughly mid-February, mid-May, mid-August, mid-November (about 10-11 weeks after each quarter ends): Federal Reserve — Distributional Financial Accounts (https://www.federalreserve.gov/releases/efa/efa-distributional-financial-accounts.htm) — new quarterly wealth-share data by percentile.
> - Quarterly, similar timing to the above: St. Louis Fed Ag Finance Monitor (https://fred.stlouisfed.org / https://www.stlouisfed.org) and quarterly Indiana State Climate Office "Climate INformer" newsletter (https://ag.purdue.edu/indiana-state-climate/).
> - Early August (first week for state data, late August for county cash rents): USDA NASS Land Values annual summary and Cash Rents (https://quickstats.nass.usda.gov/, https://www.nass.usda.gov/).
> - Mid-December: Iowa State University Land Value Survey (https://www.extension.iastate.edu/agdm/wdvalues.html, https://farmland.card.iastate.edu).
> - December: World Inequality Report / World Inequality Database annual update (https://wid.world/, https://inequalitylab.world/).
> - Late April / spring (roughly March–May): Michigan DNR Forest Health Highlights annual report (https://www.michigan.gov/dnr), USFS National Forest Health Highlights state reports for Indiana and Michigan (https://www.fs.usda.gov/foresthealth/), and the "Forests of Indiana" FIA resource update (https://research.fs.usda.gov/programs/fia).
> - Roughly 3 times a year, irregular timing — worth a light check every couple months: Indiana Woodland Steward newsletter (https://www.inwoodlands.org/).
> - Annual, timing varies — check periodically: Ownership Works Impact Report (https://ownershipworks.org/our-impact/) and NCEO Employee Ownership Report / annual surveys (https://www.nceo.org/research).
> - One-time watch for late 2026: Federal Reserve Survey of Consumer Finances 2025 results, the marquee triennial household wealth survey — watch for a release announcement (https://www.federalreserve.gov/econres/scfindex.htm).
>
> Use WebSearch/WebFetch to check the items that are due this month. Write the findings as a single markdown digest file (filename like quarterly-research-checkin-YYYY-MM-DD.md) into /mnt/user-data/outputs/, organized by source with brief prose, then deliver it with SendUserFile — even in a month where nothing substantive is due, send a short file noting "nothing due this month; next expected releases are [list]" so the user knows the check ran. Keep the accompanying chat message to one or two sentences.

---

## Self-review / things worth double-checking

- **DST drift:** the two 15th-of-month tasks and the Friday weekly task are pinned to fixed UTC times computed from the current UTC-5 offset. Once Central Time falls back to CST (UTC-6) in November, these will effectively fire an hour earlier in local time (e.g., a 7:00 AM run becomes 6:00 AM). Not a functional problem, just worth knowing — happy to nudge the cron expressions in November if the drift bothers you.
- **No cross-run memory:** because each firing is a stand-alone session, digests won't say "this changed since last week" with certainty — they report current status and let you spot changes by reading successive digests. If you'd rather have true diffing, that would need a persistent state file, which is a bigger lift and wasn't part of what you asked for.
- **Delivery:** files land in the chat via SendUserFile only — no computer is currently linked to this session, so nothing gets written to a local folder automatically.
- **Coverage gap:** the source report flagged several items (exact 2026 NASS release dates, whether Midwest Climate Hub/Indiana Forest Alliance/Equitable Growth have true RSS) as needing verification at setup — that verification wasn't done here; the scheduled tasks will simply search live each time rather than relying on a feed guess.