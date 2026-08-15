#!/usr/bin/env python3
"""
Apply the "Poppies in the Fog" theme (the NWSL dashboard's Round 20 palette)
to the MLB value-vs-cost dashboard kit.

WHY THIS EXISTS
---------------
The theme lives inside `dashboard_template.py`'s `:root` block and masthead.
Any process that ships a new `dashboard_template.py` -- a Claude session
delivering an updated kit, a restored backup, a `git checkout` -- replaces
that file wholesale and takes the theme with it. Nothing *inside* the file
can defend itself. So the theme is kept here instead, as a patch that can be
re-applied at any time, to both the template and any already-generated HTML.

Idempotent and safe to run on a timer: it patches by *anchor* (CSS custom
property names, and the masthead <svg>/<span> pair) rather than by matching
whole blocks verbatim, so it survives unrelated edits, and it writes nothing
when there is nothing to change.

USAGE
-----
    python3 apply_poppies_theme.py                 # auto-discover targets
    python3 apply_poppies_theme.py foo.html        # explicit targets
    python3 apply_poppies_theme.py --quiet         # only log actual changes
    python3 apply_poppies_theme.py --check         # report, change nothing
    python3 apply_poppies_theme.py --include-history

`install_theme_watcher.sh` installs a launchd agent that runs this
automatically whenever a file in the project changes, so the theme survives
updates without anyone remembering to re-run it.

TO CHANGE THE THEME
-------------------
Edit TOKENS / EXTRA_TOKENS / MASTHEAD below, then run the script. That is the
single source of truth; the template is downstream of it.
"""

import errno
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOCK_PATH = os.path.join(HERE, ".poppies_theme.lock")

# --- palette -----------------------------------------------------------------
# series-1 is unified with the brand's Amber (was blue #2a78d6): the
# "positive/emphasis" data color now literally equals --brand-amber.
# series-1-dark/ink are tuned to keep the hover state and the in-bubble team
# badge text legible against the amber fill -- white on amber fails WCAG
# contrast, dark ink passes. Red stays the negative color.
TOKENS = {
    "--series-1": "#C98A2E",
    "--series-1-dark": "#8A5A1E",
    "--series-1-ink": "#1F1B16",
    "--brand-amber": "#C98A2E",
    "--brand-ink": "#1F1B16",
    "--brand-clay": "#B5573F",
    "--brand-warmgray": "#8C8377",
}

# Added for parity with the NWSL token set (table headers / row hover).
EXTRA_TOKENS = {"--surface-2": "#eceff1"}

# --- masthead ----------------------------------------------------------------
# The poppy + Golden Gate + fog mark, matching the NWSL dashboard and the
# Poppies in the Fog logo artifact.
MASTHEAD = '''<svg class="masthead-mark" viewBox="0 0 240 240" aria-hidden="true">
      <g stroke="#B5573F" fill="none" stroke-linecap="round" opacity="0.6">
        <path d="M6,74 L234,74" stroke-width="2"/>
        <path d="M6,74 C34,46 52,20 68,20 C92,20 96,54 120,58 C144,54 148,20 172,20 C188,20 206,46 234,74" stroke-width="2"/>
        <line x1="63" y1="72" x2="63" y2="20" stroke-width="3"/>
        <line x1="73" y1="72" x2="73" y2="20" stroke-width="3"/>
        <line x1="63" y1="34" x2="73" y2="34" stroke-width="2"/>
        <line x1="63" y1="52" x2="73" y2="52" stroke-width="2"/>
        <line x1="167" y1="72" x2="167" y2="20" stroke-width="3"/>
        <line x1="177" y1="72" x2="177" y2="20" stroke-width="3"/>
        <line x1="167" y1="34" x2="177" y2="34" stroke-width="2"/>
        <line x1="167" y1="52" x2="177" y2="52" stroke-width="2"/>
      </g>
      <path fill="none" stroke="#8C8377" stroke-width="1.5" opacity="0.25" stroke-linecap="round" d="M-10,80 C40,72 80,88 120,80 C160,72 200,88 250,80"/>
      <path fill="none" stroke="#8C8377" stroke-width="1.5" opacity="0.35" stroke-linecap="round" d="M-10,195 C40,183 80,207 120,195 C160,183 200,207 250,195"/>
      <path fill="none" stroke="#8C8377" stroke-width="2" opacity="0.55" stroke-linecap="round" d="M-10,210 C40,196 90,224 130,210 C170,196 210,224 250,210"/>
      <path fill="none" stroke="#8C8377" stroke-width="2.5" opacity="0.8" stroke-linecap="round" d="M-10,226 C40,210 90,240 130,226 C170,210 220,240 250,226"/>
      <g transform="translate(120,150)">
        <g transform="rotate(0)"><path fill="#C98A2E" stroke="#1F1B16" stroke-width="2.5" d="M0,0 C-20,-10 -34,-30 -30,-50 C-26,-68 26,-68 30,-50 C34,-30 20,-10 0,0 Z"/></g>
        <g transform="rotate(90)"><path fill="#C98A2E" stroke="#1F1B16" stroke-width="2.5" d="M0,0 C-20,-10 -34,-30 -30,-50 C-26,-68 26,-68 30,-50 C34,-30 20,-10 0,0 Z"/></g>
        <g transform="rotate(180)"><path fill="#C98A2E" stroke="#1F1B16" stroke-width="2.5" d="M0,0 C-20,-10 -34,-30 -30,-50 C-26,-68 26,-68 30,-50 C34,-30 20,-10 0,0 Z"/></g>
        <g transform="rotate(270)"><path fill="#C98A2E" stroke="#1F1B16" stroke-width="2.5" d="M0,0 C-20,-10 -34,-30 -30,-50 C-26,-68 26,-68 30,-50 C34,-30 20,-10 0,0 Z"/></g>
        <circle r="8" fill="#1F1B16"/>
      </g>
    </svg>
    <span class="masthead-word">Poppies in the Fog</span>'''

