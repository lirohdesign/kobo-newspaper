"""ICE detention statistics — people currently detained, by criminality,
from ICE's own fiscal-year spreadsheet (published under the FY2020 DHS
appropriations act). TRAC's quick facts are built from this same file.

The detention-management page links one file per fiscal year; the current
year's name carries a release date (FY26_detentionStats07202026.xlsx). The
item is keyed by that file name, so a new release is a new history line and
a stale release stays one line however long ICE goes without updating.

No openpyxl in requirements.txt, so the sheet is read straight from the
XLSX zip (shared strings plus cell values).
"""
import io
import re
import zipfile
from datetime import datetime

from research_http import fetch, fetch_text

PAGE_URL = "https://www.ice.gov/detain/detention-management"
FILE_RE = re.compile(r'href="(https://www\.ice\.gov/doclib/detention/FY(\d\d)_detentionStats(\d{8})?\.xlsx)"')


def _latest_file(html):
    files = FILE_RE.findall(html)
    return max(files, key=lambda f: (f[1], f[2])) if files else None


def _sheet_rows(z, sheet_name):
    shared = [re.sub(r"<[^>]+>", "", s) for s in re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode(), re.S)]
    wb = z.read("xl/workbook.xml").decode()
    rels = z.read("xl/_rels/workbook.xml.rels").decode()
    targets = {}
    for rel in re.findall(r"<Relationship [^>]*>", rels):
        rid, target = re.search(r'Id="([^"]+)"', rel), re.search(r'Target="([^"]+)"', rel)
        if rid and target:
            targets[rid.group(1)] = target.group(1)
    rid = next(r for n, r in re.findall(r'<sheet [^>]*name="([^"]+)"[^>]*r:id="([^"]+)"', wb) if n.strip().startswith(sheet_name))
    xml = z.read("xl/" + targets[rid].lstrip("/").removeprefix("xl/")).decode()
    rows = {}
    for col, row, attrs, inner in re.findall(r'<c r="([A-Z]+)(\d+)"([^>]*?)(?:/>|>(.*?)</c>)', xml, re.S):
        v = re.search(r"<v>([^<]*)</v>", inner or "")
        if v:
            rows.setdefault(int(row), {})[col] = shared[int(v.group(1))] if 't="s"' in attrs else v.group(1)
    return shared, rows


def fetch_items():
    found = _latest_file(fetch_text(PAGE_URL))
    if not found:
        print("DEBUG: ice_detention — no detention statistics file linked on the page")
        return []
    url, fy, stamp = found
    body, _ = fetch(url, timeout=120)
    try:
        shared, rows = _sheet_rows(zipfile.ZipFile(io.BytesIO(body)), "Detention")
        head = next(r for r in sorted(rows) if rows[r].get("A", "").startswith("ICE Currently Detained by Crim"))
        total = next(r for r in sorted(rows) if r > head and rows[r].get("A") == "Total")
        by_crim = {rows[r]["A"]: int(float(rows[r]["F"])) for r in range(total + 1, total + 4) if "A" in rows.get(r, {}) and "F" in rows[r]}
        detained = int(float(rows[total]["F"]))
    except (StopIteration, KeyError, ValueError, zipfile.BadZipFile) as e:
        print(f"DEBUG: ice_detention — spreadsheet layout not as expected: {e}")
        return []
    src = next((s for s in shared if s.startswith("Data Source:")), "")
    m = re.search(r"(\d{2}/\d{2}/\d{4})", src)
    as_of = datetime.strptime(m.group(1), "%m/%d/%Y").strftime("%Y-%m-%d") if m else (
        datetime.strptime(stamp, "%m%d%Y").strftime("%Y-%m-%d") if stamp else "unknown")
    no_conviction = detained - by_crim.get("Convicted Criminal", 0)
    summary = (
        f"{detained} people in ICE detention as of {as_of} (FY20{fy} file). "
        + ", ".join(f"{k}: {v}" for k, v in by_crim.items())
        + f". With no criminal conviction: {no_conviction} ({100 * no_conviction / detained:.1f}%)."
    )
    return [{
        "title": f"ICE detention statistics — as of {as_of}",
        "link": url,
        "date": as_of,
        "summary": summary,
        "content_links": [],
    }]


if __name__ == "__main__":
    for item in fetch_items():
        print(item["title"], "\n  ", item["summary"])
