"""
Live data-fetching helpers for the MLB value-vs-cost dashboard -- run on YOUR
machine (unrestricted network), not in the cloud sandbox that built this kit.

**History (see README for the full story):** this file originally pulled WAR
via pybaseball (FanGraphs) and salary via FanGraphs RosterResource. A real
run on 2026-08-13 found FanGraphs now blocks scripted requests site-wide
(HTTP 403, confirmed with `cloudscraper` too, not just plain `requests` --
matches a known, current, upstream issue affecting other MLB scraping tools).
Both halves were switched to different, confirmed-reachable sources:

1. WAR: Baseball-Reference's Player Value tables (`requests` + `pandas`,
   confirmed reachable and confirmed correct table/column detection against
   live data on 2026-08-13 -- 881 players fetched successfully).
2. Salary: Spotrac's per-team payroll pages (confirmed reachable AND its
   real table structure inspected against live data on 2026-08-13 -- see
   `fetch_team_payroll`'s docstring for the specifics of what that page
   actually looks like, which turned out to be messier than RosterResource
   was: multiple sub-tables per team, player names bundled with roster-
   status text that needs cleaning).
"""

import io
import re
import time

import pandas as pd
import requests

BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9",
}


def _slugify_team_name(full_name):
    """"New York Yankees" -> "new-york-yankees", matching Spotrac's URL
    pattern (confirmed against a live fetch of that exact slug on
    2026-08-13). A handful of teams may not follow this exact pattern (the
    Athletics' current city branding in particular is a moving target) --
    if a team 404s, check its real URL on spotrac.com and add an override
    to SPOTRAC_SLUG_OVERRIDES below rather than fighting the slugify logic."""
    s = full_name.lower().replace(".", "").replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


