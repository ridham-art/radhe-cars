# Local / Windows: collect static before you push or after pull (mirrors server step).
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "==> collectstatic"
python manage.py collectstatic --noinput

$navJs = Get-ChildItem -Path "staticfiles\js\admin-panel-nav*.js" -ErrorAction SilentlyContinue
if (-not $navJs) {
    Write-Host "WARNING: admin-panel-nav.js missing from staticfiles — in-shell sidebar nav will not work." -ForegroundColor Red
    exit 1
}
$invCss = Get-ChildItem -Path "staticfiles\css\admin-panel-inventory*.css" -ErrorAction SilentlyContinue
if (-not $invCss) {
    Write-Host "WARNING: admin-panel-inventory.css missing from staticfiles — inventory page styles will 404." -ForegroundColor Red
    exit 1
}

Write-Host "==> Done. Commit, push, then on the server run: bash scripts/deploy.sh"
Write-Host "==> After deploy: hard refresh admin and run docs/admin-panel-qa.md checklist"
