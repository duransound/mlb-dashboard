# MLB Value vs. Cost

A sabermetrics dashboard comparing what MLB players **produce** (WAR) against
what they're **paid** (2026 salary) — built the same way as the
[NWSL xG Starter Kit](https://github.com/duransound/nwsl-dashboard) this
project is modeled on: a self-contained, no-build-step, no-framework HTML
dashboard, Python scripts that pull real data, and free hosting on GitHub
Pages.

**Live demo (once you deploy it):** `https://duransound.github.io/mlb-dashboard/`

## What's here

- **`dashboard_template.py`** — the shared chart-drawing library (scatter,
  diverging bar, dropdown team-compare — no external dependencies, pure SVG
  + vanilla JS, so it works fully offline once generated). Adapted directly
  from the NWSL kit's template: same tab shell, same tooltip/highlight
  conventions, retitled and recolored for baseball (navy/red instead of
  amber/clay, a baseball-seam mark instead of the NWSL kit's flower mark).
- **`chart_builders.py`** — the actual chart-construction logic: League
  Picture (WAR vs. Salary scatter), MVP Tracker (top-WAR leaderboard by
  league), Surplus Value (bargains-vs-overpays leaderboard), Team Spending
  vs. Production, and Compare Teammates. Shared by both the demo and live
  paths below, so a chart-logic change is one edit, not two.
- **`mlb_snapshot_data.py`** — the hand-verified 2026 snapshot: 47 players
  across 15 teams, individually checked against Baseball-Reference (WAR) and
  FanGraphs RosterResource (salary). See its docstring for exactly how and
  why it's a sample, not the full league.
- **`demo_dashboard.py`** → `dashboard_demo.html` / `index.html` — builds the
  dashboard from that snapshot. **This is what's currently deployed.**
- **`mlb_data.py`** / **`build_dashboard.py`** → `dashboard.html` — the LIVE
  version: pulls the full league by scraping Baseball-Reference directly for
  WAR and Spotrac's per-team payroll pages for salary (both confirmed
  reachable and working against live data — see "Getting live data working"
  below for the history). Run this on your own machine to replace the
  curated snapshot with real full-league coverage.
- **`run_weekly_update.sh`** / **`.ps1`** — thin wrappers around
  `build_dashboard.py` for a scheduled (cron / Task Scheduler) weekly
  refresh that also pushes to GitHub Pages.

## Why a 47-player snapshot, not the full league, out of the box

The cloud sandbox that built this kit has locked-down outbound network
access — it can only reach a small allowlist of package registries, not
`fangraphs.com`, `baseball-reference.com`, or a `pip install pybaseball`
package's live calls. (Confirmed while building this: direct `curl`/
`requests` calls to `statsapi.mlb.com`, `fangraphs.com`, and `spotrac.com`
all timed out immediately.) That's the exact same constraint the NWSL kit
this project is modeled on hit and documented.

What *did* work from the sandbox was a page-fetching tool that can reach the
open web — reliable enough to build and individually verify a **bounded**
set of players (this is how the 47-player snapshot was built: every player
in Baseball-Reference's 2026 bWAR top-40 batters / top-30 pitchers
leaderboards, cross-referenced against RosterResource payroll pages for the
15 teams they play for), but not something to responsibly scale to ~750
active roster players without real transcription risk. See
`mlb_snapshot_data.py`'s docstring for the full method and sourcing.