SPOTRAC_SLUG_OVERRIDES = {
    # "ATH": "oakland-athletics",  # uncomment/adjust if "athletics" 404s
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

SPOTRAC_TEAM_SLUGS = {
    abbr: SPOTRAC_SLUG_OVERRIDES.get(abbr, _slugify_team_name(name))
    for abbr, name in TEAM_NAMES.items()
}


def _read_tables(html):
    """pandas.read_html, retrying with HTML comment markers stripped --
    Baseball-Reference wraps some of its tables in <!-- --> specifically to
    deter naive scraping. The main Player Value tables have NOT been
    observed to need this (confirmed reachable directly during this kit's
    build), but this is a cheap, harmless safety net if that ever changes.
    Wrapped in io.StringIO explicitly -- passing a raw string to
    pandas.read_html is deprecated (and, worse, pandas sometimes tries to
    interpret a literal HTML string as a filepath/URL if it doesn't sniff
    unambiguously as markup, which raises a confusing FileNotFoundError)."""
    tables = []
    try:
        tables.extend(pd.read_html(io.StringIO(html)))
    except ValueError:
        pass
    # ALWAYS do the comment-stripped pass too, not just as a fallback.
    # Baseball-Reference ships most secondary tables inside <!-- --> -- on the
    # standings page the division W-L tables are plain HTML but the *expanded*
    # standings (the one carrying R/RA/Rdiff) is commented out. Because the
    # first parse succeeded on the visible tables, the old fallback-only
    # version never ran the second pass, so those tables were invisible and
    # the Pythagorean tab silently had no runs to work with.
    # Raw-pass tables stay FIRST in the list so callers that take the first
    # match (e.g. _find_table_with_columns for WAR) keep their existing
    # behaviour; the stripped pass only ever adds options at the end.
    if "<!--" in html:
        try:
            tables.extend(pd.read_html(io.StringIO(
                html.replace("<!--", "").replace("-->", ""))))
        except ValueError:
            pass
    return tables


def _flatten_columns(df):
    """Baseball-Reference sometimes returns a MultiIndex header (grouped
    column headers) -- collapse to the last non-empty level so "WAR" stays
    "WAR" instead of becoming a tuple."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[-1]) if str(c[-1]) not in ("", "nan") else str(c[0]) for c in df.columns]
    return df


# Baseball-Reference has used both of these header namings across its
# tables/years for the same two columns -- (name-column, team-column) pairs
# to try in order. A real run on 2026-08-13 confirmed the Player Value
# tables use "Player"/"Team" (NOT "Name"/"Tm", which was this file's
# original guess) -- both are kept here so either naming matches, since BR
# hasn't been fully consistent about it across different report types.
NAME_TEAM_COL_CANDIDATES = [("Name", "Tm"), ("Player", "Team")]


def _find_table_with_columns(tables, war_col="WAR"):
    """Scans every table for one containing a name column, a team column
    (either naming convention above), and `war_col`. Returns the table with
    its columns RENAMED to the canonical "Name"/"Tm" so every caller
    downstream doesn't need to care which naming this particular page
    used."""
    for t in tables:
        t = _flatten_columns(t)
        cols = set(str(c) for c in t.columns)
        for name_col, team_col in NAME_TEAM_COL_CANDIDATES:
            if {name_col, team_col, war_col}.issubset(cols):
                return t.rename(columns={name_col: "Name", team_col: "Tm"})
    return None


def fetch_war_table(season, kind):
    """kind: "batting" or "pitching". Returns a DataFrame with at least
    Name/Tm/WAR columns (normalized -- see _find_table_with_columns),
    scraped directly from Baseball-Reference's Player Value pages
    (confirmed reachable with a browser-like User-Agent as of 2026-08-13 --
    see this file's module docstring for why this replaced the
    pybaseball/FanGraphs path). Drops multi-team aggregate rows (Tm ==
    "2TM"/"3TM" etc.) since those can't be matched to a single team's
    payroll -- a small fraction of rows (players traded mid-season), each
    of which still has a separate per-team row in the same table."""
    url = f"https://www.baseball-reference.com/leagues/majors/{season}-value-{kind}.shtml"
    resp = requests.get(url, headers=BROWSER_HEADERS, timeout=30)
    resp.raise_for_status()
    # Baseball-Reference doesn't declare a charset in its Content-Type
    # header, so `requests` falls back to guessing -- and guesses wrong for
    # this page (Latin-1 instead of the page's actual UTF-8), which mangles
    # every accented name into mojibake ("José Ramírez" -> "JosÃ© RamÃ­rez").
    # Confirmed live on 2026-08-13: this was silently dropping every accented
    # name from the salary match (mangled name never matches Spotrac's
    # correctly-encoded one). Forcing UTF-8 explicitly fixes it.
    resp.encoding = "utf-8"
    tables = _read_tables(resp.text)
    df = _find_table_with_columns(tables)
    if df is None:
        raise RuntimeError(
            f"Couldn't find a table with a name/team/WAR column on {url}. "
            f"Found {len(tables)} tables with columns: {[list(t.columns) for t in tables]}. "
            "Baseball-Reference may have changed its layout -- check the URL in a browser, "
            "find the actual column names, and add them to NAME_TEAM_COL_CANDIDATES above."
        )
    df = df[~df["Tm"].astype(str).str.match(r"^\d?TM$", na=False)]
    df = df[df["Name"].notna() & (df["Name"].astype(str) != "Name")]  # drop repeated header rows
    return df


def fetch_war_leaderboards(season, min_pa=0, min_ip=0):
    """Returns a list of {"name", "team", "role", "war"} dicts covering
    Baseball-Reference's `season` batting + pitching Player Value tables,
    filtered to min_pa plate appearances / min_ip innings pitched (BR's own
    PA/IP columns, applied here rather than relying on pybaseball's old
    `qual` param, which this file no longer uses)."""
    bat = fetch_war_table(season, "batting")
    pit = fetch_war_table(season, "pitching")
    if min_pa and "PA" in bat.columns:
        bat = bat[pd.to_numeric(bat["PA"], errors="coerce").fillna(0) >= min_pa]
    if min_ip and "IP" in pit.columns:
        pit = pit[pd.to_numeric(pit["IP"], errors="coerce").fillna(0) >= min_ip]

    rows = []
    for _, r in bat.iterrows():
        rows.append({"name": str(r["Name"]).strip("*# "), "team": r["Tm"], "role": "batter", "war": float(r["WAR"])})
    for _, r in pit.iterrows():
        rows.append({"name": str(r["Name"]).strip("*# "), "team": r["Tm"], "role": "pitcher", "war": float(r["WAR"])})

    # Two-way players (Ohtani) show up once per table under the same
    # name/team -- merge into a single "two-way" row with combined WAR.
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


# Matches a roster-status marker and everything after it, so it can just be
# cut off the end of a name cell. Written as "first status word onward"
# rather than "split on double-spaces", because pandas.read_html collapses
# runs of whitespace between a table cell's sub-elements down to a single
# space (confirmed against a real parse during this kit's build) -- so the
# raw cell text can't be trusted to preserve Spotrac's own internal spacing
# as a delimiter. Cutting from the first recognized status word onward is
# robust to that collapsing either way.
_STATUS_SUFFIX_RE = re.compile(
    r"\b(TRADED|WAIVED|RELEASED|NTC|DISABLED|SUSPENDED|RETIRED|DFA|OPTIONED|"
    r"ANNIVERSARY|ASSIGNED|OUTRIGHTED|DESIGNATED|RESERVE|MINORS|"
    r"\d{1,2}-DAY|IL)\b.*$",
    re.IGNORECASE,
)


def _extract_clean_name(raw):
    """Spotrac's player-name cell isn't just a name -- it's whatever text
    was in that <td>, and the format actually varies by which sub-table it's
    in (confirmed via a live diagnostic dump of the Astros payroll page on
    2026-08-13, which caught a real bug the first version of this function
    missed -- see below):

    - Active roster / injured list / dead-money tables prefix the display
      name with a sort-key last name: "Altuve  Jose Altuve", "Correa
      Carlos Correa  60-DAY: ANKLE", "Witt  Bobby Witt Jr.". Naively
      stripping only the status suffix left "Alvarez Yordan Alvarez" for
      Yordan Alvarez, which then failed to match Baseball-Reference's
      "Yordan Alvarez" downstream -- silently dropping ~90% of players in a
      real run, since this pattern covers the whole active roster, not an
      edge case.
    - The reserve/40-man-depth table has no such prefix: "1 Jake Meyers" is
      just a rank number + the real name.

    Strategy: strip a leading rank-number prefix, cut everything from the
    first recognized roster-status word onward (see _STATUS_SUFFIX_RE),
    then check whether the first remaining word reappears later in the
    string -- if so, that first word is the sort-key duplicate (not part of
    the display name) and gets dropped; a suffix like "Jr." naturally stays
    since it comes after the duplicate. If no such repeat is found, the text
    is assumed to already be a plain name and is left as-is."""
    s = re.sub(r"^\d+\s+", "", str(raw).strip())
    s = _STATUS_SUFFIX_RE.sub("", s).strip()
    s = re.sub(r"\s{2,}", " ", s)
    words = s.split()
    if len(words) >= 3:
        first = words[0].lower()
        if any(w.lower() == first for w in words[1:]):
            words = words[1:]
    return " ".join(words) if words else None


def _is_player_salary_table(df):
    """A Spotrac team payroll page has several tables on it -- active
    roster, injured list, dead money (traded/waived/released players), a
    reserve/arbitration list, and a non-player payroll-summary table --
    confirmed via a live diagnostic dump of the Yankees page on 2026-08-13.
    The player-level ones share two traits: some column name starts with
    "Player" (the exact label varies a little by sub-table) and there's an
    exact "Payroll Salary" column (as opposed to, e.g., "Payroll Salary
    Adjusted", which shows up on the summary table and isn't a per-player
    dollar figure)."""
    cols = [str(c) for c in df.columns]
    has_player_col = any(c.strip().startswith("Player") for c in cols)
    has_salary_col = "Payroll Salary" in cols
    return has_player_col and has_salary_col


def fetch_team_payroll(team_abbr, pause=1.0):
    """Scrapes one team's Spotrac payroll page: returns (player_salary:
    {name: dollars}, total_payroll: float or None). Spotrac returns 200 to
    plain `requests` with a normal browser User-Agent (confirmed live on
    2026-08-13 -- unlike FanGraphs RosterResource, see this file's module
    docstring). Pulls salaries from every qualifying player-level table on
    the page (active roster, injured list, dead money, reserve/arbitration
    list) rather than just the first one, since a player on the IL or a
    traded/released player still counts as real payroll. Team total is
    computed as the sum of the extracted player salaries (not parsed from
    the separate summary table), for consistency with the "partial total"
    convention already used elsewhere in this kit -- see
    mlb_snapshot_data.py's TEAM_PAYROLL."""
    slug = SPOTRAC_TEAM_SLUGS[team_abbr]
    url = f"https://www.spotrac.com/mlb/{slug}/payroll/"
    resp = requests.get(url, timeout=30, headers=BROWSER_HEADERS)
    resp.raise_for_status()
    # See fetch_war_table's comment on the same line -- forcing UTF-8
    # explicitly rather than trusting requests' charset guess. Not observed
    # to be a problem on Spotrac's pages specifically (the live diagnostic
    # sample didn't include an accented name), but it's a one-line guard
    # against the same class of bug for the teams that do have one.
    resp.encoding = "utf-8"
    tables = _read_tables(resp.text)

    salaries = {}
    for t in tables:
        t = _flatten_columns(t)
        if not _is_player_salary_table(t):
            continue
        player_col = next(c for c in t.columns if str(c).strip().startswith("Player"))
        for _, row in t.iterrows():
            name = _extract_clean_name(row[player_col])
            raw = str(row["Payroll Salary"])
            match = re.search(r"[\d,]+", raw.replace("$", ""))
            if not name or not match:
                continue
            salaries[name] = float(match.group(0).replace(",", ""))

    total = sum(salaries.values()) if salaries else None
    time.sleep(pause)
    return salaries, total


