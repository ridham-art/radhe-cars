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

Write-Host "==> Done. Commit, push, then on the server run: bash scripts/deploy.sh"
