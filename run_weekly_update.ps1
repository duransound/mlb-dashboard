# Thin wrapper around build_dashboard.py, meant to run from Windows Task
# Scheduler on your own machine -- see README "Automating the weekly
# refresh". Not meant to be run by Claude or any cloud sandbox.
#
# Task Scheduler setup: Create Task -> Trigger: Weekly -> Action: "Start a
# program" running powershell.exe with arguments:
#   -ExecutionPolicy Bypass -File "C:\path\to\mlb-dashboard\run_weekly_update.ps1"

param(
    [string]$Season = "2026"
)

Set-Location -Path $PSScriptRoot

$DateTag = Get-Date -Format "yyyy-MM-dd"
Write-Host "[$(Get-Date)] Running build_dashboard.py --season $Season"
python build_dashboard.py --season $Season

New-Item -ItemType Directory -Force -Path "history" | Out-Null
Copy-Item "dashboard.html" "history\dashboard_$DateTag.html"

# keep the last 12 weekly snapshots
$old = Get-ChildItem "history\dashboard_*.html" | Sort-Object LastWriteTime -Descending | Select-Object -Skip 12
$old | Remove-Item -Force

if (Test-Path ".git") {
    git add index.html dashboard.html
    $changes = git diff --cached --name-only
    if ($changes) {
        git commit -m "Weekly data refresh: $DateTag"
        git push
        Write-Host "[$(Get-Date)] Pushed refreshed dashboard to GitHub Pages."
    } else {
        Write-Host "[$(Get-Date)] No changes to commit."
    }
} else {
    Write-Host "[$(Get-Date)] Not a git repo yet -- see README 'Hosting on GitHub Pages' to set that up."
}