def fetch_all_payrolls(team_abbrs=None):
    """Loops fetch_team_payroll over every team (or a subset). Returns
    {abbr: {"salaries": {name: dollars}, "total": float or None}}."""
    team_abbrs = team_abbrs or list(SPOTRAC_TEAM_SLUGS.keys())
    out, failures = {}, 0
    for abbr in team_abbrs:
        try:
            salaries, total = fetch_team_payroll(abbr)
            out[abbr] = {"salaries": salaries, "total": total}
            print(f"  {abbr}: {len(salaries)} players, total ${total/1e6:.0f}M" if total else f"  {abbr}: {len(salaries)} players, total unknown")
        except Exception as e:
            failures += 1
            print(f"  {abbr}: FAILED ({e})")
    if failures == len(team_abbrs) and failures > 0:
        print("\nEvery team failed -- Spotrac may have changed its page layout, or started "
              "blocking requests too. Open one team's URL in a browser (printed in the FAILED "
              "lines above) and compare its table structure against this file's "
              "fetch_team_payroll docstring.")
    return out


# ---------------------------------------------------------------------------
# Standings
#
# Added so the awards tabs can show team context: real MVP voting weighs team
# success heavily, and until now this dashboard had no outcome variable at
# all -- only WAR and salary.
#
# WRITTEN BUT NOT EXECUTED against the live site. The sandbox this was built
# in cannot reach baseball-reference.com, so unlike the WAR and Spotrac
# fetchers (both confirmed against live pages) this one is unverified. It is
# therefore deliberately TOTALLY OPTIONAL: every failure path returns {}, the
# caller treats {} as "no standings," and every downstream chart already
# renders without them. A broken standings scrape must never take the whole
# build down -- the dashboard's core argument doesn't depend on it.
# ---------------------------------------------------------------------------