MASTHEAD_RE = re.compile(
    r'<svg class="masthead-mark".*?</svg>\s*<span class="masthead-word">.*?</span>',
    re.DOTALL,
)

# Files that carry the theme. dashboard_template.py is the one that matters for
# future builds; the HTML files are already-generated output, themed in place so
# an existing build doesn't need a pipeline re-run.
TEMPLATE_NAME = "dashboard_template.py"


def discover_targets(include_history=False):
    targets = []
    tpl = os.path.join(HERE, TEMPLATE_NAME)
    if os.path.exists(tpl):
        targets.append(tpl)
    targets.extend(sorted(glob.glob(os.path.join(HERE, "*.html"))))
    if include_history:
        targets.extend(sorted(glob.glob(os.path.join(HERE, "history", "*.html"))))
    return targets


def patch_text(s):
    """Return (new_text, list_of_change_descriptions)."""
    changes = []

    for name, value in TOKENS.items():
        # `--series-1:` must not also match `--series-1-dark:` -- the explicit
        # colon in the pattern handles that.
        pattern = re.compile(r"(" + re.escape(name) + r":\s*)(#[0-9A-Fa-f]{3,8})")
        m = pattern.search(s)
        if not m:
            continue
        if m.group(2).lower() != value.lower():
            changes.append("%s %s -> %s" % (name, m.group(2), value))
            s = pattern.sub(lambda mm: mm.group(1) + value, s, count=1)

    # Insert any missing parity tokens right after --series-1-ink.
    for name, value in EXTRA_TOKENS.items():
        if re.search(re.escape(name) + r":", s):
            continue
        anchor = re.search(r"( *)(--series-1-ink:\s*#[0-9A-Fa-f]{3,8};)", s)
        if anchor:
            indent = anchor.group(1)
            s = s.replace(
                anchor.group(0),
                anchor.group(0) + "\n" + indent + "%s: %s;" % (name, value),
                1,
            )
            changes.append("added %s: %s" % (name, value))

    m = MASTHEAD_RE.search(s)
    if m:
        if "Poppies in the Fog" not in m.group(0):
            changes.append("masthead -> poppy mark + Poppies in the Fog")
            s = s[: m.start()] + MASTHEAD + s[m.end():]

    return s, changes


def patch_file(path, check_only=False):
    """Return list of changes made (or that would be made)."""
    try:
        with open(path, encoding="utf-8") as fh:
            original = fh.read()
    except (IOError, OSError, UnicodeDecodeError) as exc:
        return [("!", "could not read: %s" % exc)]

    updated, changes = patch_text(original)
    if updated == original:
        return []
    if not check_only:
        # Write via a temp file in the same directory + atomic rename, so a
        # reader (or another tool) never sees a half-written dashboard.
        tmp = path + ".poppies-tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(updated)
        os.replace(tmp, path)
    return changes


def acquire_lock():
    """Best-effort single-instance lock. Returns a file object or None.

    The watcher and a manual run can fire at the same moment; without this
    they could interleave writes to the same file.
    """
    try:
        import fcntl
    except ImportError:
        return None
    try:
        fh = open(LOCK_PATH, "w")
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fh
    except (IOError, OSError) as exc:
        if exc.errno in (errno.EAGAIN, errno.EACCES, errno.EWOULDBLOCK):
            return "busy"
        return None


def main():
    args = [a for a in sys.argv[1:]]
    quiet = "--quiet" in args
    check_only = "--check" in args
    include_history = "--include-history" in args
    targets = [a for a in args if not a.startswith("--")]
    targets = [os.path.join(HERE, t) if not os.path.isabs(t) else t for t in targets]
    if not targets:
        targets = discover_targets(include_history)

    lock = acquire_lock()
    if lock == "busy":
        if not quiet:
            print("Another run is in progress; nothing to do.")
        return 0

    total = 0
    lines = []
    for path in targets:
        if not os.path.exists(path):
            if not quiet:
                lines.append("  skip (missing): %s" % os.path.basename(path))
            continue
        changes = patch_file(path, check_only=check_only)
        if changes:
            total += 1
            verb = "would patch" if check_only else "patched"
            lines.append("  %s %s" % (verb, os.path.basename(path)))
            for c in changes:
                lines.append("      - %s" % (c if isinstance(c, str) else c[1]))
        elif not quiet:
            lines.append("  already themed: %s" % os.path.basename(path))

    if lines and (total or not quiet):
        try:
            import datetime
            stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            stamp = ""
        print("[%s] Poppies in the Fog theme:" % stamp if stamp else "Poppies in the Fog theme:")
        for line in lines:
            print(line)
        sys.stdout.flush()

    # Exit code 1 in --check mode when something is off-theme, so it can be
    # used as a test / CI gate.
    if check_only and total:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
