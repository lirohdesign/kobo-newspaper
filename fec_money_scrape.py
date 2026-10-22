"""FEC — cumulative money raised and spent in the current federal cycle by
candidates, PACs (super PACs included) and parties, from the FEC API's
totals/by_entity endpoint. Uses the public DEMO_KEY (rate-limited, ample
for one call a day).

A partial reading for c5's 'outside spending': PAC money includes super
PACs but is not limited to independent expenditures, and spending by
groups that do not disclose donors is not separable here. That variable
stays a gap until a source for it is found (OpenSecrets refuses scripted
fetches, checked 2026-10-21).
"""
import json
from datetime import datetime, timezone

from research_http import fetch

API = "https://api.open.fec.gov/v1/totals/by_entity/?api_key=DEMO_KEY&per_page=100&cycle={cycle}"
PAGE_URL = "https://www.fec.gov/data/spending-bythenumbers/"


def _bn(x):
    return f"${x / 1e9:.2f}B"


def fetch_items():
    now = datetime.now(timezone.utc)
    cycle = now.year + (now.year % 2)
    rows = json.loads(fetch(API.format(cycle=cycle))[0])["results"]
    # Rows run to the end of the current month; take the last complete one.
    done = [r for r in rows if r["end_date"] < now.strftime("%Y-%m-%d")]
    if not done:
        print("DEBUG: fec_money — no completed months in the cycle")
        return []
    r = max(done, key=lambda r: r["end_date"])
    summary = (
        f"{cycle} cycle through {r['end_date']}: PACs raised {_bn(r['cumulative_pac_receipts'])} and spent "
        f"{_bn(r['cumulative_pac_disbursements'])}; parties raised {_bn(r['cumulative_party_receipts'])}; "
        f"candidates raised {_bn(r['cumulative_candidate_receipts'])}."
    )
    return [{
        "title": f"FEC money by entity — {cycle} cycle through {r['end_date']}",
        "link": f"{PAGE_URL}#through-{r['end_date']}",
        "date": r["end_date"],
        "summary": summary,
        "content_links": [],
    }]


if __name__ == "__main__":
    for item in fetch_items():
        print(item["title"], "\n  ", item["summary"])
