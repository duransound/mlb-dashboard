"""
Builds the MLB value-vs-cost dashboard (dashboard_demo.html,
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
    add_derived_fields, build_awards_race, build_diminishing_returns,
    build_payroll_efficiency, build_price_of_win, build_story_lede,
    build_surplus_value_chart, build_takeaways, build_team_compare_chart,
    build_team_spend_chart, build_team_stories, build_value_scatter,
)
from dashboard_template import render_dashboard
from mlb_snapshot_data import (
    MARKET_RATE_PER_WAR, PLAYER_ROWS, TEAM_NAMES, TEAM_PAYROLL,
)

# The demo snapshot carries no team records: this kit's sandbox can't reach a
# standings source, and inventing W-L figures to fill a demo would put fake
# numbers on a page whose whole point is that its numbers are checkable. The
# awards tab degrades to WAR-based team context when this is empty, which is
# exactly the path a failed live standings scrape takes -- so the demo build
# also serves as the regression test for that fallback.
STANDINGS = {}


def build():
    rows = add_derived_fields(PLAYER_ROWS, MARKET_RATE_PER_WAR)

    # Tab order is the argument's order: price the unit -> show who beats
    # that price -> name them -> ask whether paying more works at all ->
    # zoom out to teams -> let the reader explore -> close with the point.
    charts = [
        build_price_of_win(rows, MARKET_RATE_PER_WAR),
        build_value_scatter(rows, TEAM_NAMES),
        build_surplus_value_chart(rows, MARKET_RATE_PER_WAR),
        build_diminishing_returns(rows, TEAM_NAMES),
        build_awards_race(rows, STANDINGS, TEAM_NAMES),
        build_payroll_efficiency(rows, TEAM_PAYROLL, TEAM_NAMES),
        build_team_spend_chart(rows, TEAM_PAYROLL, TEAM_NAMES),
        build_team_stories(rows, TEAM_NAMES, STANDINGS, MARKET_RATE_PER_WAR),
        build_team_compare_chart(rows, TEAM_NAMES),
    ]
    charts.append(build_takeaways(charts, rows, TEAM_PAYROLL, TEAM_NAMES,
                                  MARKET_RATE_PER_WAR, 2026))
    story = build_story_lede(charts, rows, TEAM_PAYROLL, TEAM_NAMES, MARKET_RATE_PER_WAR)

    html = render_dashboard(
        title="MLB Value vs. Cost",
        subtitle=(f"What baseball's wins actually cost, and who is buying them cheapest — {len(rows)} tracked "
                   f"players across {len({r['team'] for r in rows})} teams, 2026 season-to-date. "
                   "This is the demo snapshot; see Methods & Sources, or run build_dashboard.py for the "
                   "full league."),
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