# Column namings Baseball-Reference has used for wins/losses across its
# standings-style tables. Checked in order.
STANDINGS_COL_CANDIDATES = [("W", "L"), ("Wins", "Losses")]

# The standings tables identify teams by full name or by abbreviation
# depending on which table on the page you land on; both are accepted.
_FULL_NAME_TO_ABBR = {name: abbr for abbr, name in TEAM_NAMES.items()}


def _standings_team_to_abbr(raw):
    """Maps whatever the standings table calls a team to this project's
    abbreviation. Handles full names ("Los Angeles Dodgers"), plain
    abbreviations, and BR's habit of suffixing clinched teams with a marker
    ("Los Angeles Dodgers*", "Milwaukee Brewers (1)")."""
    if raw is None:
        return None
    text = str(raw).strip()
    text = re.sub(r"\s*\(\d+\)$", "", text)          # trailing seed marker
    text = text.rstrip("*xyzXYZ# ").strip()            # clinch markers
    if text in _FULL_NAME_TO_ABBR:
        return _FULL_NAME_TO_ABBR[text]
    if text in TEAM_NAMES:
        return text
    # Last resort: match on the team's nickname (final word(s)) so a
    # relocation or a "Athletics"-style branding change doesn't silently
    # drop a team.
    for full, abbr in _FULL_NAME_TO_ABBR.items():
        if text and (full.endswith(text) or text.endswith(full.split()[-1])):
            return abbr
    return None


# Runs scored / runs allowed column namings, for the Pythagorean tab. On
# Baseball-Reference these live in the *expanded* standings table, which is a
# different table on the same page from the plain W-L one -- hence the merge
# loop below rather than "first table wins".
RUNS_COL_CANDIDATES = [("R", "RA"), ("RS", "RA"), ("Runs", "Runs Allowed")]


