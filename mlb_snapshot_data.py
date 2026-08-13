"""
Hand-verified snapshot of 2026 MLB player value data (WAR vs. salary), pulled
2026-08-13 via targeted, individually-checked fetches against
Baseball-Reference's Player Value tables (bWAR, 2026-value-batting.shtml and
2026-value-pitching.shtml) and FanGraphs RosterResource team payroll pages
(fangraphs.com/roster-resource/payroll/<team>). See build_dashboard.py for
the live-data version, which pulls the FULL league via pybaseball + a
RosterResource scraper run on your own machine.

Why this snapshot is a curated ~47 players, not the full league: the cloud
sandbox that built this kit has locked-down outbound network access (same
constraint documented in the NWSL kit this project is modeled on) -- it can't
run `pip install pybaseball` or call these sites with `requests` directly.
Data here was pulled through a page-fetching tool instead, which is reliable
enough for a bounded, individually-checked set of players but not something
to scale to hundreds of rows without real transcription risk (a lesson the
NWSL kit hit and documented -- see its README's "shots-value bug"). Rather
than bulk-fetch all ~750 active roster players that way, this snapshot
covers 15 of 30 teams: every team that appears at least once in the
Baseball-Reference bWAR top-40 (batters) / top-30 (pitchers) leaderboards,
so it's a real, honest cross-section (MVP-caliber seasons, rookie-deal
bargains, and albatross contracts all included) -- not a cherry-picked
"best case" set.

**Season in progress**: 2026 WAR totals are through 2026-08-13, not a full
season -- re-running build_dashboard.py later in the season (or next year)
will naturally show higher totals and a different leaderboard.

**Salary figures**: 2026 base salary where RosterResource showed one number,
2026 AAV (average annual value) where the guaranteed-contract table showed
both -- AAV is the more meaningful "cost" figure for multi-year deals since
it smooths out backloading/deferrals, and it's what FanGraphs' own Dollars
stat uses. Noted per-player where AAV was used.

**Market rate ($/WAR)**: $11.0M, FanGraphs' overall 2025-26 free-agent-market
average ("What Are Teams Paying For A Win In Free Agency? 2026 Edition",
blogs.fangraphs.com) -- used to compute each player's "surplus value"
(WAR x market rate, minus actual salary). This is a single blended rate for
simplicity; a real refinement would tier it the way that article does
(2+ WAR/yr free agents priced far above replacement-level ones) -- see
README "Where to go next".
"""

MARKET_RATE_PER_WAR = 11_000_000
MARKET_RATE_SOURCE = ("FanGraphs, “What Are Teams Paying For A Win In Free Agency? "
                       "2026 Edition” — overall 2025-26 free-agent market average")

TEAM_NAMES = {
    "CHC": "Chicago Cubs", "HOU": "Houston Astros", "MIA": "Miami Marlins",
    "MIL": "Milwaukee Brewers", "KCR": "Kansas City Royals", "BOS": "Boston Red Sox",
    "TBR": "Tampa Bay Rays", "WSN": "Washington Nationals", "ATL": "Atlanta Braves",
    "ARI": "Arizona Diamondbacks", "NYY": "New York Yankees", "SEA": "Seattle Mariners",
    "LAD": "Los Angeles Dodgers", "LAA": "Los Angeles Angels", "PHI": "Philadelphia Phillies",
}

