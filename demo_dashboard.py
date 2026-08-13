"""
Builds the "Diamond Dollars" MLB value-vs-cost dashboard (dashboard_demo.html,
copied to index.html for GitHub Pages) from the hand-verified 2026 snapshot in
mlb_snapshot_data.py. See build_dashboard.py for the live-data version that
pulls the full league on your own machine.

Run:
    python demo_dashboard.py

Writes dashboard_demo.html and index.html (identical content -- index.html
is what GitHub Pages actually serves; dashboard_demo.html is kept under its
descriptive name for local reference, same convention as the NWSL kit this
project is modeled on).
"""

from chart_builders import (
    add_derived_fields, build_mvp_tracker, build_story_lede,
    build_surplus_value_chart, build_team_compare_chart,
    build_team_spend_chart, build_value_scatter,
)
from dashboard_template import render_dashboard
from mlb_snapshot_data import (
    MARKET_RATE_PER_WAR, PLAYER_ROWS, TEAM_NAMES, TEAM_PAYROLL,
)


def build():
    rows = add_derived_fields(PLAYER_ROWS, MARKET_RATE_PER_WAR)

    chart_value = build_value_scatter(rows, TEAM_NAMES)
    chart_mvp = build_mvp_tracker(rows)
    chart_surplus = build_surplus_value_chart(rows, MARKET_RATE_PER_WAR)
    chart_team_spend = build_team_spend_chart(rows, TEAM_PAYROLL, TEAM_NAMES)
    chart_compare = build_team_compare_chart(rows, TEAM_NAMES)

    charts = [chart_value, chart_mvp, chart_surplus, chart_team_spend, chart_compare]
    story = build_story_lede(charts)

    html = render_dashboard(
        title="Diamond Dollars — MLB Value vs. Cost",
        subtitle=("Comparing what MLB players produce (WAR) against what they're paid, 2026 season-to-date. "
                   "A curated 47-player sample across 15 teams — see the README for why, and how to pull the "
                   "full league yourself."),
        charts=charts,
        story=story,
        story_kicker="2026 season, through 8/13",
    )
    return html


if __name__ == "__main__":
    html = build()
    with open("dashboard_demo.html", "w") as f:
        f.write(html)
    with open("index.html", "w") as f:
        f.write(html)
    print(f"Wrote dashboard_demo.html and index.html ({len(html):,} bytes)")