def fetch_standings(season):
    """Returns {abbr: {"w", "l", "pct"[, "r", "ra"]}} for every team it can
    parse, or {} if anything at all goes wrong.

    Runs scored/allowed are OPTIONAL and merged in from whichever table on the
    page carries them -- Baseball-Reference splits plain W-L and expanded
    (R/RA/Rdiff) standings across separate tables, so a team's fields can come
    from two different tables. Callers that need runs must check for the keys;
    the Pythagorean tab is skipped entirely when they're absent rather than
    invented.

    Never raises. {} means "team records unavailable"."""
    url = f"https://www.baseball-reference.com/leagues/majors/{season}-standings.shtml"
    try:
        resp = requests.get(url, headers=BROWSER_HEADERS, timeout=30)
        resp.encoding = "utf-8"      # same guard as the WAR fetch: requests
        resp.raise_for_status()      # guesses Latin-1 on these pages
        tables = _read_tables(resp.text)
    except Exception as exc:                                  # noqa: BLE001
        print(f"  standings: could not fetch ({exc.__class__.__name__}: {exc}) "
              "-- continuing without team records")
        return {}

    out = {}
    unmatched = set()
    for raw_table in tables:
        try:
            t = _flatten_columns(raw_table)
        except Exception:                                     # noqa: BLE001
            continue
        cols = set(str(c) for c in t.columns)

        win_col = loss_col = None
        for w, l in STANDINGS_COL_CANDIDATES:
            if {w, l}.issubset(cols):
                win_col, loss_col = w, l
                break
        runs_col = allowed_col = None
        for rs, ra in RUNS_COL_CANDIDATES:
            if {rs, ra}.issubset(cols):
                runs_col, allowed_col = rs, ra
                break
        # A table is only useful if it carries records, runs, or both.
        if not win_col and not runs_col:
            continue

        team_col = next((c for c in ("Tm", "Team", "Name", t.columns[0])
                         if c in t.columns), None)
        if team_col is None:
            continue

        for _, row in t.iterrows():
            raw_label = row.get(team_col)
            abbr = _standings_team_to_abbr(raw_label)
            if not abbr:
                label = str(raw_label).strip()
                # Ignore the obvious non-team rows every BR table carries.
                if (label and label.lower() not in ("nan", "tm", "team", "name")
                        and "average" not in label.lower()
                        and "total" not in label.lower()
                        and not label.startswith("Unnamed")):
                    unmatched.add(label)
                continue
            entry = out.get(abbr, {})

            if win_col and "w" not in entry:
                try:
                    w = int(float(row[win_col]))
                    l = int(float(row[loss_col]))
                except (TypeError, ValueError):
                    w = l = None
                if w is not None and w + l > 0:
                    entry.update({"w": w, "l": l, "pct": round(w / (w + l), 3)})

            if runs_col and "r" not in entry:
                try:
                    r = float(row[runs_col])
                    ra = float(row[allowed_col])
                except (TypeError, ValueError):
                    r = ra = None
                # Baseball-Reference's expanded standings reports R and RA as
                # RUNS PER GAME (e.g. 4.6 / 4.1), not season totals. An
                # earlier guard here required both to exceed 50 -- meant to
                # reject a stray rank column -- and rejected the real data
                # instead. Both units are accepted now and the unit is
                # recorded, because the two must not be silently mixed:
                # Pythagorean expectation is scale-invariant so the
                # percentage is identical either way, but anything that
                # DISPLAYS a run figure has to know which it's holding.
                if r is not None and ra is not None and r > 0 and ra > 0:
                    if r < 25 and ra < 25:
                        entry.update({"r": r, "ra": ra, "runs_per_game": True})
                    elif r > 50 and ra > 50:
                        entry.update({"r": r, "ra": ra, "runs_per_game": False})

            if entry:
                out[abbr] = entry

    # Only teams with a real W-L are usable downstream; a stray row that
    # matched a team name but produced no record is dropped.
    out = {k: v for k, v in out.items() if "w" in v}

    if out:
        with_runs = sum(1 for v in out.values() if "r" in v)
        rate_based = sum(1 for v in out.values() if v.get("runs_per_game"))
        unit = " as runs per game" if rate_based and rate_based == with_runs else ""
        print(f"  standings: parsed records for {len(out)} teams "
              f"({with_runs} with runs scored/allowed{unit})")
        if len(out) < len(TEAM_NAMES):
            missing = sorted(set(TEAM_NAMES) - set(out))
            print(f"  standings: no record found for {', '.join(missing)}")
        if unmatched:
            print("  standings: these table labels didn't map to a team -- "
                  f"{'; '.join(sorted(unmatched)[:8])}")
        if not with_runs:
            print("  standings: no runs-scored/allowed columns found -- the "
                  "Pythagorean tab will be skipped this build. Run "
                  "`python diagnose_standings.py` to dump what's on the page.")
    else:
        print("  standings: no parsable standings table found "
              "-- continuing without team records")
    return out
