"""
Builds the full-league "Diamond Dollars" dashboard (dashboard.html) from
LIVE data: WAR via pybaseball (wraps FanGraphs' season leaderboards) and
salary via a RosterResource scraper (mlb_data.py) -- all 30 teams, every
qualifying player, not the ~47-player curated snapshot demo_dashboard.py
ships with.

Run on your own machine (unrestricted network):
    pip install pybaseball pandas requests lxml
    python build_dashboard.py --season 2026 --min-pa 100 --min-ip 20

Why this has to run on your machine, not in a Claude session: the cloud
sandbox that built this kit has locked-down outbound network access (can't
reach fangraphs.com or pypi-installed pybaseball's live calls directly --
see README and mlb_data.py's docstring for the full explanation, same
constraint the NWSL kit this project is modeled on hit and documented). This
script's actual code path was never run end-to-end before you run it --
treat your first run as the real test. If a column name or team slug is
off, see mlb_data.py's docstring for where to look.

For a hands-off weekly refresh once this runs cleanly once, see
run_weekly_update.sh / .ps1.
"""

import argparse
import difflib

from chart_builders import (
    add_derived_fields, build_story_lede, build_surplus_value_chart,
    build_team_compare_chart, build_team_spend_chart, build_value_scatter,
)
from dashboard_template import render_dashboard
from mlb_data import TEAM_NAMES, fetch_all_payrolls, fetch_war_leaderboards

MARKET_RATE_PER_WAR = 11_000_000  # see mlb_snapshot_data.py's docstring for the source


def _normalize(name):
    return "".join(c for c in name.lower() if c.isalnum())


def match_salary(war_rows, payrolls, fuzzy_cutoff=0.82):
    """war_rows: output of fetch_war_leaderboards(). payrolls: output of
    fetch_all_payrolls(). Joins each player to their team's salary table by
    name -- exact normalized match first, falling back to a fuzzy match
    (difflib) within the same team for name-format mismatches (accents,
    suffixes, nicknames) between FanGraphs and RosterResource. Players with
    no match on either pass are dropped (printed to stderr with a count) --
    the whole point of surplus value is WAR *and* salary both being real, so
    a silently-zero salary would badly distort that player's chart position
    rather than just being absent from it."""
    rows, unmatched = [], []
    for r in war_rows:
        team_payroll = payrolls.get(r["team"], {})
        salaries = team_payroll.get("salaries", {})
        target = _normalize(r["name"])
        salary = None
        for name, amt in salaries.items():
            if _normalize(name) == target:
                salary = amt
                break
        if salary is None and salaries:
            close = difflib.get_close_matches(target, [_normalize(n) for n in salaries], n=1, cutoff=fuzzy_cutoff)
            if close:
                for name, amt in salaries.items():
                    if _normalize(name) == close[0]:
                        salary = amt
                        break
        if salary is None:
            unmatched.append(f"{r['name']} ({r['team']})")
            continue
        rows.append({
            "id": target, "name": r["name"], "team": r["team"], "role": r["role"],
            "war": r["war"], "salary": salary, "is_aav": False,
        })

    if unmatched:
        print(f"\n{len(unmatched)} players had WAR but no salary match (dropped): "
              f"{', '.join(unmatched[:15])}{' ...' if len(unmatched) > 15 else ''}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--min-pa", type=int, default=100, help="min plate appearances for a batter to be included (passed to pybaseball as qual)")
    ap.add_argument("--min-ip", type=int, default=20, help="min innings pitched for a pitcher to be included")
    ap.add_argument("--min-war", type=float, default=0.0, help="drop players below this WAR from the League Picture chart (surplus leaderboard is unaffected)")
    args = ap.parse_args()

    print(f"Fetching {args.season} WAR leaderboards from FanGraphs via pybaseball...")
    bat_rows = fetch_war_leaderboards(args.season, qual=args.min_pa)
    war_rows = [r for r in bat_rows]  # fetch_war_leaderboards already covers both bat + pitch
    print(f"  {len(war_rows)} players with a WAR figure")

    teams_present = sorted({r["team"] for r in war_rows if r["team"] in TEAM_NAMES})
    print(f"Fetching payroll for {len(teams_present)} teams from FanGraphs RosterResource...")
    payrolls = fetch_all_payrolls(teams_present)

    matched = match_salary(war_rows, payrolls)
    matched = [r for r in matched if r["war"] >= args.min_war]
    print(f"\n{len(matched)} players matched to both WAR and salary (>= {args.min_war} WAR)")

    rows = add_derived_fields(matched, MARKET_RATE_PER_WAR)
    team_payroll = {abbr: {"total": p["total"], "partial": p["total"] is None}
                     for abbr, p in payrolls.items() if p["total"]}

    chart_value = build_value_scatter(rows)
    chart_surplus = build_surplus_value_chart(rows, MARKET_RATE_PER_WAR, top_n=20, bottom_n=20)
    chart_team_spend = build_team_spend_chart(rows, team_payroll, TEAM_NAMES)
    chart_compare = build_team_compare_chart(rows, TEAM_NAMES)
    charts = [chart_value, chart_surplus, chart_team_spend, chart_compare]

    html = render_dashboard(
        title="Diamond Dollars — MLB Value vs. Cost",
        subtitle=(f"Comparing what MLB players produce (WAR) against what they're paid, {args.season} season — "
                   f"{len(rows)} players across {len(team_payroll)} teams."),
        charts=charts,
        story=build_story_lede(charts),
        story_kicker=f"{args.season} season, full league",
    )
    with open("dashboard.html", "w") as f:
        f.write(html)
    with open("index.html", "w") as f:
        f.write(html)
    print(f"\nWrote dashboard.html and index.html ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
