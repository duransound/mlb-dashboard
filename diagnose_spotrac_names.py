"""
One-off diagnostic: dumps exactly what mlb_data.py's Spotrac scraper is
extracting for one team, so we can see why match_salary is dropping ~90% of
players instead of guessing again. Run this, paste the full output back.

    python diagnose_spotrac_names.py HOU
"""
import sys

from mlb_data import SPOTRAC_TEAM_SLUGS, _extract_clean_name, _flatten_columns, _is_player_salary_table, _read_tables
import requests
from mlb_data import BROWSER_HEADERS

team = sys.argv[1] if len(sys.argv) > 1 else "HOU"
slug = SPOTRAC_TEAM_SLUGS[team]
url = f"https://www.spotrac.com/mlb/{slug}/payroll/"
print(f"Fetching {url}")
resp = requests.get(url, timeout=30, headers=BROWSER_HEADERS)
print(f"status: {resp.status_code}, length: {len(resp.text)}")

tables = _read_tables(resp.text)
print(f"\n{len(tables)} tables found on the page\n")

for i, t in enumerate(tables):
    t = _flatten_columns(t)
    qualifies = _is_player_salary_table(t)
    print(f"--- table {i}: columns={list(t.columns)} qualifies={qualifies} rows={len(t)}")
    if not qualifies:
        continue
    player_col = next(c for c in t.columns if str(c).strip().startswith("Player"))
    print(f"    using player_col={player_col!r}")
    for j, row in t.iterrows():
        if j >= 8:
            print(f"    ... ({len(t) - 8} more rows)")
            break
        raw = row[player_col]
        cleaned = _extract_clean_name(raw)
        salary = row.get("Payroll Salary", "?")
        print(f"    raw={raw!r:50s} -> cleaned={cleaned!r:30s} salary={salary!r}")
    print()
