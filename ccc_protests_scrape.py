"""Crowd Counting Consortium (Harvard Ash Center / UConn) — US protest
events, from the phase 3 (2025-) dataset on Harvard Dataverse. Records are
fact-checked from public sources before posting. The CSV is about 47 MB
and is posted roughly monthly, with the data running a few months behind
(checked 2026-10-21: version of 2026-09-10 runs through May 2026).

Monthly event counts for the last six months in the data, nationally and
for Indiana. Keyed by Dataverse version, so the ledger grows only when CCC
posts a new version.
"""
import csv
import io
import json
from collections import Counter

from research_http import fetch

DATAVERSE = "https://dataverse.harvard.edu"
COLLECTION = f"{DATAVERSE}/api/dataverses/crowdcountingconsortium/contents"
DATA_FILE = "ccc-phase3-public.csv"


def _phase3():
    for d in json.loads(fetch(COLLECTION)[0])["data"]:
        if d.get("type") != "dataset":
            continue
        pid = f"doi:{d['authority']}/{d['identifier']}"
        meta = json.loads(fetch(f"{DATAVERSE}/api/datasets/:persistentId/?persistentId={pid}")[0])["data"]["latestVersion"]
        for f in meta["files"]:
            if f["dataFile"]["filename"] == DATA_FILE:
                return pid, meta, f["dataFile"]["id"]
    return None


def fetch_items():
    found = _phase3()
    if not found:
        print(f"DEBUG: ccc_protests — {DATA_FILE} not found in the Dataverse collection")
        return []
    pid, meta, file_id = found
    body, _ = fetch(f"{DATAVERSE}/api/access/datafile/{file_id}", timeout=300)
    rows = list(csv.DictReader(io.StringIO(body.decode("utf-8", errors="replace"))))
    months = Counter(r["date"][:7] for r in rows if r.get("date", "")[:4].isdigit())
    indiana = Counter(r["date"][:7] for r in rows if r.get("state") == "IN")
    recent = sorted(months)[-6:]
    if not recent:
        print("DEBUG: ccc_protests — data file parsed but no dated events")
        return []
    version = f"{meta['versionNumber']}.{meta['versionMinorNumber']}"
    updated = meta.get("lastUpdateTime", "")[:10]
    summary = (
        f"Dataverse version {version} (posted {updated}), data through {recent[-1]}. Events by month: "
        + ", ".join(f"{m} {months[m]}" for m in recent)
        + ". Indiana: " + ", ".join(f"{m} {indiana[m]}" for m in recent) + "."
    )
    return [{
        "title": f"Crowd Counting Consortium — version {version}, data through {recent[-1]}",
        "link": f"https://doi.org/{pid.removeprefix('doi:')}#v{version}",
        "date": recent[-1],
        "summary": summary,
        "content_links": [],
    }]


if __name__ == "__main__":
    for item in fetch_items():
        print(item["title"], "\n  ", item["summary"])
