# Local / Windows: collect static before you push or after pull (mirrors server step).
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "==> collectstatic"
python manage.py collectstatic --noinput

Write-Host "==> Done. Commit, push, then on the server run: bash scripts/deploy.sh"
