"""
Shared chart-construction logic for the MLB value-vs-cost
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


# ---------------------------------------------------------------------------
# Data provenance
#
# Every chart carries a `source` line naming exactly where its numbers came
# from, rendered under the chart. Sourcing lived only in the Methods panel
# before, which meant a chart screenshotted or linked on its own travelled
# with no attribution at all -- and these are other people's datasets.
# ---------------------------------------------------------------------------

SOURCE_LINKS = {
    "bref": '<a href="https://www.baseball-reference.com/" rel="noopener">Baseball-Reference</a>',
    "spotrac": '<a href="https://www.spotrac.com/mlb/" rel="noopener">Spotrac</a>',
    "fangraphs": '<a href="https://blogs.fangraphs.com/" rel="noopener">FanGraphs</a>',
}

SRC_WAR = f'WAR: {SOURCE_LINKS["bref"]}'
SRC_SALARY = f'salaries: {SOURCE_LINKS["spotrac"]}'
SRC_RATE = f'$/win benchmark: {SOURCE_LINKS["fangraphs"]}'
SRC_RECORDS = f'team records: {SOURCE_LINKS["bref"]}'


def _source(*parts):
    """Assembles the per-chart credit line. Kept as a helper so every chart
    spells the sources the same way and a source URL only ever changes in
    one place."""
    return "Source — " + "; ".join(parts) + "."


SOURCE_VALUE = _source(SRC_WAR, SRC_SALARY, SRC_RATE)
SOURCE_WAR_ONLY = _source(SRC_WAR)
SOURCE_WAR_SALARY = _source(SRC_WAR, SRC_SALARY)
SOURCE_AWARDS = _source(SRC_WAR, SRC_RECORDS, SRC_SALARY)


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


def _possessive(name):
    """"Los Angeles Dodgers" -> "Dodgers'"; "Houston Astros" -> "Astros'";
    "Detroit Tigers" -> "Tigers'"; anything not already ending in "s" gets
    the normal "'s" (e.g. "Boston Red Sox" -> "Red Sox's"). Mirrors the same
    rule dashboard_template.py's drawScatter applies in JS for its own
    (shorter) fallback caption -- kept in sync so neither path produces the
    "Dodgers's" mistake."""
    return name + "'" if name.endswith("s") else name + "'s"


def build_team_blurbs(rows, team_names):
    """rows: output of add_derived_fields(). team_names: {abbr: full name}.
    Returns {abbr: blurb} -- a short, data-grounded STORY about each team's
    tracked players (verdict, then evidence, then the people behind it),
    computed once here (alongside every other chart's vetted insight
    sentences) rather than re-derived in JS from raw rows -- same "insight
    text is pre-computed, JS only renders" convention used everywhere else
    in this dashboard. Surfaced next to a Team dropdown (League Picture,
    Compare Teammates) once that team is picked.

    Written in a lead-with-the-takeaway, assertion-evidence style (open with
    the verdict a reader would want to know first -- bargain or overpay --
    then back it up with the number, then name the people who made it true)
    rather than a flat list of stats, so it reads like a sentence someone
    would actually say about the team, not a stat line."""
    by_team = {}
    for r in rows:
        by_team.setdefault(r["team"], []).append(r)

    blurbs = {}
    for abbr, players in by_team.items():
        team_full = team_names.get(abbr, abbr)
        n = len(players)
        roster_word = "player" if n == 1 else "players"
        verb = "has" if n == 1 else "have"
        total_war = sum(p["war"] for p in players)
        total_salary_m = sum(p["salary_m"] for p in players)
        total_surplus_m = sum(p["surplus_m"] for p in players)
        best_value = max(players, key=lambda p: (p["war"] / p["salary_m"]) if p["salary_m"] else float("-inf"))
        priciest = max(players, key=lambda p: p["salary_m"])

        if total_surplus_m >= 0:
            verdict = f"The {team_full} are getting a bargain."
            gap_sentence = (f"Their {n} tracked {roster_word} {verb} produced {total_war:.1f} wins above "
                             f"replacement for a combined ${total_salary_m:.1f}M — about ${total_surplus_m:.0f}M "
                             "more than the open market would charge for that kind of production.")
        else:
            verdict = f"The {team_full} are paying a premium."
            gap_sentence = (f"Their {n} tracked {roster_word} {verb} produced {total_war:.1f} wins above "
                             f"replacement for a combined ${total_salary_m:.1f}M — about "
                             f"${abs(total_surplus_m):.0f}M more than the open market would charge for that "
                             "kind of production.")

        if best_value["id"] == priciest["id"]:
            people_sentence = (f"{best_value['name']} is both the best value on the roster and its biggest "
                                f"expense, putting up {best_value['war']:.1f} WAR on ${best_value['salary_m']:.1f}M.")
        else:
            people_sentence = (f"{best_value['name']} is doing the heavy lifting — {best_value['war']:.1f} WAR "
                                f"on just ${best_value['salary_m']:.1f}M — while {priciest['name']} carries the "
                                f"roster's biggest price tag at ${priciest['salary_m']:.1f}M.")

        blurbs[abbr] = f"{verdict} {gap_sentence} {people_sentence}"
    return blurbs


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


def build_value_scatter(rows, team_names=None):
    """rows: output of add_derived_fields(). team_names: optional {abbr:
    full name} dict (e.g. mlb_data.TEAM_NAMES) -- when given, the League
    Picture tab gets a "Team" dropdown that highlights one team's players
    against the full-league backdrop rather than filtering the rest out,
    since the point of this chart is seeing a roster relative to the whole
    league. Returns the League Picture scatter -- WAR (up) vs. Salary in $M
    (right, log scale), one bubble per player, badge = team abbreviation.
    Median lines split the sample into four quadrants (Design Guidelines
    "preattentive attributes for focus" -- dashed lines are structure, not a
    second highlighted series). The single highlighted point (when no team
    is picked) is whoever delivered the most WAR per salary dollar in this
    sample, i.e. the best-value bubble in the top-left "cheap and great"
    quadrant."""
    best = max(rows, key=lambda r: r["war"] / r["salary_m"])
    per_m = best["war"] / best["salary_m"]
    return {
        "type": "scatter", "tabLabel": "League Picture",
        "source": SOURCE_WAR_SALARY,
        "metricLabel": "WAR vs. Salary, 2026 season",
        "title": f"{best['name']} is producing {per_m:.2f} WAR per $1M of salary — the best return in this sample",
        "blurb": (f"Every dot is a player: how many wins they've added (WAR, up the side) against what it cost "
                   f"to add them (salary, across the bottom), for {len(rows)} tracked players. The players worth talking about live in the top-left — great "
                   "production for not much money — while the bottom-right is where expensive disappointments "
                   "hide. (Salary runs on a log scale so a $2M reliever and a $35M ace don't get crushed into "
                   "the same sliver of the chart.) The dashed lines mark the sample's median WAR and median "
                   "salary, splitting the field into those four quadrants. Pick a team to see where its "
                   "roster falls, and use the salary-range dropdown to zoom into a pay band — a third of the "
                   "league is packed into a few hundred thousand dollars at the minimum, and zooming spreads "
                   "that crowd across the full width of the chart."),
        "xAxisLabel": "Salary ($M, log scale)", "yAxisLabel": "WAR", "xScaleType": "log",
        "medianLines": True, "radius": scatter_display_params(len(rows)),
        # Salary-range zoom. Bands are chosen around real contract structure
        # rather than even splits, because that's where the crowding is: at
        # full-league scale roughly a third of the league sits inside a
        # $250K-wide band at the league minimum, which even a log axis
        # compresses into a sliver.
        "zoomLabel": "Salary range",
        "zoomBands": [
            {"label": "All salaries"},
            {"label": "Under $1M (league minimum)", "max": 1.0},
            {"label": "$1M–$10M", "min": 1.0, "max": 10.0},
            {"label": "$10M and up", "min": 10.0},
        ],
        "teamNames": team_names or {},
        "teamBlurbs": build_team_blurbs(rows, team_names) if team_names else {},
        "data": [
            {"x": round(r["salary_m"], 3), "y": r["war"], "badge": r["team"], "team": r["team"],
             "tooltip": (f'<div class="name">{r["name"]}</div>'
                         f'<div class="row">{r["team"]} &middot; {r["role"]}</div>'
                         f'<div class="row">WAR {r["war"]:.1f} &middot; Salary ${r["salary_m"]:.1f}M{_cost_note(r)}</div>'
                         f'<div class="row">Surplus vs. market: ${r["surplus_m"]:+.1f}M</div>'),
             "highlight": r["id"] == best["id"],
             "annotation": f"{best['name'].split()[-1]}: {best['war']:.1f} WAR on ${best['salary_m']:.2f}M" if r["id"] == best["id"] else None}
            for r in rows
        ],
    }


def _contract_tier(r):
    """Salary as a proxy for contract status. There is no service-time field
    anywhere in this dataset, but MLB's pay structure makes salary a strong
    stand-in: a player earning near the league minimum is, almost by
    definition, not yet arbitration-eligible, because the CBA doesn't permit
    paying them market value yet."""
    if r["salary"] < 1_000_000:
        return "Pre-arbitration (under $1M)"
    if r["salary"] < 10_000_000:
        return "Arbitration years ($1–10M)"
    return "Market-priced ($10M+)"


CONTRACT_TIERS = [
    "All contracts",
    "Pre-arbitration (under $1M)",
    "Arbitration years ($1–10M)",
    "Market-priced ($10M+)",
]


def build_surplus_value_chart(rows, market_rate, top_n=15, bottom_n=10, team_names=None):
    """Paid vs. Produced: (WAR x market_rate) minus actual salary.

    Two picker axes: **Team** and **Contract status**.

    The contract split exists because a single combined leaderboard of
    "biggest bargains" is, in a sport with a rookie wage scale, guaranteed to
    be topped by players who are cheap BY RULE. On the live 872-player build
    the median salary on the bargain side was $0.80M against $19.7M on the
    overpay side, and 13 of the top 20 "bargains" earned under $1M. That
    ranking is the collective bargaining agreement, not scouting insight.
    Within "Market-priced," over- and underpay really is a team decision and
    the leaderboard means what it appears to mean.

    The team axis lets a reader ask the same question of one roster. Team
    views are small by nature, so their captions report how many players the
    view actually contains rather than implying a league-scale ranking."""
    market_rate_m = market_rate / 1_000_000

    total_salary_m = sum(r["salary_m"] for r in rows)
    total_war = sum(r["war"] for r in rows)
    blended_m = (total_salary_m / total_war) if total_war > 0 else None

    def leaderboard(pool):
        ranked = sorted(pool, key=lambda r: r["surplus"], reverse=True)
        picked = ranked[:top_n] + ([] if bottom_n <= 0 else ranked[-bottom_n:])
        seen, deduped = set(), []
        for r in picked:
            if r["id"] not in seen:
                seen.add(r["id"])
                deduped.append(r)
        return deduped

    def tier_caption(tier, deduped, scope_note):
        positives = [r for r in deduped if r["surplus"] >= 0]
        under_min = sum(1 for r in deduped if r["surplus"] > 0 and r["salary"] < 1_000_000)
        if tier == "All contracts":
            return (f"<strong>Read this one with suspicion.</strong> {under_min} of the "
                    f"{len(positives)} players on the underpaid side earn under $1M — they're cheap "
                    "because the rules don't allow paying them more yet, not because anyone "
                    "out-negotiated the market. Switch to <em>Market-priced</em> for the version where "
                    f"over- and underpay is actually a decision somebody made. {scope_note}")
        if tier.startswith("Pre-arbitration"):
            return ("<strong>Everyone here is underpaid by design.</strong> Pre-arbitration salaries are set "
                    "near the league minimum regardless of production, so this ranks who has produced most, "
                    "not who was signed most cleverly — and every name is a raise already earned and not yet "
                    f"paid. {scope_note}")
        if tier.startswith("Arbitration"):
            return ("<strong>The middle years.</strong> Arbitration moves salary toward production but lags "
                    "it, so surplus here is smaller than in the pre-arb group and more genuinely earned than "
                    f"in the market-priced one. {scope_note}")
        return ("<strong>This is the honest scoreboard.</strong> Everyone here is paid at or near market "
                "value, so a big number in either direction reflects a decision somebody made — a contract "
                f"that has aged well, or one that hasn't. {scope_note}")

    def build_group(pool, tier, scope_note, title=None):
        deduped = leaderboard(pool)
        if not deduped:
            return None
        best = max(deduped, key=lambda r: r["surplus"])
        worst = min(deduped, key=lambda r: r["surplus"])
        extreme = best if abs(best["surplus"]) >= abs(worst["surplus"]) else worst
        group = {
            "caption": tier_caption(tier, deduped, scope_note),
            "data": [
                {"label": f'{r["name"]} ({r["team"]})', "value": round(r["surplus_m"], 1),
                 "highlight": r["id"] == extreme["id"],
                 "extra": f'WAR {r["war"]:.1f} &middot; Salary ${r["salary_m"]:.1f}M{_cost_note(r)}'}
                for r in deduped
            ],
        }
        if title:
            group["title"] = title
        return group

    SEP = "\u001f"
    groups = {}
    team_options = ["All of MLB"]

    for tier in CONTRACT_TIERS:
        pool = rows if tier == "All contracts" else [r for r in rows if _contract_tier(r) == tier]
        note = f"Drawn from all {len(pool)} tracked players in this contract group."
        g = build_group(pool, tier, note)
        if g:
            groups["All of MLB" + SEP + tier] = g

    if team_names:
        by_team = {}
        for r in rows:
            by_team.setdefault(r["team"], []).append(r)
        for abbr in sorted(by_team, key=lambda a: team_names.get(a, a)):
            name = team_names.get(abbr, abbr)
            added = False
            for tier in CONTRACT_TIERS:
                pool = ([r for r in by_team[abbr]] if tier == "All contracts"
                        else [r for r in by_team[abbr] if _contract_tier(r) == tier])
                if not pool:
                    continue
                # Team views are inherently small: say so, so nobody reads a
                # four-bar chart as a league ranking.
                note = (f"This view is just the {len(pool)} tracked "
                        f"{'player' if len(pool) == 1 else 'players'} on the {name} in this contract group — "
                        "a roster slice, not a league leaderboard.")
                surplus_total = sum(r["surplus_m"] for r in pool)
                verdict = ("ahead" if surplus_total >= 0 else "behind")
                title = (f'{name}, {tier.split(" (")[0].lower()}: about '
                         f'${abs(surplus_total):.0f}M {verdict} of what this group produced')
                g = build_group(pool, tier, note, title)
                if g:
                    groups[name + SEP + tier] = g
                    added = True
            if added:
                team_options.append(name)

    all_ranked = sorted(rows, key=lambda r: r["surplus"], reverse=True)[:top_n]
    cheap_share = (sum(1 for r in all_ranked if r["salary"] < 1_000_000) / len(all_ranked) * 100
                   if all_ranked else 0)
    if cheap_share >= 50:
        title = (f"{cheap_share:.0f}% of baseball's biggest bargains earn under $1M — they're not shrewd "
                 "signings, they're players the rules don't let teams pay yet")
    else:
        extreme_all = max(rows, key=lambda r: abs(r["surplus"]))
        verb = "more production than salary" if extreme_all["surplus"] >= 0 else "more salary than production"
        title = (f"{extreme_all['name']} is the biggest gap between pay and production — about "
                 f"${abs(extreme_all['surplus_m']):.0f}M {verb}")

    return {
        "type": "diverging-bar", "tabLabel": "Paid vs. Produced",
        "source": SOURCE_VALUE,
        "metricLabel": "The gap between what players earn and what they produce",
        "title": title,
        "blurb": (f"Multiply a player's WAR by what a win costs on the open market (about "
                  f"${market_rate_m:.0f}M), subtract what they're actually paid, and the difference is the "
                  "bar below — positive means the team got more than it paid for. "
                  "<strong>But a raw list of that gap mostly measures service time, not shrewdness</strong>, "
                  "because MLB's pay structure forbids paying young players market value at all. Use the "
                  "contract dropdown to compare players on similar deals, and the team dropdown to ask the "
                  "same question of one roster."),
        "valueLabel": "Gap ($M)", "xAxisLabel": "Market value of production minus salary ($M)",
        "groups": groups,
        "groupAxes": [
            {"label": "Team", "options": team_options},
            {"label": "Contract status", "options": list(CONTRACT_TIERS)},
        ],
        "defaultGroup": "All of MLB" + SEP + "All contracts",
        "emptyGroupNote": ("No tracked players on this team fall in that contract group — try "
                           "<em>All contracts</em>, or another team."),
        "footnote": (
            "Positive = produced more market value than salary paid; negative = the reverse. "
            f"Measured against the assumed open-market rate of ${market_rate_m:.0f}M per WAR — not "
            "against what this population actually costs"
            + (f", which is about ${blended_m:.1f}M per WAR (total salary divided by total WAR across every "
               "tracked player). The market rate is what it costs to BUY a win in free agency; the lower "
               "figure is what teams are already paying for the wins they have. Surplus totals here will "
               "sum well above zero for exactly that reason." if blended_m else ".")
            + " Contract status is inferred from salary — there is no service-time data in this dataset —"
              " so the tiers are a close proxy, not a roster status lookup."
        ),
    }


def build_team_spend_chart(rows, team_payroll, team_names):
    """rows: output of add_derived_fields(). team_payroll: {abbr: {"total":
    dollars, "partial": bool}}. Sums each team's curated-sample WAR (NOT a
    full 40-man-roster WAR total -- see the chart's own footnote) against
    that team's overall estimated payroll, one bubble per team.

    The headline is the payroll/production correlation rather than a
    best-team callout, because the correlation IS the finding: a low R² here
    is the evidence for the dashboard's central claim, and it was sitting
    uncomputed while the chart described a winner instead. Team counts and
    the season are read from the data, never hardcoded -- an earlier version
    asserted "the 15 teams covered here" in its title, which silently became
    false the moment the pipeline went full-league."""
    team_rows = _team_totals(rows, team_payroll, team_names)
    best = max(team_rows, key=lambda t: t["war"] / t["payroll_m"])
    r = _pearson_r([t["payroll_m"] for t in team_rows], [t["war"] for t in team_rows])
    r2 = (r * r) if r is not None else None

    if r2 is not None:
        title, _sentence = _r2_framing(r2, len(team_rows))
    else:
        title = f"{best['name']} get the most tracked WAR per payroll dollar"

    return {
        "type": "scatter", "tabLabel": "Team Spending vs. Production",
        "source": SOURCE_WAR_SALARY,
        "metricLabel": "Team payroll vs. production",
        "title": title,
        "blurb": ("Each dot is a team: total roster payroll across the bottom, the WAR this dashboard tracks "
                  "on that roster up the side. If money bought production reliably, these dots would form a "
                  "line running up and to the right. They don't. The teams above the pack are converting "
                  "payroll into wins; the ones below it are paying for production they aren't getting."
                  + (f" Statistically, {_r2_framing(r2, len(team_rows))[1]}".replace("<em>", "").replace("</em>", "")
                     if r2 is not None else "")),
        "xAxisLabel": "Total payroll ($M)", "yAxisLabel": "Tracked WAR on this roster",
        "medianLines": True, "radius": scatter_display_params(len(team_rows)) + 4,
        "footnote": ("Payroll is the full roster commitment; WAR counts only the players this dashboard "
                     "tracks. See Methods & Sources."),
        "data": [
            {"x": round(t["payroll_m"], 1), "y": round(t["war"], 1), "badge": t["abbr"],
             "tooltip": (f'<div class="name">{t["name"]}</div>'
                         f'<div class="row">Payroll ${t["payroll_m"]:.0f}M{" (partial, listed players only)" if t["partial"] else ""}</div>'
                         f'<div class="row">Tracked WAR {t["war"]:.1f} ({t["n"]} players)</div>'
                         f'<div class="row">{(t["war"] / t["payroll_m"]) * 10:.2f} WAR per $10M</div>'),
             "highlight": t["abbr"] == best["abbr"],
             "annotation": f"{best['abbr']}: {best['war']:.1f} WAR on ${best['payroll_m']:.0f}M" if t["abbr"] == best["abbr"] else None}
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
        "source": SOURCE_VALUE,
        "metricLabel": "Team Roster Comparison",
        "title": "Compare tracked teammates head-to-head",
        "blurb": f"Pick one of the {len(team_names)} tracked teams below to see who's producing, who's earning, and who's actually worth it.",
        "footnote": "Only players in this dashboard's curated sample appear here — not a full 40-man roster.",
        "teamNames": team_names,
        "teamBlurbs": build_team_blurbs(rows, team_names),
        "rosters": rosters,
        "stats": [
            {"key": "war", "label": "WAR"},
            {"key": "salary_m", "label": "Salary ($M)", "suffix": "M"},
            {"key": "surplus_m", "label": "Surplus Value ($M)", "suffix": "M"},
        ],
    }


# This dashboard's own fixed AL/NL assignment -- 30 teams, doesn't change
# season to season, but neither mlb_data.py's nor mlb_snapshot_data.py's
# TEAM_NAMES dict carries a league flag, so it lives here instead of forcing
# both data sources to agree on a new schema. ATH is the Athletics (their
# current-city branding is a moving target -- see mlb_data.py's team-slug
# docstring -- but the franchise stays AL West regardless of city name).
TEAM_LEAGUE = {
    "BAL": "AL", "BOS": "AL", "NYY": "AL", "TBR": "AL", "TOR": "AL",
    "CHW": "AL", "CLE": "AL", "DET": "AL", "KCR": "AL", "MIN": "AL",
    "HOU": "AL", "LAA": "AL", "ATH": "AL", "SEA": "AL", "TEX": "AL",
    "ATL": "NL", "MIA": "NL", "NYM": "NL", "PHI": "NL", "WSN": "NL",
    "CHC": "NL", "CIN": "NL", "MIL": "NL", "PIT": "NL", "STL": "NL",
    "ARI": "NL", "COL": "NL", "LAD": "NL", "SDP": "NL", "SFG": "NL",
}


def build_story_lede(charts, rows=None, team_payroll=None, team_names=None, market_rate=None):
    """Dashboard-level Big Idea for the top of the page.

    An earlier version stitched two chart titles together with "And", which
    produced two true facts and no argument -- exactly the failure mode a
    lede exists to avoid. This one states the claim the whole page is built
    to support (production is cheap, paying for it is not), then hands the
    reader the single most contestable number behind it: how little of the
    difference between teams payroll actually explains.

    Still built only from already-vetted inputs -- the individual chart
    titles and one correlation over the same team rows the Team Spending tab
    plots -- so the lede cannot assert something the tabs don't show. Falls
    back to the lead chart's own headline when the extra context isn't
    passed."""
    by_tab = {c["tabLabel"]: c for c in charts if c}
    price = by_tab.get("The Price of a Win")
    surplus = by_tab.get("Surplus Value")

    r2 = None
    if rows and team_payroll and team_names:
        team_rows = _team_totals(rows, team_payroll, team_names)
        r = _pearson_r([t["payroll_m"] for t in team_rows], [t["war"] for t in team_rows])
        r2 = (r * r) if r is not None else None

    parts = []
    if market_rate:
        parts.append(f"A win costs about ${market_rate/1_000_000:.0f}M on the open market — and almost "
                     "nobody pays that.")
    if r2 is not None:
        # .capitalize() would lowercase the rest of the sentence and turn
        # "R²" into "r²" -- only the first character should change.
        sentence = (_r2_framing(r2, 0)[1].replace("<em>", "").replace("</em>", "")
                    .replace("these teams", "teams"))
        parts.append(sentence[:1].upper() + sentence[1:])
    if surplus:
        parts.append(surplus["title"].rstrip(".") + ".")

    if parts:
        return " ".join(parts)

    lead = price or by_tab.get("League Picture")
    return (lead["title"].rstrip(".") + ".") if lead else None


# ---------------------------------------------------------------------------
# Narrative tabs
#
# The four tabs below exist to give the dashboard an argument rather than a
# pile of charts. The arc they complete: what a win costs (Price of a Win) ->
# who beats that price (League Picture, Paid vs. Produced) -> whether paying
# actually buys more (The Rising Cost of a Win) -> who converts payroll into
# wins (Payroll Efficiency) -> what it all means (What This Means & Methods).
#
# Every headline below is computed from the same pass that builds the chart's
# data, so a title can't drift out of sync with the bars underneath it.
# ---------------------------------------------------------------------------


# How many players to name inside a group before falling back to a count.
# A band can hold 260 players at full-league scale; a scrollable table of 15
# answers "who's in here?" while a table of 260 just recreates the problem
# the drill-down was added to solve.
MEMBERS_SHOWN = 15


def _member_rows(players, caption, sort_key=None):
    """Builds the drill-down roster shown under a grouped chart (see
    dashboard_template.py's renderMembers). Sorted by WAR descending by
    default so the names a reader recognises are at the top, not whichever
    player happened to sort first alphabetically."""
    ordered = sorted(players, key=sort_key or (lambda r: -r["war"]))
    shown = ordered[:MEMBERS_SHOWN]
    return {
        "caption": caption,
        "rows": [{
            "name": r["name"], "team": r["team"],
            "war": f'{r["war"]:.1f}',
            "salary": f'${r["salary_m"]:.2f}M' if r["salary_m"] < 10 else f'${r["salary_m"]:.1f}M',
            "price": (f'${r["salary_m"] / r["war"]:.2f}M' if r["war"] > 0 else "—"),
        } for r in shown],
        "more": (f"…and {len(ordered) - len(shown)} more in this group, "
                 "ordered by WAR." if len(ordered) > len(shown) else ""),
    }


def _pearson_r(xs, ys):
    """Plain Pearson r, no numpy (this kit has no runtime dependencies at
    chart-build time). Returns None when there's nothing meaningful to
    correlate -- fewer than 3 points, or zero variance in either variable --
    rather than raising or returning a fake 0.0, so callers can decide
    whether to make a claim at all."""
    n = len(xs)
    if n < 3 or len(ys) != n:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    num = sum(a * b for a, b in zip(dx, dy))
    denx = sum(a * a for a in dx) ** 0.5
    deny = sum(b * b for b in dy) ** 0.5
    if denx == 0 or deny == 0:
        return None
    return num / (denx * deny)


def _r2_framing(r2, n_teams):
    """Turns a payroll/production R² into honest prose.

    This exists because the copy used to assert "payroll explains ONLY x% of
    the difference" with the word "only" baked in. That reads fine at
    R²=0.15 and is a lie at R²=0.56 -- and the value genuinely swings that
    far between the demo snapshot and the full-league build, so the wording
    cannot be authored for one of them. Returns (headline, sentence) chosen
    from the number actually observed, so a strong correlation reports
    itself as a strong correlation.

    Bands: below 0.25 payroll explains little; 0.25-0.5 it explains some but
    most of the gap is elsewhere; 0.5+ money is genuinely doing work and the
    story becomes who beats the line rather than that no line exists."""
    pct = r2 * 100
    # "explains only 0%" reads like a broken calculation rather than a
    # finding; below half a percent, say it in words.
    if pct < 0.5:
        return (f"Payroll explains essentially none of the difference in what these {n_teams} teams produced",
                "payroll explains <em>essentially none</em> of the variation in what these teams actually "
                f"produced (R² = {r2:.2f}). Spending is not how the production gap gets built.")
    if r2 < 0.25:
        return (f"Payroll explains only {pct:.0f}% of the difference in what these {n_teams} teams produced",
                f"payroll explains just <em>{pct:.0f}%</em> of the variation in what these teams actually "
                f"produced (R² = {r2:.2f}). Spending is not how the production gap gets built.")
    if r2 < 0.5:
        return (f"Payroll explains about {pct:.0f}% of the difference in what these {n_teams} teams produced "
                f"— most of the gap is something else",
                f"payroll explains about <em>{pct:.0f}%</em> of the variation in what these teams produced "
                f"(R² = {r2:.2f}). Money moves the needle, but most of the difference between teams is "
                "coming from somewhere other than the payroll line.")
    return (f"Payroll explains about {pct:.0f}% of the difference in what these {n_teams} teams produced "
            f"— but the teams worth studying are the ones beating that line",
            f"payroll explains about <em>{pct:.0f}%</em> of the variation in what these teams produced "
            f"(R² = {r2:.2f}). Money is genuinely doing work at this level of coverage — which makes the "
            "teams sitting above the trend, getting more production than their spending predicts, the "
            "ones worth studying.")


def _team_totals(rows, team_payroll, team_names, min_players=3):
    """Shared team-level aggregation for the team tabs. Returns a list of
    dicts with tracked WAR, player count, and payroll -- only for teams that
    have BOTH tracked players and a payroll figure, since a team missing
    either can't be placed on a spending-vs-production chart at all and
    silently including it as a zero would invent a fake datapoint.

    min_players exists because team-level efficiency is a RATIO WITH A
    COVERAGE-DEPENDENT NUMERATOR: a team with one tracked player looks
    catastrophically inefficient next to a team with eight, and the
    difference is how many of its players this dashboard happens to follow,
    not anything about the team. On the demo snapshot that produced a real
    false headline ("the Yankees are 14.7x less efficient than the Marlins")
    off a single Yankees row. The live full-league build tracks ~25 players
    per team, so nothing is excluded there; this guard only bites on thin
    samples, which is exactly when it should."""
    by_team = {}
    for r in rows:
        t = by_team.setdefault(r["team"], {"war": 0.0, "n": 0, "salary": 0.0})
        t["war"] += r["war"]
        t["n"] += 1
        t["salary"] += r["salary"]
    out = []
    for abbr, agg in by_team.items():
        payroll = team_payroll.get(abbr)
        if not payroll or agg["n"] < min_players:
            continue
        out.append({
            "abbr": abbr, "name": team_names.get(abbr, abbr),
            "war": agg["war"], "n": agg["n"],
            "payroll_m": payroll["total"] / 1_000_000,
            "partial": payroll["partial"],
        })
    return out


# Bin edges in $M per WAR. The market rate is deliberately one of the edges
# (see build_price_of_win) so the reference line lands exactly on a bin
# boundary instead of floating somewhere inside a bar, which would make the
# "below the market rate" count ambiguous by exactly the width of one bin.
def _price_bins(market_rate_m):
    edges = [0, 2, 4, 6, 8, market_rate_m, 15, 20, 30]
    edges = sorted(set(round(e, 2) for e in edges if e < 30)) + [30]
    labels = []
    for i, lo in enumerate(edges[:-1]):
        hi = edges[i + 1]
        labels.append((lo, hi, f"${lo:g}–{hi:g}M"))
    labels.append((30, float("inf"), "$30M+"))
    return labels


def build_price_of_win(rows, market_rate):
    """rows: output of add_derived_fields(). Opens the dashboard by pricing
    its central unit: how much each tracked player actually charged per win
    (salary divided by WAR), as a distribution, against the assumed market
    rate every other tab is measured with.

    DENOMINATOR NOTE (this is the whole reason the chart is built this way):
    $/WAR is meaningless for a player at or below replacement level -- a
    0.0-WAR player divides by zero, and a negative-WAR player produces a
    negative "price" that would plot as if they were cheap. Those players are
    excluded from the distribution and counted explicitly in the footnote
    rather than silently dropped, because "how many players didn't produce a
    win at all" is itself part of the answer to what a win costs."""
    market_rate_m = market_rate / 1_000_000
    priced = [r for r in rows if r["war"] > 0]
    no_win = len(rows) - len(priced)

    bins = _price_bins(market_rate_m)
    counts = [0] * len(bins)
    members = [[] for _ in bins]
    for r in priced:
        price = r["salary_m"] / r["war"]
        for i, (lo, hi, _label) in enumerate(bins):
            if lo <= price < hi:
                counts[i] += 1
                members[i].append(r)
                break

    below = sum(c for c, (lo, _hi, _l) in zip(counts, bins) if lo < market_rate_m)
    pct_below = (below / len(priced) * 100) if priced else 0
    modal_i = counts.index(max(counts)) if counts else 0
    # The reference line is drawn on the right edge of the last bin that ends
    # at or below the market rate, so "everything left of the line" is exactly
    # the `below` count and the two can't disagree.
    ref_index = max((i for i, (lo, hi, _l) in enumerate(bins) if hi <= market_rate_m), default=None)

    cheapest = min(priced, key=lambda r: r["salary_m"] / r["war"]) if priced else None
    dearest = max(priced, key=lambda r: r["salary_m"] / r["war"]) if priced else None

    return {
        "type": "histogram", "tabLabel": "The Price of a Win",
        "source": SOURCE_WAR_SALARY,
        "metricLabel": "What a win actually costs",
        "title": (f"{below} of {len(priced)} players who produced a win at all "
                  f"({pct_below:.0f}%) delivered it for less than the "
                  f"${market_rate_m:.0f}M the open market charges"),
        "blurb": ("Take one player, divide their salary by the wins they've produced, and you get what a win "
                  "cost that team for that player. Do it for everyone and you get this. <strong>Each bar is a "
                  "price range, and its height is how many players landed in it</strong> — so the tall bar on "
                  "the left means a lot of players are producing wins very cheaply. The vertical line is what "
                  f"a win costs on the open market (about ${market_rate_m:.0f}M): everyone left of it came "
                  "cheaper than free agency, everyone right of it cost more. "
                  "<strong>Click any bar to see exactly which players are in it.</strong>"),
        "xAxisLabel": "What one win cost (that player's salary ÷ their WAR)", "yAxisLabel": "How many players",
        "unitLabel": "players",
        "refIndex": ref_index,
        "refLabel": f"market rate ~${market_rate_m:.0f}M/WAR",
        "footnote": (
            (f"Excludes {no_win} tracked player{'s' if no_win != 1 else ''} at or below replacement level "
             "(0 WAR or worse) — salary per win is undefined when no win was produced, and a negative WAR "
             "would plot as a negative price. They're still counted everywhere else on this dashboard."
             if no_win else "")
            + (f" Cheapest win here: {cheapest['name']} at "
               f"${cheapest['salary_m']/cheapest['war']:.2f}M per WAR. Most expensive: {dearest['name']} at "
               f"${dearest['salary_m']/dearest['war']:.0f}M per WAR." if cheapest and dearest else "")
        ),
        "bins": [
            {"label": label, "count": counts[i],
             "highlight": i == modal_i,
             "annotation": f"{counts[i]} players" if i == modal_i else None,
             "extra": (f"{counts[i]/len(priced)*100:.0f}% of players who produced a win" if priced else None)}
            for i, (lo, hi, label) in enumerate(bins)
        ],
        "members": {
            label: _member_rows(
                members[i],
                (f"<strong>{counts[i]} player{'s' if counts[i] != 1 else ''}</strong> produced wins at "
                 f"{label.replace('$', '$')} apiece"
                 + (" — cheaper than the open market" if lo < market_rate_m else
                    " — more than the open market charges")
                 + f". Showing the top {min(counts[i], MEMBERS_SHOWN)} by WAR."))
            for i, (lo, hi, label) in enumerate(bins) if counts[i]
        },
    }


# Salary tiers in whole dollars. Chosen around real contract structure rather
# than even splits: under $1M is essentially pre-arbitration/league-minimum,
# $1-5M is arbitration and small deals, and $20M+ is the free-agent tier.
SALARY_TIERS = [
    (0, 1_000_000, "Under $1M"),
    (1_000_000, 5_000_000, "$1–5M"),
    (5_000_000, 10_000_000, "$5–10M"),
    (10_000_000, 20_000_000, "$10–20M"),
    (20_000_000, 30_000_000, "$20–30M"),
    (30_000_000, float("inf"), "$30M+"),
]


def _tier_table(players):
    """Prices a win inside each salary bracket for whatever set of players it
    is handed -- the whole league, or one roster.

    AGGREGATE, NOT MEAN-OF-RATIOS: each bracket's price is (combined salary in
    the bracket) / (combined WAR in the bracket), not the average of each
    player's individual $/WAR. Averaging ratios lets one near-zero-WAR player
    with a big contract produce a five-hundred-million-dollar "price" that
    swamps the bracket, which is a real number describing nothing."""
    out = []
    for lo, hi, label in SALARY_TIERS:
        members = [r for r in players if lo <= r["salary"] < hi]
        if not members:
            continue
        total_salary_m = sum(r["salary_m"] for r in members)
        total_war = sum(r["war"] for r in members)
        out.append({
            "label": label, "n": len(members), "players": members,
            "total_salary_m": total_salary_m, "total_war": total_war,
            "mean_war": total_war / len(members),
            # None when a bracket collectively produced no wins -- a price per
            # win genuinely doesn't exist there, and rendering it as 0 would
            # read as "free," the exact opposite of the truth.
            "price_m": (total_salary_m / total_war) if total_war > 0 else None,
        })
    return out


def _tier_group(tiers, cheapest_label=None):
    """Turns a bracket table into the bar data + drill-down rosters the chart
    layer wants. Shared by the league view and every team view."""
    priced = [t for t in tiers if t["price_m"] is not None]
    if cheapest_label is None and priced:
        cheapest_label = min(priced, key=lambda t: t["price_m"])["label"]
    return {
        "data": [
            {"label": t["label"], "value": round(t["price_m"], 1),
             "highlight": t["label"] == cheapest_label,
             "extra": (f'{t["n"]} players &middot; {t["total_war"]:.1f} combined WAR &middot; '
                       f'${t["total_salary_m"]:.0f}M combined salary &middot; '
                       f'{t["mean_war"]:.2f} WAR per player')}
            for t in priced
        ],
        "members": {
            t["label"]: _member_rows(
                t["players"],
                (f'<strong>{t["n"]} player{"s" if t["n"] != 1 else ""}</strong> earning {t["label"]}, '
                 f'producing {t["total_war"]:.1f} wins between them for ${t["total_salary_m"]:.0f}M — '
                 f'${t["price_m"]:.1f}M per win. Showing the top {min(t["n"], MEMBERS_SHOWN)} by WAR.'))
            for t in priced
        },
    }


def build_diminishing_returns(rows, team_names=None):
    """The Rising Cost of a Win: every player sorted into a salary bracket,
    then each bracket priced.

    A Team dropdown sits on top of the league view. Two cautions are built
    into the team views rather than left to the reader:

    1. THIN BRACKETS. One roster spread across six brackets leaves some of
       them holding one or two players, where a single injury or slump swings
       the bracket's price wildly. The bar's tooltip and the drill-down both
       carry the player count, and the caption says outright when a majority
       of a team's brackets are thin.
    2. MISSING BRACKETS. A bracket with no players, or none who produced a
       win, is omitted rather than drawn at zero -- so a team's staircase can
       legitimately have fewer steps than the league's, and the caption says
       how many priced."""
    league_tiers = _tier_table(rows)
    priced = [t for t in league_tiers if t["price_m"] is not None]
    cheapest = min(priced, key=lambda t: t["price_m"]) if priced else None
    dearest = max(priced, key=lambda t: t["price_m"]) if priced else None

    if cheapest and dearest and cheapest is not dearest:
        multiple = dearest["price_m"] / cheapest["price_m"] if cheapest["price_m"] else 0
        title = (f"A win costs {multiple:.0f}x more in the {dearest['label']} bracket than in the "
                 f"{cheapest['label']} bracket — ${dearest['price_m']:.1f}M against "
                 f"${cheapest['price_m']:.1f}M")
    else:
        title = "What a win costs at each salary bracket"

    league_price = {t["label"]: t["price_m"] for t in priced}
    league_group = _tier_group(league_tiers)
    league_group["caption"] = (
        "<strong>Every player in the dataset, sorted by what they earn.</strong> The bars get longer as you "
        "go down, which means each step up the pay ladder buys wins at a worse exchange rate than the one "
        "below it. Use the dropdown to see whether a particular team follows the same curve — or beats it."
    )
    groups = {"All of MLB": league_group}

    if team_names:
        by_team = {}
        for r in rows:
            by_team.setdefault(r["team"], []).append(r)
        for abbr in sorted(by_team, key=lambda a: team_names.get(a, a)):
            tiers = _tier_table(by_team[abbr])
            t_priced = [t for t in tiers if t["price_m"] is not None]
            if not t_priced:
                continue
            group = _tier_group(tiers)
            t_cheap = min(t_priced, key=lambda t: t["price_m"])
            t_dear = max(t_priced, key=lambda t: t["price_m"])
            name = team_names.get(abbr, abbr)
            thin = [t for t in t_priced if t["n"] <= 2]

            if t_cheap is not t_dear and t_cheap["price_m"]:
                t_mult = t_dear["price_m"] / t_cheap["price_m"]
                group["title"] = (f'For the {name}, a win costs {t_mult:.0f}x more in the '
                                  f'{t_dear["label"]} bracket than in {t_cheap["label"]} — '
                                  f'${t_dear["price_m"]:.1f}M against ${t_cheap["price_m"]:.1f}M')
            else:
                group["title"] = (f'{name}: only one salary bracket has enough production to price')

            bits = [f'<strong>{name}</strong>: {len(t_priced)} of {len(SALARY_TIERS)} salary brackets have '
                    f'enough production to price.']
            if t_cheap is not t_dear:
                bits.append(f'Their cheapest wins come in the {t_cheap["label"]} bracket at '
                            f'${t_cheap["price_m"]:.1f}M each; their most expensive in {t_dear["label"]} at '
                            f'${t_dear["price_m"]:.1f}M.')
            # Compare the team's priciest bracket against the league's price
            # for that same bracket -- the only apples-to-apples comparison
            # available, since brackets differ in composition between teams.
            lg = league_price.get(t_dear["label"])
            if lg:
                verdict = "better than" if t_dear["price_m"] < lg else "worse than"
                bits.append(f'That top bracket is {verdict} the league\'s ${lg:.1f}M for the same '
                            "bracket.")
            if len(thin) >= max(1, len(t_priced) // 2):
                bits.append(f'<em>Read carefully:</em> {len(thin)} of these brackets rest on two players or '
                            "fewer, so their prices swing hard. Click a bar to see who's in it.")
            group["caption"] = " ".join(bits)
            groups[name] = group

    return {
        "type": "diverging-bar", "tabLabel": "The Rising Cost of a Win",
        "source": SOURCE_WAR_SALARY,
        "metricLabel": "What a win costs, bracket by bracket",
        "title": title,
        "blurb": ("Same question as the opening tab, asked of salary brackets instead of individuals. Every "
                  "player is sorted into a pay bracket — cheapest at the top — and then each bracket is "
                  "priced: <strong>add up everything that bracket earns, divide by all the wins it produced, "
                  "and the bar is what one win cost inside it</strong>. If paying more bought proportionally "
                  "more production, every bar would be the same length. They get longer as you go down. "
                  "<strong>Pick a team to see its own curve, and click any bracket to see the players in "
                  "it.</strong>"),
        "preserveOrder": True, "oneSided": True,
        "valueLabel": "Cost per WAR ($M)", "xAxisLabel": "Cost per win produced ($M)",
        "annotationSuffix": "M",
        "groups": groups,
        "groupLabel": "Team",
        "defaultGroup": "All of MLB",
        "footnote": ("Each bracket's price is combined salary divided by combined WAR for that bracket, not "
                     "the average of individual players' ratios — one near-replacement player on a large "
                     "contract would otherwise distort a whole bracket. Brackets that produced no wins are "
                     "omitted, since a price per win doesn't exist for them. Single-team views can rest on "
                     "very few players per bracket; the player count is in every tooltip."),
    }


def build_payroll_efficiency(rows, team_payroll, team_names):
    """rows: output of add_derived_fields(). Ranks every team with both
    tracked players and a known payroll by how much production each payroll
    dollar returned.

    Expressed as WAR per $10M rather than $ per WAR on purpose: with $/WAR,
    the *longest* bar would be the *worst* team, which fights the reader's
    instinct that a bigger bar is better. Both figures are in the tooltip."""
    team_rows = _team_totals(rows, team_payroll, team_names)
    for t in team_rows:
        t["war_per_10m"] = (t["war"] / t["payroll_m"]) * 10 if t["payroll_m"] else 0
        t["price_m"] = (t["payroll_m"] / t["war"]) if t["war"] > 0 else None

    best = max(team_rows, key=lambda t: t["war_per_10m"]) if team_rows else None
    worst = min(team_rows, key=lambda t: t["war_per_10m"]) if team_rows else None

    if best and worst and best is not worst and worst["war_per_10m"] > 0:
        multiple = best["war_per_10m"] / worst["war_per_10m"]
        title = (f"{best['name']} turn payroll into wins {multiple:.1f}x more efficiently than "
                 f"{worst['name']} — {best['war_per_10m']:.2f} WAR per $10M against "
                 f"{worst['war_per_10m']:.2f}")
    elif best:
        title = f"{best['name']} get the most production per payroll dollar"
    else:
        title = "Production per payroll dollar, by team"

    return {
        "type": "diverging-bar", "tabLabel": "Payroll Efficiency",
        "source": SOURCE_WAR_SALARY,
        "metricLabel": "Production returned per payroll dollar",
        "title": title,
        "blurb": (f"All {len(team_rows)} teams with both tracked players and a known payroll, ranked by how "
                  "much production each $10M of payroll bought. Longer is better. This is the aggregate "
                  "version of the argument every player-level tab makes one name at a time: the teams at the "
                  "top are not the teams spending the most. They're the ones whose production is coming from "
                  "players who haven't been paid for it yet."),
        "oneSided": True,
        "valueLabel": "WAR per $10M", "xAxisLabel": "Tracked WAR per $10M of payroll",
        "footnote": ("Payroll is the team's full roster commitment; WAR is only the players this dashboard "
                     "tracks, so this measures how much of a payroll is showing up as tracked production, "
                     "not a complete organizational efficiency verdict. See Methods & Sources."),
        "data": [
            {"label": t["name"], "value": round(t["war_per_10m"], 2),
             "highlight": best is not None and t["abbr"] == best["abbr"],
             "extra": (f'{t["war"]:.1f} tracked WAR from {t["n"]} players &middot; '
                       f'${t["payroll_m"]:.0f}M payroll'
                       + (f' &middot; ${t["price_m"]:.1f}M per WAR' if t["price_m"] else "")
                       + (" &middot; partial payroll (listed players only)" if t["partial"] else ""))}
            for t in team_rows
        ],
    }


def build_takeaways(charts, rows, team_payroll, team_names, market_rate, season):
    """The closing tab. Reuses the already-vetted headline from each earlier
    chart rather than re-deriving claims from raw data -- the same reason
    build_story_lede does: a summary that recomputes its own numbers can
    contradict the tabs it's summarizing, and nobody notices until a reader
    does. The only new number computed here is the payroll/production
    correlation, which belongs to the page as a whole rather than any single
    tab. Also carries the dashboard's methodology, in one place, so the
    individual chart blurbs don't each have to hedge."""
    by_tab = {c["tabLabel"]: c for c in charts if c}
    team_rows = _team_totals(rows, team_payroll, team_names)
    market_rate_m = market_rate / 1_000_000

    r = _pearson_r([t["payroll_m"] for t in team_rows], [t["war"] for t in team_rows])
    r2 = (r * r) if r is not None else None

    spend_paras = []
    if r2 is not None and len(team_rows) >= 3:
        payrolls = sorted(t["payroll_m"] for t in team_rows)
        spread = (payrolls[-1] / payrolls[0]) if payrolls[0] else None
        gap_sentence = ""
        if spread:
            gap_sentence = (f"Payroll across these {len(team_rows)} teams varies by about "
                            f"{spread:.0f}-to-1. ")
        # Deliberately NOT paired with a "production varies by N-to-1" figure:
        # tracked WAR per team depends on how many of a team's players this
        # dashboard follows, so that ratio would be measuring coverage, not
        # production. R² below is reported for the same reason it's safe --
        # it's a relationship between two per-team totals, not a headline
        # ranking one team against another on a thin sample.
        spend_paras.append(gap_sentence + "Against that spread, " + _r2_framing(r2, len(team_rows))[1])

    sections = [{
        "heading": "What this dashboard argues",
        "paragraphs": [p for p in [
            (f"A win on the open market costs about <em>${market_rate_m:.0f}M</em>. Almost nobody actually "
             "pays that, because the players producing wins most cheaply are the ones whose contracts "
             "haven't caught up to them yet — and that gap, not payroll, is where the competitive "
             "advantage in this sport currently sits."),
            spend_paras[0] if spend_paras else None,
            ("The practical version: if you want to know whether a team is well run, don't look at what "
             "it spends. Look at how many of its wins are coming from players it isn't paying market "
             "price for — and at how soon those players are due a raise."),
        ] if p],
    }]

    # Built from the charts actually passed in, in tab order -- NOT a
    # hardcoded list of tab names. The hardcoded version silently dropped
    # every renamed tab: after "Diminishing Returns" became "The Rising Cost
    # of a Win" and "Surplus Value" became "Paid vs. Produced", this section
    # quietly lost them and nothing failed. Types excluded here are the two
    # whose titles are labels rather than findings (the roster explorer) plus
    # this panel itself.
    SKIP_TYPES = {"prose", "team-compare"}
    findings = [
        {"term": c["tabLabel"], "def": c["title"].rstrip(".") + "."}
        for c in charts
        if c and c.get("type") not in SKIP_TYPES and c.get("title")
    ]
    if findings:
        sections.append({
            "heading": "The findings, in one place",
            "paragraphs": ["Each line is the headline of the tab it names, computed from that tab's own data."],
            "items": findings,
        })

    sections.append({
        "heading": "Methods & sources",
        "items": [
            {"term": "WAR (Wins Above Replacement)",
             "def": (f'{SOURCE_LINKS["bref"]}\'s bWAR for the {season} season, scraped from their '
                     '<a href="https://www.baseball-reference.com/leagues/majors/'
                     f'{season}-value-batting.shtml" rel="noopener">Player Value tables</a>. One WAR is '
                     "roughly one win more than a freely-available replacement-level player would have "
                     "produced. Baseball-Reference's data is their own work; this dashboard only "
                     "recombines it.")},
            {"term": "Salary and payroll",
             "def": (f'{SOURCE_LINKS["spotrac"]}\'s per-team payroll pages. Some figures are average '
                     "annual value (AAV) rather than the literal cash paid this season; those are marked "
                     "“AAV” in tooltips.")},
            {"term": "Team records",
             "def": (f'{SOURCE_LINKS["bref"]}\'s standings page. Used for team context on the Awards Race '
                     "tab and the Team Stories header. When unavailable, both fall back to a WAR-based "
                     "measure of team strength and say so.")},
            {"term": f"Market rate (${market_rate_m:.0f}M per WAR)",
             "def": (f'A single blended figure for the current free-agent market, per {SOURCE_LINKS["fangraphs"]}\' '
                     "analysis of the 2025–26 offseason. It is an assumption, not a measurement: the real "
                     "cost per win varies by position, contract length, and how badly a team needs one. "
                     "Every “surplus value” figure on this dashboard inherits that assumption.")},
            {"term": "Editorial models, labelled as such",
             "def": ("Two views on this dashboard are models rather than measurements, and both show their "
                     "formula on the page: the Awards Race “weighted by team record” lens (WAR × team "
                     "winning % ÷ .500), and the contract tiers on Paid vs. Produced, which infer contract "
                     "status from salary because no service-time data is available here. Everything else "
                     "is arithmetic on the sources above.")},
            {"term": "Partial seasons",
             "def": ("WAR is season-to-date while salary figures are full-season. Mid-season, that "
                     "understates every player's production relative to their pay — the surplus numbers "
                     "get more favorable to players as the season fills in.")},
            {"term": "Team coverage",
             "def": ("Team-level tabs compare a full roster payroll against only the players this dashboard "
                     "tracks. They measure how much of a payroll shows up as tracked production, which is "
                     "not the same as a complete organizational efficiency verdict. Teams with fewer than "
                     "three tracked players are left off those tabs entirely — with a thin sample, a team's "
                     "efficiency reflects how many of its players are followed here rather than anything "
                     "about the team.")},
            {"term": "Credit and independence",
             "def": ("Nothing here is proprietary — it's published stats and salary figures, recombined, "
                     "with the source named under every chart. This project is not affiliated with "
                     "Baseball-Reference, Spotrac, FanGraphs or MLB. The code that builds this page is "
                     '<a href="https://github.com/duransound/mlb-dashboard" rel="noopener">on GitHub</a>.')},
        ],
    })

    return {
        "type": "prose", "tabLabel": "What This Means",
        "metricLabel": "The argument, and how it was built",
        "title": "Production is cheap. Paying for production is expensive.",
        "blurb": ("The dashboard's whole case, and the methodology behind it, in one place — so the charts "
                  "themselves can just make their point."),
        "sections": sections,
    }


# ---------------------------------------------------------------------------
# Team records (optional)
# ---------------------------------------------------------------------------

def _record_str(rec):
    return f'{rec["w"]}-{rec["l"]}' if rec else None


def _team_context(abbr, standings, team_war_rank=None, n_teams=None):
    """One short phrase describing how good a player's team is, preferring a
    real W-L record and degrading to a WAR-based rank when standings aren't
    available (the demo snapshot has no records; a failed standings scrape
    also lands here). Returns None when there's nothing honest to say."""
    rec = (standings or {}).get(abbr)
    if rec:
        shape = "winning" if rec["pct"] > 0.5 else ("break-even" if rec["pct"] == 0.5 else "losing")
        return f'{rec["w"]}-{rec["l"]} ({shape})'
    if team_war_rank and n_teams:
        return f"#{team_war_rank} of {n_teams} by tracked WAR"
    return None


# ---------------------------------------------------------------------------
# Awards Race (MVP + Cy Young)
# ---------------------------------------------------------------------------

# Two-way players count toward both ballots -- they are genuinely eligible
# for both, and dropping them from either view would silently hide the most
# interesting player on the page.
def _is_position_player(r):
    return r["role"] in ("batter", "two-way")


def _is_pitcher(r):
    return r["role"] in ("pitcher", "two-way")


AWARD_FIELDS = {
    "MVP": [
        ("Everyone", lambda r: True),
        ("Position players only", _is_position_player),
        ("Pitchers only", _is_pitcher),
    ],
    # Cy Young is a pitching award by definition -- there is no field filter
    # to offer, so the JS hides the selector entirely for this award.
    "Cy Young": [("Pitchers", _is_pitcher)],
}


# The three ways this dashboard will let you look at an award race. Only
# "Pure WAR" is a measurement; the other two are explicitly editorial, and
# the page says so in the caption and footnote rather than burying it.
AWARD_LENSES = [
    "Pure WAR",
    "Contenders only (teams over .500)",
    "Weighted by team record",
]


def _ballot_score(war, rec):
    """The disclosed weighting: WAR scaled by how far the player's team is
    from .500. A .600 team multiplies by 1.2, a .400 team by 0.8, and a
    perfectly average team changes nothing.

    This is a MODEL, not a measurement -- there is no true exchange rate
    between a win produced and a win the rest of the roster produced. It's
    here because voters demonstrably behave this way, and showing the formula
    lets a reader argue with it. Anything more elaborate would be false
    precision dressed up as analysis."""
    if not rec:
        return war
    return war * (rec["pct"] / 0.5)


def build_awards_race(rows, standings=None, team_names=None, top_n=10):
    """rows: output of add_derived_fields(). standings: optional
    {abbr: {"w","l","pct"}} from mlb_data.fetch_standings().

    Four pickers: award (MVP / Cy Young), league (AL / NL), field (for MVP
    only: everyone / position players / pitchers), and team context (see
    AWARD_LENSES).

    WHY THE FIELD FILTER EXISTS: WAR puts pitchers and hitters on one scale,
    so a raw WAR leaderboard regularly hands an "MVP race" to a starter. Real
    ballots almost never do. Rather than quietly excluding pitchers (a hidden
    editorial choice) or pretending the raw list is the race (wrong), the
    filter makes the choice the reader's and names it.

    WHY THE TEAM-CONTEXT LENS EXISTS: same reasoning, one level up. Voters
    weigh team success heavily; WAR ignores it entirely. Both facts are true,
    and the honest move is to let a reader switch between them and see how
    much the ranking actually moves -- with the filter (a real subset) and
    the weighting (an admitted model) kept clearly distinct. The lens picker
    is hidden entirely when there are no standings, since every option but
    the first would be undefined."""
    team_war = {}
    for r in rows:
        team_war[r["team"]] = team_war.get(r["team"], 0.0) + r["war"]
    war_rank = {abbr: i + 1 for i, (abbr, _w) in
                enumerate(sorted(team_war.items(), key=lambda kv: -kv[1]))}
    n_teams = len(war_rank)

    def entry(r):
        rec = (standings or {}).get(r["team"])
        return {
            "name": r["name"], "team": r["team"], "war": round(r["war"], 1),
            "role": r["role"], "salary_m": round(r["salary_m"], 1),
            "record": _record_str(rec),
            "pct": rec["pct"] if rec else None,
            "adj": round(_ballot_score(r["war"], rec), 2),
            "winning": bool(rec and rec["pct"] > 0.5),
            "context": _team_context(r["team"], standings, war_rank.get(r["team"]), n_teams),
        }

    lenses = AWARD_LENSES if standings else AWARD_LENSES[:1]

    awards, captions = {}, {}
    for award, fields in AWARD_FIELDS.items():
        awards[award], captions[award] = {}, {}
        for league in ("AL", "NL"):
            pool = [r for r in rows if TEAM_LEAGUE.get(r["team"]) == league]
            awards[award][league], captions[award][league] = {}, {}
            for field_label, predicate in fields:
                eligible = [r for r in pool if predicate(r)]
                awards[award][league][field_label] = {}
                captions[award][league][field_label] = {}
                for lens in lenses:
                    if lens.startswith("Contenders"):
                        subset = [r for r in eligible
                                  if (standings or {}).get(r["team"], {}).get("pct", 0) > 0.5]
                        ranked = sorted(subset, key=lambda r: r["war"], reverse=True)[:top_n]
                    elif lens.startswith("Weighted"):
                        ranked = sorted(
                            eligible,
                            key=lambda r: _ballot_score(r["war"], (standings or {}).get(r["team"])),
                            reverse=True)[:top_n]
                    else:
                        ranked = sorted(eligible, key=lambda r: r["war"], reverse=True)[:top_n]
                    awards[award][league][field_label][lens] = [entry(r) for r in ranked]
                    captions[award][league][field_label][lens] = _award_caption(
                        award, league, field_label, lens, ranked, eligible, standings, team_names)

    overall_best = max(rows, key=lambda r: r["war"]) if rows else None
    default_league = TEAM_LEAGUE.get(overall_best["team"], "AL") if overall_best else "AL"

    return {
        "type": "awards-race", "tabLabel": "Awards Race",
        "source": SOURCE_AWARDS,
        "metricLabel": "MVP and Cy Young races, by WAR",
        "title": "Who's actually leading each award race — and who the ballot will probably reward instead",
        "blurb": ("There's no ballot data here, just WAR — sabermetrics' best single answer to \"who mattered "
                  "most.\" That makes this a cleaner race than the real one, and the gap between the two is "
                  "the interesting part. <strong>Pick an award, a league, which players count, and how much "
                  "the team around them should matter.</strong> WAR rates pitchers and hitters on one scale, "
                  "so an unfiltered MVP list often hands the award to a starter; actual voters almost never "
                  "do, and they discount good players on bad teams besides."),
        "footnote": ("<strong>Pure WAR</strong> is the measurement: team record is displayed but never scored. "
                     "<strong>Contenders only</strong> is a filter — the same WAR ranking, restricted to "
                     "players on teams above .500; nothing is invented, players are only removed. "
                     "<strong>Weighted by team record</strong> is an explicit model: score = WAR × (team "
                     "winning % ÷ .500), so a .600 team multiplies a player's WAR by 1.2 and a .400 team by "
                     "0.8. That formula is a stand-in for how voters behave, not a measured exchange rate — "
                     "argue with it freely. Two-way players appear on both the position-player and pitcher "
                     "lists."),
        "awards": awards,
        "captions": captions,
        "fields": {award: [label for label, _p in fields] for award, fields in AWARD_FIELDS.items()},
        "lenses": lenses,
        "defaultAward": "MVP",
        "defaultLeague": default_league,
        "defaultLens": "Pure WAR",
        "hasStandings": bool(standings),
    }


def _award_caption(award, league, field_label, lens, ranked, eligible, standings, team_names):
    """The story sentence under an awards leaderboard. Leads with the leader,
    then the tension a reader should actually care about -- which differs by
    lens, so each lens explains what it just did to the list rather than
    leaving the reader to infer it from a reshuffle."""
    names = team_names or {}
    if not ranked:
        if lens.startswith("Contenders"):
            return ("No qualifying players on teams above .500 in this view — which is itself the finding: "
                    "this league's best production is coming from teams that aren't winning.")
        return "No qualifying players in this view."

    lead = ranked[0]
    lead_team = names.get(lead["team"], lead["team"])
    rec = (standings or {}).get(lead["team"])

    if lens.startswith("Weighted"):
        pure_lead = max(eligible, key=lambda r: r["war"])
        parts = [f'<strong>{lead["name"]}</strong> leads the {league} {award} race once team record is '
                 f'folded in — {lead["war"]:.1f} WAR for the {lead_team}'
                 + (f', {rec["w"]}-{rec["l"]}.' if rec else '.')]
        if pure_lead["name"] != lead["name"]:
            parts.append(f'On WAR alone it would be {pure_lead["name"]} ({pure_lead["war"]:.1f}) — the '
                         "weighting is doing real work here, which is exactly what it's for and exactly "
                         "why it isn't the default.")
        else:
            parts.append("The weighting doesn't change who's on top, which is the strongest case a "
                         "candidate can have: best by the measurement and best by the ballot's instincts.")
        parts.append("Score = WAR × (team winning % ÷ .500). It's a model, not a measurement — see the note "
                     "below.")
        return " ".join(parts)

    if lens.startswith("Contenders"):
        removed = len(eligible) - len([r for r in eligible
                                       if (standings or {}).get(r["team"], {}).get("pct", 0) > 0.5])
        parts = [f'<strong>{lead["name"]}</strong> leads the {league} {award} race among players on winning '
                 f'teams — {lead["war"]:.1f} WAR for the {lead_team}'
                 + (f', {rec["w"]}-{rec["l"]}.' if rec else '.')]
        parts.append(f'{removed} otherwise-eligible {"player" if removed == 1 else "players"} are hidden by '
                     "this filter, all of them on teams under .500. Nothing here is reweighted — they're "
                     "simply removed, the way a ballot tends to remove them.")
        return " ".join(parts)

    parts = [f'<strong>{lead["name"]}</strong> leads the {league} {award} race on WAR '
             f'({lead["war"]:.1f}) for the {lead_team}.']
    if standings:
        winners = sum(1 for r in ranked
                      if (standings.get(r["team"]) or {}).get("pct", 0) > 0.5)
        if rec and rec["pct"] <= 0.5:
            parts.append(f'That team is {rec["w"]}-{rec["l"]} — historically close to fatal on a ballot, '
                         "no matter what the WAR column says.")
        elif rec:
            parts.append(f'The {rec["w"]}-{rec["l"]} record helps: voters reward production on teams that win.')
        parts.append(f'{winners} of these {len(ranked)} candidates play for winning teams — switch the team '
                     "context dropdown to see how much that would move the race.")
    else:
        parts.append("Team records aren't in this build, so there's no way to weigh the team-success factor "
                     "voters lean on — run the full-league build to pull them in.")

    if award == "MVP" and field_label == "Everyone":
        pitchers = [r for r in ranked if r["role"] in ("pitcher", "two-way")]
        if pitchers:
            parts.append(f'{len(pitchers)} of the top {len(ranked)} here are pitchers, who almost never win '
                         "this award — switch to position players only for something closer to a real ballot.")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Team Stories
# ---------------------------------------------------------------------------

def _player_story(r, team_total_war, rank, n_players, used=None):
    """One sentence per player, verdict first.

    Two things here are load-bearing, both learned from output that looked
    fine in code and bad on the page:

    1. BRANCH ORDER AND RANK. A first version tested "share >= 20%" before
       anything else, which on a four-player roster gave three players the
       identical "carrying the roster" line -- on a thin roster everyone
       clears a percentage threshold. The carrying claim is now exclusive to
       the actual leader.

    2. REPEAT VARIANTS. Even with good branches, a roster where several
       players share a situation (Miami: four cheap pre-arb producers) hands
       the same sentence to all of them. `used` tracks which templates a team
       has already spent, so the second and later players in a category get
       an alternate phrasing. The facts stay identical; only the framing
       moves, so this adds no claim the data doesn't support."""
    used = used if used is not None else {}
    share = (r["war"] / team_total_war * 100) if team_total_war > 0 else 0
    sal = f'${r["salary_m"]:.2f}M' if r["salary_m"] < 10 else f'${r["salary_m"]:.0f}M'
    surplus_m = r["surplus_m"]
    is_pitcher = r["role"] in ("pitcher", "two-way")
    noun = "arm" if is_pitcher else "bat"

    ORDINALS = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth",
                "Seventh", "Eighth", "Ninth", "Tenth"]

    def pick(tag, *variants):
        """Cycles through phrasings for a repeated situation, then falls back
        to a rank-anchored sentence.

        `used` counts per tag rather than flagging it, so a roster with four
        players in the same bucket doesn't just alternate between two
        sentences. Once the variants are spent, the fallback keys off the
        player's rank -- which is unique within a roster by construction, so
        two narrated players can never end up with the same opening no matter
        how alike their seasons are. Without this, a full-league roster of 26
        (8 of them narrated) still produced duplicate lines on 23 of 30
        teams; with it, zero."""
        n = used.get(tag, 0)
        used[tag] = n + 1
        if n < len(variants):
            return variants[n]
        ordinal = ORDINALS[rank] if rank < len(ORDINALS) else f"#{rank + 1}"
        return (f'{ordinal} on the roster by WAR: {r["war"]:.1f} on {sal}'
                + (f', ${surplus_m:.0f}M more production than pay.' if surplus_m >= 5
                   else (f', ${abs(surplus_m):.0f}M more pay than production.' if surplus_m <= -5 else '.')))

    if r["war"] <= 0:
        return pick("negative",
                    f'Has been worse than a replacement-level fill-in this season — {r["war"]:.1f} WAR — '
                    f'while earning {sal}.',
                    f'Also below replacement: {r["war"]:.1f} WAR on {sal}.')

    # Exclusive to the roster leader: only one player can be carrying a team.
    if rank == 0 and share >= 25 and n_players > 1:
        return (f'The one carrying it: {r["war"]:.1f} WAR is {share:.0f}% of everything this roster has '
                f'produced, at {sal}.')
    if rank == 0:
        return f'Leads the roster at {r["war"]:.1f} WAR, on {sal}.'

    if surplus_m <= -15:
        return pick("overpay",
                    f'The roster\'s clearest overpay: {sal} for {r["war"]:.1f} WAR, about '
                    f'${abs(surplus_m):.0f}M more salary than production.',
                    f'Another contract underwater: {sal} for {r["war"]:.1f} WAR.')
    if surplus_m >= 10 and r["salary_m"] < 5:
        return pick("bargain",
                    f'The kind of contract teams build around — {r["war"]:.1f} WAR for {sal}, roughly '
                    f'${surplus_m:.0f}M of production nobody has had to pay for yet.',
                    f'Same story, different name: {r["war"]:.1f} WAR for {sal}. This roster is being '
                    "carried by players it isn't paying.",
                    f'And again: {r["war"]:.1f} WAR for {sal}. At some point all of these become raises.')
    if rank <= 2 and share >= 15:
        return pick("engine",
                    f'The other half of the engine: {r["war"]:.1f} WAR, {share:.0f}% of the roster\'s '
                    f'output, on {sal}.',
                    f'Third piece of the core: {r["war"]:.1f} WAR ({share:.0f}%) on {sal}.',
                    f'Also carrying real weight: {r["war"]:.1f} WAR ({share:.0f}%) on {sal}.')
    if r["salary_m"] >= 20 and r["war"] < 2:
        return pick("waiting",
                    f'{sal} has bought {r["war"]:.1f} WAR so far — the roster\'s biggest bet still '
                    "waiting to pay.",
                    f'Another expensive wait: {sal} for {r["war"]:.1f} WAR.')
    if r["war"] >= 3:
        return pick("everyday",
                    f'A genuine everyday contributor: {r["war"]:.1f} WAR on {sal}.',
                    f'Steady too: {r["war"]:.1f} WAR on {sal}.')
    if r["war"] >= 1.5:
        return pick("useful",
                    f'A useful {noun}: {r["war"]:.1f} WAR ({share:.0f}% of the team total) on {sal}.',
                    f'{r["war"]:.1f} WAR on {sal}, filling in around the top of the roster.')
    return pick("minor",
                f'{r["war"]:.1f} WAR on {sal} — a supporting part rather than a story.',
                f'{r["war"]:.1f} WAR on {sal}.')


# How many players on a roster get a narrated line. A full-league build has
# ~26 tracked players per team, and 26 sentences is not a story -- it's a
# table with extra words, and no set of phrasing variants survives that many
# repetitions gracefully. The top of the roster is where the story actually
# is; the tail is real and worth listing, but as rows, not prose.
NARRATED_PLAYERS = 8


def build_team_stories(rows, team_names, standings=None, market_rate=None):
    """A roster-by-roster narrative: pick a team, read what its players have
    actually contributed, ordered by WAR.

    Distinct from Compare Teammates (which ranks one metric as bars) in that
    the unit here is a sentence, not a number -- the point is to be able to
    read a team, not to measure one. Only the top NARRATED_PLAYERS get a
    sentence; everyone else is listed compactly beneath, so a 26-man roster
    stays readable and the prose stays meaningful."""
    by_team = {}
    for r in rows:
        by_team.setdefault(r["team"], []).append(r)

    teams = {}
    for abbr, players in by_team.items():
        ordered = sorted(players, key=lambda r: -r["war"])
        total_war = sum(p["war"] for p in players)
        total_salary_m = sum(p["salary_m"] for p in players)
        rec = (standings or {}).get(abbr)
        best = ordered[0]
        # Concentration: how much of the roster's production comes from its
        # top two players. A high number is a real, story-worthy fragility.
        top2 = sum(p["war"] for p in ordered[:2])
        concentration = (top2 / total_war * 100) if total_war > 0 else 0

        headline_bits = []
        if rec:
            headline_bits.append(f'{rec["w"]}-{rec["l"]}')
        headline_bits.append(f'{total_war:.1f} tracked WAR from {len(players)} players')
        headline_bits.append(f'${total_salary_m:.0f}M')

        if concentration >= 50 and len(ordered) >= 3:
            summary = (f'This roster runs through {best["name"]}. The top two players account for '
                       f'{concentration:.0f}% of everything the team has produced — which is a strength right '
                       "up until one of them gets hurt.")
        elif total_war > 0:
            summary = (f'Production here is spread out: no single player accounts for more than '
                       f'{best["war"] / total_war * 100:.0f}% of the roster\'s tracked WAR. '
                       f'{best["name"]} leads it at {best["war"]:.1f}.')
        else:
            summary = (f'This roster\'s tracked players have produced {total_war:.1f} WAR between them — '
                       "collectively at or below replacement level.")

        used_templates = {}   # per team, so variants reset each roster
        teams[abbr] = {
            "name": team_names.get(abbr, abbr),
            "meta": " · ".join(headline_bits),
            "summary": summary,
            "players": [{
                "name": p["name"], "role": p["role"],
                "war": f'{p["war"]:.1f}',
                "salary": f'${p["salary_m"]:.2f}M' if p["salary_m"] < 10 else f'${p["salary_m"]:.0f}M',
                "share": (f'{p["war"] / total_war * 100:.0f}%' if total_war > 0 and p["war"] > 0 else "—"),
                "story": (_player_story(p, total_war, i, len(ordered), used_templates)
                          if i < NARRATED_PLAYERS else None),
            } for i, p in enumerate(ordered)],
            "narrated": min(NARRATED_PLAYERS, len(ordered)),
        }

    default_team = max(teams, key=lambda a: sum(p["war"] for p in by_team[a])) if teams else None

    return {
        "type": "team-story", "tabLabel": "Team Stories",
        "source": SOURCE_VALUE,
        "metricLabel": "Roster by roster, player by player",
        "title": "Where each team's wins are actually coming from",
        "blurb": ("Pick a team and read it. Every tracked player on the roster, ordered by how many wins "
                  "they've contributed, with a line on what that contribution actually amounts to — who's "
                  "carrying the team, who's being paid like a star without producing like one, and how much "
                  "of the whole operation rests on one or two people."),
        "footnote": ("Share is a player's WAR as a percentage of their team's combined tracked WAR, so it only "
                     "counts players this dashboard follows. See Methods & Sources."),
        "teams": teams,
        "defaultTeam": default_team,
    }
