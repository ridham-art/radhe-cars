# MUST bind 0.0.0.0:$PORT or Render shows "Port scan timeout" (default gunicorn is 127.0.0.1 only).
# If Render "Start Command" is set, it overrides this — use the same bind line there or leave Start empty.
web: gunicorn radhe_cars.wsgi --bind 0.0.0.0:$PORT --workers 1 --timeout 120
