"""
Shared chart-construction logic for the MLB "Diamond Dollars" value-vs-cost
dashboard, used by BOTH demo_dashboard.py (the hand-verified snapshot that
ships as index.html) and build_dashboard.py (the live version you run
locally against the full league). Modeled directly on the NWSL xG starter
kit's chart_builders.py -- same split (one function per chart, one
implementation shared by both the demo and live paths) for the same reason:
a future change to how a chart is built (a new highlight rule, a tooltip
field) should be one edit here, not two files quietly drifting apart.

Every function takes plain player/team rows (see each docstring for the
exact shape) and returns a chart-config dict in the shape dashboard_template.
py's JS engine understands (see that file's drawScatter/drawDivergingBar/
drawTeamCompare). Money is passed to the chart layer already converted to
millions (salary_m, surplus_m, payroll_m) since a raw dollar axis reads
worse than "$26.8M" -- the underlying dict fields on PLAYER_ROWS stay in
whole dollars, this is purely a presentation-layer conversion.
"""


def add_derived_fields(rows, market_rate):
    """rows: list of dicts matching mlb_snapshot_data.PLAYER_ROWS' shape
    (id, name, team, role, war, salary, is_aav[, note]). Returns a NEW list
    with salary_m, surplus (dollars), surplus_m, and dollar_per_war added --
    doesn't mutate the input, so the same raw rows can feed multiple charts
    without one chart's rounding leaking into another's."""
    out = []
    for r in rows:
        salary_m = r["salary"] / 1_000_000
        surplus = (r["war"] * market_rate) - r["salary"]
        dollar_per_war = (r["salary"] / r["war"]) if r["war"] else None
        out.append({**r, "salary_m": salary_m, "surplus": surplus,
                    "surplus_m": surplus / 1_000_000, "dollar_per_war": dollar_per_war})
    return out


def _cost_note(r):
    return " (AAV)" if r.get("is_aav") else ""


def scatter_display_params(n):
    """Adaptive bubble radius for the League Picture / Team Spending scatter
    charts -- the demo snapshot is a curated ~47 points (radius 13 reads
    fine), but a live full-league run (build_dashboard.py) can be several
    hundred. Same idea as the NWSL kit's scatter_display_params: past a
    point, a big fixed radius turns a full-league scatter into an
    unreadable pile of overlapping bubbles."""
    if n > 150:
        return 6
    if n > 60:
        return 9
    return 13


def build_value_scatter(rows):
    """rows: output of add_derived_fields(). Returns the League Picture
    scatter -- WAR (up) vs. Salary in $M (right), one bubble per player,
    badge = team abbreviation. Median lines split the sample into four
    quadrants (Design Guidelines "preattentive attributes for focus" --
    dashed lines are structure, not a second highlighted series). The single
    highlighted point is whoever delivered the most WAR per salary dollar in
    this sample, i.e. the best-value bubble in the top-left "cheap and great"
    quadrant."""
    best = max(rows, key=lambda r: r["war"] / r["salary_m"])
    per_m = best["war"] / best["salary_m"]
    return {
        "type": "scatter", "tabLabel": "League Picture",
        "metricLabel": "WAR vs. Salary, 2026 season",
        "title": f"{best['name']} is producing {per_m:.2f} WAR per $1M of salary — the best return in this sample",
        "blurb": (f"Wins Above Replacement (WAR, y-axis) vs. salary in millions (x-axis) for {len(rows)} tracked "
                   "players (see the README for sample coverage). Dashed lines mark the sample's median WAR and "
                   "median salary — top-left is cheap-and-great, bottom-right is expensive-and-underperforming."),
        "xAxisLabel": "Salary ($M)", "yAxisLabel": "WAR",
        "medianLines": True, "radius": scatter_display_params(len(rows)),
        "data": [
            {"x": round(r["salary_m"], 3), "y": r["war"], "badge": r["team"],
             "tooltip": (f'<div class="name">{r["name"]}</div>'
                         f'<div class="row">{r["team"]} &middot; {r["role"]}</div>'
                         f'<div class="row">WAR {r["war"]:.1f} &middot; Salary ${r["salary_m"]:.1f}M{_cost_note(r)}</div>'
                         f'<div class="row">Surplus vs. market: ${r["surplus_m"]:+.1f}M</div>'),
             "highlight": r["id"] == best["id"],
             "annotation": f"{best['name'].split()[-1]}: {best['war']:.1f} WAR on ${best['salary_m']:.2f}M" if r["id"] == best["id"] else None}
            for r in rows
        ],
    }


