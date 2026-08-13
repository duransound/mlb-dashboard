#!/bin/bash
# Thin wrapper around build_dashboard.py, meant to run from cron on your own
# machine (macOS/Linux) -- see README "Automating the weekly refresh". Not
# meant to be run by Claude or any cloud sandbox; see build_dashboard.py's
# docstring for why.
set -euo pipefail
cd "$(dirname "$0")"

SEASON="${1:-2026}"
DATE_TAG="$(date +%Y-%m-%d)"

echo "[$(date)] Running build_dashboard.py --season $SEASON"
python3 build_dashboard.py --season "$SEASON"

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