**The fix is exactly the NWSL kit's fix: run the real script on your own
machine.** `build_dashboard.py` uses plain `requests`/`pandas` against
Baseball-Reference (WAR) and Spotrac (salary) directly — normal library
calls over a normal internet connection, no page-fetching-tool transcription
risk, covering all 30 teams in about a minute. (Originally this used
`pybaseball` against FanGraphs and RosterResource instead — see "Getting
live data working" below for why that changed.)

## Getting live data working: the FanGraphs → Baseball-Reference/Spotrac story

A real run on 2026-08-13 surfaced something the sandbox that built this kit
couldn't have caught: **FanGraphs now returns HTTP 403 to scripted
requests** — confirmed via a direct diagnostic (`requests.get` with a normal
browser User-Agent) hitting both `pybaseball`'s FanGraphs leaderboard call
and the RosterResource payroll pages, and confirmed to also defeat
[`cloudscraper`](https://github.com/venomous/cloudscraper) (a library built
specifically to get past Cloudflare-style anti-bot pages) — so FanGraphs is
running something more robust than a basic challenge page. This isn't
specific to this project — [pybaseball issue
#479](https://github.com/jldbc/pybaseball/issues/479) and [baseballr issue
#397](https://github.com/billpetti/baseballr/issues/397) (tagged
`upstream-fangraphs`) show the same block hitting other tools.

Both halves of `mlb_data.py` were rewritten to use different sources
entirely, and **both are now confirmed working against live data** as of
2026-08-13:

1. **WAR** — scrapes Baseball-Reference's Player Value tables directly
   (`fetch_war_leaderboards`), using `requests` + `pandas`. Confirmed live:
   881 players fetched in a real run (the real column names turned out to be
   `Player`/`Team`, not `Name`/`Tm` as first guessed — `mlb_data.py` tries
   both namings, see `NAME_TEAM_COL_CANDIDATES`).
2. **Salary** — scrapes Spotrac's per-team payroll pages directly
   (`fetch_team_payroll`), using plain `requests` (Spotrac returns a normal
   200, no cloudscraper needed). Confirmed live: a diagnostic dump of the
   Yankees payroll page showed the real page has several tables (active
   roster, injured list, dead-money for traded/waived/released players, a
   reserve/arbitration list, and a non-player payroll-summary table) —
   `fetch_team_payroll` pulls from every table that has both a `Player`-ish
   column and an exact `Payroll Salary` column, and cleans roster-status
   text (`"10-DAY IL"`, `"TRADED (MIL)"`, etc.) out of the name cells. See
   `mlb_data.py`'s docstrings for the full detail.

If Spotrac ever changes its page layout or starts blocking requests too,
`fetch_all_payrolls` will tell you (every team fails with the same error) —
at that point, either inspect a team's URL in a browser and update
`fetch_team_payroll` to match the new structure, or fall back to a manual
export (open each team's payroll page in your own browser, copy the table
into a spreadsheet, and point `fetch_team_payroll` at a local CSV instead of
a URL).

## Run it yourself

```bash
# One-time setup: this project keeps its dependencies in a local .venv.
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Then, with the venv active:
python demo_dashboard.py           # rebuilds index.html from the curated snapshot (instant, no network)
python build_dashboard.py          # pulls the FULL league live (~1 min, needs internet)
```

On macOS there is no bare `python` on the PATH — that's what
`zsh: command not found: python` means. Either activate the venv first (as
above, which puts a `python` on the PATH), or skip activation and call the
venv's interpreter directly:

```bash
./.venv/bin/python build_dashboard.py --season 2026
```

Plain `python3 build_dashboard.py` uses the *system* Python, which doesn't
have pandas/requests/lxml installed and will fail with `ModuleNotFoundError`.

`build_dashboard.py` flags: `--season` (default 2026), `--min-pa` / `--min-ip`
(playing-time floor before a player is fetched at all, default 100 PA / 20
IP), `--min-war` (optionally drop players below this WAR from the League
Picture scatter *only* — every other tab always uses the full matched set.
Unset by default, so below-replacement players aren't dropped anywhere
unless you explicitly ask for a floor; they're real, and they're exactly
what the Surplus Value tab's "biggest overpay" side is supposed to surface).

Both halves of this pipeline (Baseball-Reference for WAR, Spotrac for
salary) have been confirmed working end-to-end against live data as of
2026-08-13 — see "Getting live data working" above for the history. If a
future run breaks, it's most likely one of these sites having changed its
page layout; `mlb_data.py`'s docstrings say exactly what each function
expects to find (column names, table-qualification rules) so you know what
changed.

## The five tabs

1. **League Picture** — every tracked player, WAR (up) vs. salary (right,
   **log-scaled** — salary spans roughly two orders of magnitude, from
   league-minimum to $70M+, and a linear axis crushes almost everyone into
   a sliver near zero). Dashed median lines split the sample into
   quadrants; top-left is the "cheap and great" corner, bottom-right is
   "expensive and underperforming." A solid line at 0 WAR marks replacement
   level when the sample includes below-replacement players. One point is
   highlighted: the best WAR-per-dollar return in the sample. Past 60
   players, per-point team-abbreviation labels give way to small unlabeled
   dots (identity via the hover tooltip instead) — a few hundred 3-letter
   badges simply can't all fit on one chart legibly. A **Team dropdown**
   above the chart highlights one team's players against the full-league
   backdrop (rather than filtering the rest away) — the point of this chart
   is seeing a roster relative to the whole league, which a filtered view
   would lose.
2. **MVP Tracker** — the top 10 players by WAR in each league, one league
   at a time via a dropdown (defaults to whichever league has the single
   highest-WAR player, so it opens on the more compelling race). This isn't
   an official stat — there's no ballot data here — but a league's top-WAR
   leaderboard is the standard sabermetric stand-in for the MVP
   conversation. Pitchers are included, since WAR puts them on the same
   scale as hitters, even though real MVP voting leans toward position
   players in practice; that caveat is in the tab's own footnote.
3. **Surplus Value** — a leaderboard of `(WAR × assumed $/WAR) − salary`,
   showing the biggest bargains and the biggest overpays side by side. The
   $/WAR rate is a single blended constant (see below) — real front offices
   tier it by player caliber, which is a natural next step here too.
4. **Team Spending vs. Production** — team payroll vs. this sample's total
   WAR on that roster. Explicitly labeled as sample coverage, not a true
   team-WAR total, since the underlying player set isn't every player on
   every 40-man roster (the live path gets much closer to that than the
   demo snapshot does).
5. **Compare Teammates** — pick a team, pick WAR / Salary / Surplus, see
   that roster's tracked players ranked.

## The $/WAR assumption

Surplus value needs a "what's a win worth" constant to compare against
salary. This dashboard uses **$11.0M per WAR** — FanGraphs' reported overall
2025-26 free-agent-market average
([source](https://blogs.fangraphs.com/what-are-teams-paying-for-a-win-in-free-agency-2026-edition/)),
set as `MARKET_RATE_PER_WAR` in `mlb_snapshot_data.py` (demo path) and
`build_dashboard.py` (live path) — change it in either place to test a
different assumption. That same FanGraphs piece found the *real* market is
tiered by player caliber (~$12.8M/WAR for proven 2+ WAR players vs. ~$6.7M/
WAR for fringe free agents) — using one blended number is a simplification
worth revisiting if you want the Surplus Value numbers to hold up to real
scrutiny; see "Where to go next."

## Automating the weekly refresh

Same pattern as the NWSL kit — `run_weekly_update.sh` (macOS/Linux) or
`run_weekly_update.ps1` (Windows), triggered by your OS's own scheduler, not
by Claude:

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
crontab -e
# every Monday 7am:
0 7 * * 1 /full/path/to/mlb-dashboard/run_weekly_update.sh >> /full/path/to/mlb-dashboard/weekly_update.log 2>&1
```

Windows: Task Scheduler → Create Task → weekly trigger → action "Start a
program" running `powershell.exe` with arguments
`-ExecutionPolicy Bypass -File "C:\path\to\mlb-dashboard\run_weekly_update.ps1"`.

Either script overwrites `dashboard.html`/`index.html`, keeps the last 12
weekly snapshots in `history/`, and pushes to GitHub Pages automatically
once you've done the one-time setup below.

## Hosting on GitHub Pages

`index.html` is a complete, self-contained static site, already published at
**https://duransound.github.io/mlb-dashboard/**.

The repo is set up: `origin` points at `duransound/mlb-dashboard`, the branch
is `main`, and Pages is serving `/ (root)`. To publish changes:

```bash
# from inside this mlb-dashboard folder:
git add -A
git commit -m "Update dashboard"
git push
```

Pages redeploys in about a minute. Hard-refresh (Cmd+Shift+R) to get past the
browser cache.

If `git push` asks for a password, GitHub no longer accepts your account
password there — use `gh auth login` or a
[Personal Access Token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).
Both are one-time steps.

`run_weekly_update.sh`/`.ps1` already commit and push automatically each time
they run, so a scheduled refresh publishes itself.

**What's public:** the whole repo (source + dashboard) is visible to anyone
with the link — that's how GitHub Pages' free tier works. Nothing here is
sensitive; it's public MLB stats and salary figures already published by
Baseball-Reference and Spotrac, plus open-source-style code.

## Where to go next

- **Tiered $/WAR** — replace the single `$11M` blended rate with the
  2+/1-2/0-1 WAR tiers FanGraphs itself reports, so a rookie's first full
  win and a proven All-Star's 5th win aren't priced the same. Would sharpen
  Surplus Value noticeably, especially for the bargain end (see "Note on the
  current sample's lopsidedness" below).
- **A "notable overpays" seed list** — the current 47-player snapshot was
  drawn from the *WAR leaderboards*, so it's naturally full of good players
  playing well; even big contracts (Trout, Bregman) come out close to
  breakeven at $11M/WAR because they're still producing real value. A richer
  "biggest bust" story needs a few known underperforming-big-contract
  players added deliberately (the live `build_dashboard.py` path already
  fixes this for free, since it pulls every player above the playing-time
  floor regardless of how good their season is).
- **Contract length / years remaining** — this dashboard only looks at one
  season's salary vs. one season's WAR. A team-building tool would also
  want "years left on this deal," since a $30M/yr player owed 1 more year
  reads very differently than one owed 6.
- **Team logos** — bubbles currently show a 3-letter team-abbreviation
  badge, not a real crest, for the same reason as the NWSL kit (no image
  fetching from this sandbox). Same fix: save each team's logo locally and
  wire it into the `<circle>`/`<image>` marker code in
  `dashboard_template.py`'s `drawScatter`.
- **Pitcher-specific value stats** — FIP-based WAR, or separating
  rate-based (ERA-, FIP-) value from cumulative WAR, for a more
  pitching-native "value" story than reusing the same bWAR-vs-salary frame
  used for hitters.

## Note on the current sample's lopsidedness

Because the demo snapshot draws from the WAR leaderboards, almost every
tracked player comes out at or above breakeven on Surplus Value — that's
expected (rookie-deal stars *should* look like bargains; that's the whole
point of the pre-arbitration salary system) and not a bug, but it does mean
the "biggest overpay" side of the Surplus Value tab is thin (currently just
2 players). The live `build_dashboard.py` path fixes this automatically by
pulling the whole qualifying league, not just the leaderboard.

## Note on the sandbox that built this

Same story as the NWSL kit: the cloud environment used to put this together
has locked-down outbound network access (an allowlist of package
registries only), so it couldn't `pip install pybaseball` or call
`fangraphs.com`/`baseball-reference.com` directly with `requests`. The
47-player snapshot was built from individually fetched, cross-checked pages
instead (see `mlb_snapshot_data.py`'s docstring) — reliable for a bounded
set, not something to scale further from inside a Claude session. Your own
machine won't have that restriction.