# Each row: id, name, team abbr, role (batter/pitcher/two-way), WAR (bWAR,
# 2026 season through 8/13), salary in dollars, whether that figure is an
# AAV rather than a straight 2026 salary, and a one-line source note.
PLAYER_ROWS = [
    dict(id="crow-armstrong", name="Pete Crow-Armstrong", team="CHC", role="batter", war=7.5, salary=894_000, is_aav=False),
    dict(id="alvarez", name="Yordan Alvarez", team="HOU", role="batter", war=5.4, salary=26_833_333, is_aav=True),
    dict(id="lopez-otto", name="Otto Lopez", team="MIA", role="batter", war=5.4, salary=810_500, is_aav=False),
    dict(id="turang", name="Brice Turang", team="MIL", role="batter", war=5.3, salary=4_150_000, is_aav=False),
    dict(id="witt", name="Bobby Witt Jr.", team="KCR", role="batter", war=5.2, salary=26_252_525, is_aav=True),
    dict(id="rafaela", name="Ceddanne Rafaela", team="BOS", role="batter", war=5.1, salary=2_250_000, is_aav=False),
    dict(id="caminero", name="Junior Caminero", team="TBR", role="batter", war=4.5, salary=794_800, is_aav=False),
    dict(id="abrams", name="CJ Abrams", team="WSN", role="batter", war=4.4, salary=4_200_000, is_aav=False),
    dict(id="olson", name="Matt Olson", team="ATL", role="batter", war=4.2, salary=22_000_000, is_aav=False),
    dict(id="moreno", name="Gabriel Moreno", team="ARI", role="batter", war=4.1, salary=2_550_000, is_aav=False),
    dict(id="wood", name="James Wood", team="WSN", role="batter", war=4.0, salary=806_900, is_aav=False),
    dict(id="bellinger", name="Cody Bellinger", team="NYY", role="batter", war=3.9, salary=42_500_000, is_aav=False),
    dict(id="carroll", name="Corbin Carroll", team="ARI", role="batter", war=3.9, salary=10_625_000, is_aav=False),
    dict(id="w-contreras", name="Willson Contreras", team="BOS", role="batter", war=3.9, salary=18_000_000, is_aav=False),
    dict(id="young-cole", name="Cole Young", team="SEA", role="batter", war=3.9, salary=786_100, is_aav=False),
    dict(id="harris", name="Michael Harris II", team="ATL", role="batter", war=3.8, salary=8_000_000, is_aav=False),
    dict(id="perdomo", name="Geraldo Perdomo", team="ARI", role="batter", war=3.7, salary=6_250_000, is_aav=False),
    dict(id="muncy", name="Max Muncy", team="LAD", role="batter", war=3.6, salary=10_000_000, is_aav=False),
    dict(id="suzuki", name="Seiya Suzuki", team="CHC", role="batter", war=3.6, salary=19_000_000, is_aav=False),
    dict(id="arozarena", name="Randy Arozarena", team="SEA", role="batter", war=3.4, salary=15_650_000, is_aav=False),
    dict(id="trout", name="Mike Trout", team="LAA", role="batter", war=3.3, salary=37_116_667, is_aav=False),
    dict(id="freeman", name="Freddie Freeman", team="LAD", role="batter", war=3.2, salary=27_000_000, is_aav=False),
    dict(id="bregman", name="Alex Bregman", team="CHC", role="batter", war=3.0, salary=35_000_000, is_aav=False),
    dict(id="pena", name="Jeremy Peña", team="HOU", role="batter", war=3.0, salary=9_475_000, is_aav=False),
    dict(id="edwards", name="Xavier Edwards", team="MIA", role="batter", war=2.9, salary=804_000, is_aav=False),
    dict(id="schwarber", name="Kyle Schwarber", team="PHI", role="batter", war=2.9, salary=18_000_000, is_aav=False),
    dict(id="caglianone", name="Jac Caglianone", team="KCR", role="batter", war=2.8, salary=784_000, is_aav=False),
    dict(id="j-rodriguez", name="Julio Rodríguez", team="SEA", role="batter", war=2.8, salary=20_185_714, is_aav=False),
    dict(id="swanson", name="Dansby Swanson", team="CHC", role="batter", war=2.8, salary=28_000_000, is_aav=False),
    dict(id="hicks", name="Liam Hicks", team="MIA", role="batter", war=2.6, salary=790_000, is_aav=False),
    dict(id="baldwin", name="Drake Baldwin", team="ATL", role="batter", war=2.6, salary=800_000, is_aav=False),
    dict(id="paredes", name="Isaac Paredes", team="HOU", role="batter", war=2.6, salary=9_350_000, is_aav=False),
    dict(id="diaz-yandy", name="Yandy Díaz", team="TBR", role="batter", war=2.5, salary=12_000_000, is_aav=False),
    dict(id="ohtani", name="Shohei Ohtani", team="LAD", role="two-way", war=6.4, salary=70_000_000, is_aav=False,
         note="Two-way: 3.4 bWAR batting + 3.0 bWAR pitching, combined."),
    dict(id="sanchez-c", name="Cristopher Sánchez", team="PHI", role="pitcher", war=6.6, salary=4_000_000, is_aav=False),
    dict(id="wheeler", name="Zack Wheeler", team="PHI", role="pitcher", war=4.6, salary=42_000_000, is_aav=False),
    dict(id="luzardo", name="Jesús Luzardo", team="PHI", role="pitcher", war=4.4, salary=11_000_000, is_aav=False),
    dict(id="e-rodriguez", name="Eduardo Rodriguez", team="ARI", role="pitcher", war=4.3, salary=21_000_000, is_aav=False),
    dict(id="sale", name="Chris Sale", team="ATL", role="pitcher", war=4.0, salary=18_000_000, is_aav=False),
    dict(id="yamamoto", name="Yoshinobu Yamamoto", team="LAD", role="pitcher", war=3.9, salary=16_166_667, is_aav=False),
    dict(id="n-martinez", name="Nick Martinez", team="TBR", role="pitcher", war=3.4, salary=9_000_000, is_aav=False),
    dict(id="lambert", name="Peter Lambert", team="HOU", role="pitcher", war=3.2, salary=1_534_759, is_aav=False),
    dict(id="rasmussen", name="Drew Rasmussen", team="TBR", role="pitcher", war=3.1, salary=5_750_000, is_aav=False),
    dict(id="skubal", name="Tarik Skubal", team="LAD", role="pitcher", war=3.1, salary=32_000_000, is_aav=False,
         note="Traded mid-2026 season; salary/team reflect current club per RosterResource."),
    dict(id="gray", name="Sonny Gray", team="BOS", role="pitcher", war=3.0, salary=31_000_000, is_aav=False),
    dict(id="wacha", name="Michael Wacha", team="KCR", role="pitcher", war=3.0, salary=17_000_000, is_aav=True),
    dict(id="meyer", name="Max Meyer", team="MIA", role="pitcher", war=2.8, salary=980_000, is_aav=False),
]