def build_surplus_value_chart(rows, market_rate, top_n=15, bottom_n=10):
    """rows: output of add_derived_fields(). Surplus = (WAR x market_rate)
    minus actual salary -- positive means the player produced more market
    value than they were paid (a bargain), negative means the reverse (an
    overpay relative to the sample's blended $/WAR rate). Capped to the
    top_n biggest bargains + bottom_n biggest overpays (not all 47 rows) --
    a ranked leaderboard reads better at ~25 bars than at 47, the same call
    the NWSL kit made for its Goals Added leaderboard (see that project's
    README, "full-league player pool instead of a top-N cut")."""
    ranked = sorted(rows, key=lambda r: r["surplus"], reverse=True)
    pool = ranked[:top_n] + ([] if bottom_n <= 0 else ranked[-bottom_n:])
    # de-dupe in case top_n + bottom_n overlaps the full sample
    seen, deduped = set(), []
    for r in pool:
        if r["id"] not in seen:
            seen.add(r["id"])
            deduped.append(r)

    best = max(deduped, key=lambda r: r["surplus"])
    worst = min(deduped, key=lambda r: r["surplus"])
    extreme = best if abs(best["surplus"]) >= abs(worst["surplus"]) else worst
    if extreme["surplus"] >= 0:
        title = (f"{extreme['name']} is the sample's biggest bargain — about "
                  f"${extreme['surplus_m']:.0f}M more production than salary, at an assumed "
                  f"${market_rate/1_000_000:.0f}M per WAR")
    else:
        title = (f"{extreme['name']} is the sample's biggest overpay — about "
                  f"${abs(extreme['surplus_m']):.0f}M more salary than production, at an assumed "
                  f"${market_rate/1_000_000:.0f}M per WAR")

    return {
        "type": "diverging-bar", "tabLabel": "Surplus Value",
        "metricLabel": "Surplus Value (market value of WAR minus salary)",
        "title": title,
        "blurb": (f"Top {len([r for r in deduped if r['surplus']>=0])} bargains and bottom "
                   f"{len([r for r in deduped if r['surplus']<0])} overpays in the sample, by surplus dollars. "
                   f"Market value = WAR x ${market_rate/1_000_000:.0f}M (the 2025-26 free-agent market's overall "
                   "average cost per win, per FanGraphs — see README for the source and its limits as a single "
                   "blended rate)."),
        "valueLabel": "Surplus ($M)", "xAxisLabel": "Surplus vs. market value ($M)",
        "footnote": "Positive = produced more market value than salary paid (underpaid); negative = the reverse (overpaid) relative to the sample's blended $/WAR rate.",
        "data": [
            {"label": f'{r["name"]} ({r["team"]})', "value": round(r["surplus_m"], 1),
             "highlight": r["id"] == extreme["id"],
             "extra": f'WAR {r["war"]:.1f} &middot; Salary ${r["salary_m"]:.1f}M{_cost_note(r)}'}
            for r in deduped
        ],
    }


