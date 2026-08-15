#!/usr/bin/env python3
"""
Dumps what's actually on Baseball-Reference's standings page, so a failed
runs-scored/allowed parse can be diagnosed from evidence instead of guesses.

Run this when build_dashboard.py reports:

    standings: no runs-scored/allowed columns found

Usage:
    source .venv/bin/activate
    python diagnose_standings.py            # current season
    python diagnose_standings.py 2025       # a specific season

It prints, for every table on the page: whether it came from the visible HTML
or from inside an HTML comment, its column names, and one sample row. What
we're looking for is a table with a team column plus columns for runs scored
and runs allowed. If those columns exist under names this kit doesn't know
about, add the pair to RUNS_COL_CANDIDATES in mlb_data.py and re-run the build
-- no other change needed.

Nothing here is scraped for the dashboard; this is a read-only inspection.
"""

import io
import sys

import pandas as pd
import requests

from mlb_data import (
    BROWSER_HEADERS, RUNS_COL_CANDIDATES, STANDINGS_COL_CANDIDATES,
    _flatten_columns,
)


def describe(tables, origin):
    for i, raw in enumerate(tables):
        try:
            t = _flatten_columns(raw)
        except Exception as exc:                              # noqa: BLE001
            print(f"\n[{origin} #{i}] could not flatten columns: {exc}")
            continue
        cols = [str(c) for c in t.columns]
        print(f"\n[{origin} #{i}]  {len(t)} rows")
        print(f"  columns: {cols}")

        has_wl = any({w, l}.issubset(set(cols)) for w, l in STANDINGS_COL_CANDIDATES)
        runs_pair = next((f"{rs}/{ra}" for rs, ra in RUNS_COL_CANDIDATES
                          if {rs, ra}.issubset(set(cols))), None)
        flags = []
        if has_wl:
            flags.append("has W/L")
        if runs_pair:
            flags.append(f"HAS RUNS ({runs_pair})  <-- this is the one")
        else:
            # Surface anything that smells like a runs column even when the
            # exact pair isn't recognised -- that's the whole point of running
            # this script.
            candidates = [c for c in cols
                          if c.upper() in ("R", "RA", "RS", "RUNS", "RUNS ALLOWED",
                                           "RDIFF", "RUN DIFF", "PYTHWL")]
            if candidates:
                flags.append(f"unrecognised runs-ish columns: {candidates}")
        print(f"  {'; '.join(flags) if flags else 'no record/runs columns'}")

        if len(t):
            row = t.iloc[0]
            sample = {c: row[c] for c in cols[:9]}
            print(f"  first row: {sample}")


def main():
    season = sys.argv[1] if len(sys.argv) > 1 else "2026"
    url = f"https://www.baseball-reference.com/leagues/majors/{season}-standings.shtml"
    print(f"Fetching {url}\n")
    resp = requests.get(url, headers=BROWSER_HEADERS, timeout=30)
    resp.encoding = "utf-8"
    resp.raise_for_status()
    html = resp.text
    print(f"page size: {len(html):,} chars; contains HTML comments: {'<!--' in html}")

    try:
        visible = pd.read_html(io.StringIO(html))
    except ValueError:
        visible = []
    print(f"tables in visible HTML: {len(visible)}")

    commented = []
    if "<!--" in html:
        try:
            allt = pd.read_html(io.StringIO(
                html.replace("<!--", "").replace("-->", "")))
            commented = allt[len(visible):]
        except ValueError:
            pass
    print(f"additional tables revealed by stripping comments: {len(commented)}")

    describe(visible, "visible")
    describe(commented, "commented")

    print("\n---")
    print("Looking for a table with a team column plus runs scored AND runs")
    print("allowed. If you see one whose column names aren't in")
    print(f"RUNS_COL_CANDIDATES ({RUNS_COL_CANDIDATES}), add that pair to")
    print("mlb_data.py and re-run build_dashboard.py.")


if __name__ == "__main__":
    main()
