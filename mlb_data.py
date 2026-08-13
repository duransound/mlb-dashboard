"""
Live data-fetching helpers for the "Diamond Dollars" dashboard -- run on YOUR
machine (unrestricted network), not in the cloud sandbox that built this kit
(see README "Why the live path has to run on your machine"). Two sources:

1. WAR (bWAR-style value stats) via `pybaseball`, which wraps FanGraphs'
   season leaderboards (pip install pybaseball; wraps requests + pandas
   under the hood, no scraping code of your own needed).
2. Salary via a small RosterResource scraper (pandas.read_html against
   FanGraphs' public per-team payroll pages) -- pybaseball itself has no
   salary endpoint, so this part is custom, kept in this file rather than
   inline in build_dashboard.py for the same one-function-one-job reason
   chart_builders.py exists.

**Not verified against a live run.** The cloud sandbox that wrote this kit
can't reach pybaseball's PyPI-installed package's actual network calls or
fangraphs.com directly (see README) -- pybaseball's column names, and
RosterResource's HTML table structure, were confirmed by fetching sample
pages through a page-fetching tool rather than by running this exact code
path end to end. Treat the first real run as the actual test: if a column
name or team slug is off, the fix is almost certainly a one-line rename in
FG_WAR_COL / RR_TEAM_SLUGS below, not a structural problem. Please report
back (or just fix and keep going) if you hit one.
"""

import re
import time

import pandas as pd
import requests

# pybaseball's FanGraphs leaderboard WAR column is literally "WAR" in both
# batting_stats() and pitching_stats() as of the version this was written
# against -- kept as a constant here in case that ever changes upstream.
FG_WAR_COL = "WAR"

# FanGraphs RosterResource payroll page slugs, one per team. FanGraphs uses
# its own 3-letter team codes in batting_stats()/pitching_stats() output
# (e.g. "CHC", "NYY") -- this dict's keys match those, mapped to the URL
# slug RosterResource uses at fangraphs.com/roster-resource/payroll/<slug>.
RR_TEAM_SLUGS = {
    "ARI": "diamondbacks", "ATL": "braves", "BAL": "orioles", "BOS": "red-sox",
    "CHC": "cubs", "CHW": "white-sox", "CIN": "reds", "CLE": "guardians",
    "COL": "rockies", "DET": "tigers", "HOU": "astros", "KCR": "royals",
    "LAA": "angels", "LAD": "dodgers", "MIA": "marlins", "MIL": "brewers",
    "MIN": "twins", "NYM": "mets", "NYY": "yankees", "ATH": "athletics",
    "PHI": "phillies", "PIT": "pirates", "SDP": "padres", "SFG": "giants",
    "SEA": "mariners", "STL": "cardinals", "TBR": "rays", "TEX": "rangers",
    "TOR": "blue-jays", "WSN": "nationals",
}

TEAM_NAMES = {
    "ARI": "Arizona Diamondbacks", "ATL": "Atlanta Braves", "BAL": "Baltimore Orioles",
    "BOS": "Boston Red Sox", "CHC": "Chicago Cubs", "CHW": "Chicago White Sox",
    "CIN": "Cincinnati Reds", "CLE": "Cleveland Guardians", "COL": "Colorado Rockies",
    "DET": "Detroit Tigers", "HOU": "Houston Astros", "KCR": "Kansas City Royals",
    "LAA": "Los Angeles Angels", "LAD": "Los Angeles Dodgers", "MIA": "Miami Marlins",
    "MIL": "Milwaukee Brewers", "MIN": "Minnesota Twins", "NYM": "New York Mets",
    "NYY": "New York Yankees", "ATH": "Athletics", "PHI": "Philadelphia Phillies",
    "PIT": "Pittsburgh Pirates", "SDP": "San Diego Padres", "SFG": "San Francisco Giants",
    "SEA": "Seattle Mariners", "STL": "St. Louis Cardinals", "TBR": "Tampa Bay Rays",
    "TEX": "Texas Rangers", "TOR": "Toronto Blue Jays", "WSN": "Washington Nationals",
}