# Team-level estimated total 2026 payroll (RosterResource "Estimated Total
# Payroll" where the page gave one directly; CHC's page didn't surface that
# total, so it's a sum of the individually-listed player salaries on that
# page instead -- flagged as partial since a handful of minimum-salary
# pre-arb players aren't itemized there, so the true 40-man total is likely
# somewhat higher).
TEAM_PAYROLL = {
    "CHC": dict(total=255_874_000, partial=True),
    "HOU": dict(total=240_000_000, partial=False),
    "MIA": dict(total=74_000_000, partial=False),
    "MIL": dict(total=142_000_000, partial=False),
    "KCR": dict(total=148_000_000, partial=False),
    "BOS": dict(total=199_000_000, partial=False),
    "TBR": dict(total=90_000_000, partial=False),
    "WSN": dict(total=95_257_296, partial=False),
    "ATL": dict(total=259_206_368, partial=False),
    "ARI": dict(total=199_427_366, partial=False),
    "NYY": dict(total=310_000_000, partial=False),
    "SEA": dict(total=167_000_000, partial=False),
    "LAD": dict(total=410_000_000, partial=False),
    "LAA": dict(total=184_000_000, partial=False),
    "PHI": dict(total=290_500_000, partial=False),
}

SOURCES = [
    "Baseball-Reference, Player Value — Batting, 2026 "
    "(baseball-reference.com/leagues/majors/2026-value-batting.shtml)",
    "Baseball-Reference, Player Value — Pitching, 2026 "
    "(baseball-reference.com/leagues/majors/2026-value-pitching.shtml)",
    "FanGraphs RosterResource, per-team Payroll pages "
    "(fangraphs.com/roster-resource/payroll/<team>)",
    MARKET_RATE_SOURCE,
]
