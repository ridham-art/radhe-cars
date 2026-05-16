#!/usr/bin/env bash
# Production deploy helper for Radhe Auto (run on the server after git pull).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Installing dependencies (if requirements.txt exists)"
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
fi

echo "==> Collecting static files (hashed filenames for cache busting)"
python manage.py collectstatic --noinput

echo "==> Verify admin nav JS was collected"
if ! ls staticfiles/js/admin-panel-nav*.js 1>/dev/null 2>&1; then
  echo "WARNING: admin-panel-nav.js missing from staticfiles — in-shell sidebar nav will not work."
  exit 1
fi
if ! ls staticfiles/css/admin-panel-inventory*.css 1>/dev/null 2>&1; then
  echo "WARNING: admin-panel-inventory.css missing from staticfiles — inventory page styles will 404."
  exit 1
fi

echo "==> Migrations"
python manage.py migrate --noinput

echo "==> Done. Restart your app server (gunicorn / systemd), e.g.:"
echo "    sudo systemctl restart gunicorn"
echo ""
echo "==> After restart: hard refresh admin and run docs/admin-panel-qa.md checklist"