def fetch_war_leaderboards(season, qual=1):
    """Returns a list of {"name", "team", "role", "war"} dicts covering
    every qualifying batter and pitcher in FanGraphs' `season` leaderboard.
    qual=1 means "no minimum" (pybaseball's convention -- pass a higher
    number, or "y" for the league's own qualification cutoff, to shrink the
    pool). Requires `pip install pybaseball`."""
    import pybaseball  # imported lazily so the rest of this module can be
    pybaseball.cache.enable()  # inspected/imported without pybaseball installed

    bat = pybaseball.batting_stats(season, qual=qual)
    pit = pybaseball.pitching_stats(season, qual=qual)

    rows = []
    for _, r in bat.iterrows():
        rows.append({"name": r["Name"], "team": r["Team"], "role": "batter", "war": float(r[FG_WAR_COL])})
    for _, r in pit.iterrows():
        rows.append({"name": r["Name"], "team": r["Team"], "role": "pitcher", "war": float(r[FG_WAR_COL])})

    # Two-way players (Ohtani) show up once in each table under the same
    # name/team -- merge into a single "two-way" row with combined WAR
    # rather than letting one person occupy two bubbles on the same chart.
    by_name_team = {}
    for r in rows:
        key = (r["name"], r["team"])
        if key in by_name_team:
            existing = by_name_team[key]
            existing["role"] = "two-way"
            existing["war"] = round(existing["war"] + r["war"], 3)
        else:
            by_name_team[key] = dict(r)
    return list(by_name_team.values())


def fetch_team_payroll(team_abbr, pause=1.0):
    """Scrapes one team's RosterResource payroll page: returns
    (player_salary: {name: dollars}, total_payroll: float or None).
    `pause` is a polite delay between calls when looping over all 30 teams
    (see fetch_all_payrolls) -- RosterResource is a public page, not an API,
    so don't hammer it.

    Table structure (per a manual check of a handful of teams while writing
    this kit): each page has 2-4 tables -- "guaranteed", "arbitration-eligible",
    "pre-arbitration"/"not yet arbitration eligible", and sometimes "no
    longer on 40-man roster". This grabs every table pandas can find and
    takes the first two columns of each as (player, salary) -- if
    RosterResource changes its layout this is the first thing to check."""
    slug = RR_TEAM_SLUGS[team_abbr]
    url = f"https://www.fangraphs.com/roster-resource/payroll/{slug}"
    resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0 (personal sabermetrics dashboard)"})
    resp.raise_for_status()
    html = resp.text

    salaries = {}
    try:
        tables = pd.read_html(html)
    except ValueError:
        tables = []
    for t in tables:
        if t.shape[1] < 2:
            continue
        name_col, salary_col = t.columns[0], t.columns[1]
        for _, row in t.iterrows():
            name = str(row[name_col]).strip()
            raw = str(row[salary_col])
            match = re.search(r"[\d,]+", raw.replace("$", ""))
            if not name or name.lower() == "nan" or not match:
                continue
            salaries[name] = float(match.group(0).replace(",", ""))

    total = None
    m = re.search(r"Estimated Total (?:2\d{3} )?Payroll[:\s]*\$?([\d,.]+)\s*(million|M)?", html, re.IGNORECASE)
    if m:
        val = float(m.group(1).replace(",", ""))
        total = val * 1_000_000 if (m.group(2) or "").lower().startswith("m") and val < 10_000 else val

    time.sleep(pause)
    return salaries, total


def fetch_all_payrolls(team_abbrs=None):
    """Loops fetch_team_payroll over every team (or a subset). Returns
    {abbr: {"salaries": {name: dollars}, "total": float or None}}. Takes
    ~30-60 seconds for all 30 teams given the polite per-team pause."""
    team_abbrs = team_abbrs or list(RR_TEAM_SLUGS.keys())
    out = {}
    for abbr in team_abbrs:
        try:
            salaries, total = fetch_team_payroll(abbr)
            out[abbr] = {"salaries": salaries, "total": total}
            print(f"  {abbr}: {len(salaries)} players, total ${total/1e6:.0f}M" if total else f"  {abbr}: {len(salaries)} players, total unknown")
        except Exception as e:
            print(f"  {abbr}: FAILED ({e}) -- skipping, check RR_TEAM_SLUGS / page structure")
    return out