def build_team_spend_chart(rows, team_payroll, team_names):
    """rows: output of add_derived_fields(). team_payroll: {abbr: {"total":
    dollars, "partial": bool}}. Sums each team's curated-sample WAR (NOT a
    full 40-man-roster WAR total -- see the chart's own footnote) against
    that team's overall estimated payroll, one bubble per team. Highlights
    the team getting the most sample-WAR per payroll dollar."""
    by_team = {}
    for r in rows:
        t = by_team.setdefault(r["team"], {"war": 0.0, "n": 0})
        t["war"] += r["war"]
        t["n"] += 1

    team_rows = []
    for abbr, agg in by_team.items():
        payroll = team_payroll.get(abbr)
        if not payroll:
            continue
        team_rows.append({
            "abbr": abbr, "name": team_names.get(abbr, abbr),
            "war": agg["war"], "n": agg["n"],
            "payroll_m": payroll["total"] / 1_000_000, "partial": payroll["partial"],
        })

    best = max(team_rows, key=lambda t: t["war"] / t["payroll_m"])
    return {
        "type": "scatter", "tabLabel": "Team Spending vs. Production",
        "metricLabel": "Team payroll vs. sample WAR produced",
        "title": f"{best['name']} gets the most sample WAR per payroll dollar of the 15 teams covered here",
        "blurb": ("Each team's estimated total 2026 payroll (x-axis, all 40-man roster salary, not just the "
                   "players in this sample) vs. the combined WAR of THIS SAMPLE'S players on that roster "
                   "(y-axis) — not the team's true total WAR, since this dashboard only tracks the curated "
                   "player set described in the README. Reads best as \"how much of what this team is paying "
                   "for shows up in the players we're tracking,\" not a full efficiency ranking."),
        "xAxisLabel": "Estimated total 2026 payroll ($M)", "yAxisLabel": "Sample WAR (players tracked on this roster)",
        "medianLines": True, "radius": 15,
        "data": [
            {"x": round(t["payroll_m"], 1), "y": round(t["war"], 1), "badge": t["abbr"],
             "tooltip": (f'<div class="name">{t["name"]}</div>'
                         f'<div class="row">Payroll ${t["payroll_m"]:.0f}M{" (partial, listed players only)" if t["partial"] else ""}</div>'
                         f'<div class="row">Sample WAR {t["war"]:.1f} ({t["n"]} players tracked)</div>'),
             "highlight": t["abbr"] == best["abbr"],
             "annotation": f"{best['abbr']}: {best['war']:.1f} sample WAR on ${best['payroll_m']:.0f}M payroll" if t["abbr"] == best["abbr"] else None}
            for t in team_rows
        ],
    }


def build_team_compare_chart(rows, team_names):
    """rows: output of add_derived_fields(). Dropdown-driven explorer tab --
    pick a team (of the 15 covered), pick a metric, see that team's tracked
    players ranked. Same drawTeamCompare/drawDivergingBar pattern the NWSL
    kit uses for its Compare Teammates tab."""
    rosters = {}
    for r in rows:
        rosters.setdefault(r["team"], []).append({
            "name": r["name"], "war": r["war"], "salary_m": round(r["salary_m"], 2),
            "surplus_m": round(r["surplus_m"], 1),
        })
    for abbr in rosters:
        rosters[abbr] = sorted(rosters[abbr], key=lambda p: p["war"], reverse=True)

    return {
        "type": "team-compare", "tabLabel": "Compare Teammates",
        "metricLabel": "Team Roster Comparison",
        "title": "Compare tracked teammates head-to-head",
        "blurb": "Pick one of the 15 tracked teams to see how its players in this sample stack up on WAR, salary, or surplus value.",
        "footnote": "Only players in this dashboard's curated sample appear here — not a full 40-man roster.",
        "teamNames": team_names,
        "rosters": rosters,
        "stats": [
            {"key": "war", "label": "WAR"},
            {"key": "salary_m", "label": "Salary ($M)", "suffix": "M"},
            {"key": "surplus_m", "label": "Surplus Value ($M)", "suffix": "M"},
        ],
    }


def build_story_lede(charts):
    """Dashboard-level "Big Idea" for the top of the page, stitched from two
    already-computed chart insights (League Picture + Surplus Value) rather
    than a fresh pass over raw data -- same approach as the NWSL kit's
    build_story_lede, and for the same reason: every chart's `title` is
    already a vetted, insight-stating sentence, so reusing it verbatim can
    never assert something a tab doesn't support."""
    by_tab = {c["tabLabel"]: c for c in charts if c}
    lead = by_tab.get("League Picture")
    second = by_tab.get("Surplus Value")
    if not lead:
        return None
    sentences = [lead["title"].rstrip(".") + "."]
    if second and second is not lead:
        sentences.append(second["title"].rstrip(".") + ".")
    return " ".join(sentences)
