"""OFAC Specially Designated Nationals list — counts of listed entries by
sanctions program, from the published sdn.csv (about 5.7 MB, no key).
Column 4 holds the program tags, several per entry as 'A] [B'.

A count of entries on the list, not of new designations: a week where the
count falls means delistings outnumbered additions. Program groups:
  - Russia/Ukraine: any RUSSIA-* or UKRAINE-* tag
  - Iran: any IRAN* tag, IFSR, or IRGC
  - SDGT: counter-terrorism; covers Hamas but is not Gaza-specific
"""
import csv
import io
from email.utils import parsedate_to_datetime

from research_http import fetch, snapshot, today

CSV_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"
PAGE_URL = "https://ofac.treasury.gov/specially-designated-nationals-and-blocked-persons-list-sdn-human-readable-lists"


def _programs(field):
    return {p.strip(" []") for p in field.split("] [") if p.strip(" []")}


def fetch_items():
    body, headers = fetch(CSV_URL, timeout=120)
    rows = [r for r in csv.reader(io.StringIO(body.decode("latin-1"))) if len(r) > 3]
    if not rows:
        print("DEBUG: ofac_sdn — sdn.csv fetched but no rows parsed")
        return []
    groups = {"Russia/Ukraine": 0, "Iran": 0, "SDGT": 0}
    for r in rows:
        progs = _programs(r[3])
        if any(p.startswith(("RUSSIA-", "UKRAINE-")) for p in progs):
            groups["Russia/Ukraine"] += 1
        if any(p.startswith("IRAN") or p in ("IFSR", "IRGC") for p in progs):
            groups["Iran"] += 1
        if "SDGT" in progs:
            groups["SDGT"] += 1
    modified = headers.get("Last-Modified")
    as_of = parsedate_to_datetime(modified).strftime("%Y-%m-%d") if modified else "unknown"
    summary = (
        f"{len(rows)} entries on the SDN list (file last modified {as_of}). "
        + ", ".join(f"{k}: {v}" for k, v in groups.items())
        + ". SDGT is counter-terrorism and not Gaza-specific."
    )
    date = today()
    return [snapshot(f"OFAC SDN list by program — {date}", PAGE_URL, date, summary)]


if __name__ == "__main__":
    for item in fetch_items():
        print(item["summary"])
