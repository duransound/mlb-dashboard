#!/bin/bash
# Thin wrapper around build_dashboard.py, meant to run from cron on your own
# machine (macOS/Linux) -- see README "Automating the weekly refresh". Not
# meant to be run by Claude or any cloud sandbox; see build_dashboard.py's
# docstring for why.
set -euo pipefail
cd "$(dirname "$0")"

SEASON="${1:-2026}"
DATE_TAG="$(date +%Y-%m-%d)"

# Prefer this project's own virtualenv. cron runs with a minimal PATH and no
# shell profile, so a bare `python3` there resolves to the SYSTEM Python --
# which does not have pandas/requests/lxml and fails with ModuleNotFoundError
# the first time this runs unattended. Falling back to python3 only if the
# venv is missing keeps the script working for anyone who skipped it.
if [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="$(command -v python3 || true)"
  if [ -z "$PYTHON" ]; then
    echo "[$(date)] ERROR: no python3 found and no .venv in $(pwd)." >&2
    echo "  Create one with: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
    exit 1
  fi
  echo "[$(date)] WARNING: no .venv found, using $PYTHON -- if this fails with"
  echo "  ModuleNotFoundError, see the README's 'Run it yourself' section."
fi

echo "[$(date)] Running build_dashboard.py --season $SEASON with $PYTHON"
"$PYTHON" build_dashboard.py --season "$SEASON"

mkdir -p history
cp dashboard.html "history/dashboard_${DATE_TAG}.html"
# keep the last 12 weekly snapshots
ls -1t history/dashboard_*.html 2>/dev/null | tail -n +13 | xargs -r rm --

if [ -d .git ]; then
  git add index.html dashboard.html
  if ! git diff --cached --quiet; then
    git commit -m "Weekly data refresh: ${DATE_TAG}"
    git push
    echo "[$(date)] Pushed refreshed dashboard to GitHub Pages."
  else
    echo "[$(date)] No changes to commit."
  fi
else
  echo "[$(date)] Not a git repo yet -- see README 'Hosting on GitHub Pages' to set that up."
fi
