#!/bin/bash
#
# Installs a launchd agent that keeps the "Poppies in the Fog" theme applied to
# the Diamond Dollars dashboard, so an update that replaces dashboard_template.py
# no longer silently reverts the design.
#
#   bash install_theme_watcher.sh              # install (or re-install)
#   bash install_theme_watcher.sh --uninstall  # remove it completely
#   bash install_theme_watcher.sh --status     # is it loaded? what did it do?
#
# The agent runs as you, only when you're logged in, and only ever touches files
# inside this project folder. It does two things:
#   * WatchPaths  -- fires within a second or two of any file here changing
#   * StartInterval 300 -- a 5-minute safety net, because launchd's directory
#     watch doesn't reliably fire for in-place writes to an existing file
# Both just run apply_poppies_theme.py, which writes nothing when there's
# nothing to fix, so the cost of a wasted run is a few milliseconds.

set -euo pipefail

LABEL="com.duransound.poppies-theme-watch"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs"
LOG="$LOG_DIR/poppies-theme-watch.log"
SCRIPT="$PROJECT_DIR/apply_poppies_theme.py"

uninstall() {
  if [ -f "$PLIST" ]; then
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || launchctl unload "$PLIST" 2>/dev/null || true
    rm -f "$PLIST"
    echo "Removed $PLIST"
  else
    echo "Not installed (no $PLIST)"
  fi
  echo "The log at $LOG was left in place; delete it if you like."
}

status() {
  if launchctl list 2>/dev/null | grep -q "$LABEL"; then
    echo "LOADED: $LABEL"
  else
    echo "NOT LOADED: $LABEL"
  fi
  echo "plist:   $PLIST"
  echo "project: $PROJECT_DIR"
  echo "log:     $LOG"
  if [ -f "$LOG" ]; then
    echo "--- last 20 log lines ---"
    tail -20 "$LOG"
  fi
}

case "${1:-}" in
  --uninstall|-u) uninstall; exit 0 ;;
  --status|-s)    status;    exit 0 ;;
esac

# --- preflight ---------------------------------------------------------------
if [ ! -f "$SCRIPT" ]; then
  echo "ERROR: apply_poppies_theme.py not found next to this installer." >&2
  echo "       Run this script from inside the mlb-dashboard folder." >&2
  exit 1
fi

PYTHON="$(command -v python3 || true)"
if [ -z "$PYTHON" ]; then
  echo "ERROR: python3 not found on PATH." >&2
  echo "       Install it (or run: xcode-select --install) and try again." >&2
  exit 1
fi
echo "Using python3: $PYTHON"

# Prove the script runs before wiring it to launchd -- a broken agent that
# fails silently every 5 minutes is worse than no agent.
if ! "$PYTHON" "$SCRIPT" --check >/dev/null 2>&1; then
  : # --check exits 1 when files are off-theme, which is fine; only a crash matters
fi
if ! "$PYTHON" -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$SCRIPT"; then
  echo "ERROR: apply_poppies_theme.py failed to parse." >&2
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"

# --- write the plist ---------------------------------------------------------
cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>

  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>$SCRIPT</string>
    <string>--quiet</string>
  </array>

  <key>WorkingDirectory</key>
  <string>$PROJECT_DIR</string>

  <!-- Fires on adds/removes/renames in the project folder, and on writes to
       the four files that actually carry the theme. -->
  <key>WatchPaths</key>
  <array>
    <string>$PROJECT_DIR</string>
    <string>$PROJECT_DIR/dashboard_template.py</string>
    <string>$PROJECT_DIR/dashboard.html</string>
    <string>$PROJECT_DIR/index.html</string>
    <string>$PROJECT_DIR/dashboard_demo.html</string>
  </array>

  <!-- Safety net: launchd's watch can miss an in-place write to an existing
       file, so also sweep every 5 minutes. A no-op run costs milliseconds. -->
  <key>StartInterval</key>
  <integer>300</integer>

  <key>RunAtLoad</key>
  <true/>

  <key>StandardOutPath</key>
  <string>$LOG</string>
  <key>StandardErrorPath</key>
  <string>$LOG</string>

  <key>ProcessType</key>
  <string>Background</string>
  <key>LowPriorityIO</key>
  <true/>
  <key>Nice</key>
  <integer>5</integer>
</dict>
</plist>
PLIST_EOF

plutil -lint "$PLIST" >/dev/null || { echo "ERROR: generated plist is invalid." >&2; exit 1; }

# --- (re)load ----------------------------------------------------------------
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || launchctl unload "$PLIST" 2>/dev/null || true
if ! launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null; then
  launchctl load "$PLIST"
fi

sleep 2
echo
if launchctl list 2>/dev/null | grep -q "$LABEL"; then
  echo "Installed and running."
else
  echo "Installed, but launchctl doesn't list it yet -- check: bash $0 --status"
fi
echo
echo "  watching:  $PROJECT_DIR"
echo "  log:       $LOG"
echo "  uninstall: bash $0 --uninstall"
echo
echo "Test it: change --series-1 in dashboard_template.py to something else,"
echo "save, wait a few seconds, and look again -- it should be back to #C98A2E."
