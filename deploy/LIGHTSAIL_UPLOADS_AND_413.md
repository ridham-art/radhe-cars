# Lightsail: large uploads and fixing HTTP 413

A **413 Request Entity Too Large** on multipart forms (admin car save, public sell flow) is almost always **Nginx** rejecting the body before Gunicorn/Django sees it. Client-side image compression and Django memory limits help, but **production Nginx must allow a large enough body**.

## 1. Nginx (required on the server)

1. Edit the active site (often `/etc/nginx/sites-enabled/radhe-cars` or similar).
2. Inside the `server { ... }` block that serves HTTPS for this app, set:

   ```nginx
   client_max_body_size 100M;
   ```

   Example reference: `deploy/lightsail/nginx-site.conf.example`.

3. If you use a CDN or another reverse proxy in front of Nginx, raise its upload limit too (same order of magnitude).

4. Test and reload:

   ```bash
   sudo nginx -t && sudo systemctl reload nginx
   ```

5. If 413 persists, check which `server` / `location` handled the request:

   ```bash
   sudo tail -n 50 /var/log/nginx/error.log
   ```

## 2. Gunicorn / app process

After changing Nginx, reload is usually enough. If you changed app env or code, restart Gunicorn:

```bash
sudo systemctl restart gunicorn
```

(Use your actual unit name if different.)

## 3. Django environment (optional tuning)

In `.env` on the server you can align in-memory buffering with your instance RAM:

| Variable | Meaning |
|----------|---------|
| `DATA_UPLOAD_MAX_MEMORY_MB` | Megabytes of multipart body buffered in memory before spooling to disk (default **12** in code if unset). |
| `FILE_UPLOAD_MAX_MEMORY_MB` | Per-file in-memory threshold before temp file (default **5** if unset). |

These do **not** replace Nginx’s body limit; they avoid stricter accidental defaults only in edge cases.

## 4. Smoke test after deploy

1. Open admin car form or `/sell/`.
2. Attach **many full-resolution** phone photos (e.g. 15–20) in one submit.
3. Confirm save returns 200/redirect, not 413.
4. If failure, confirm `client_max_body_size` is in the **same** `server` block as `proxy_pass` for that host, then re-check `error.log`.

## 5. Database migrations

If you deploy code that adds migrations (for example admin performance indexes), run on the server:

```bash
cd /var/www/radhe-cars && source venv/bin/activate && python manage.py migrate
```

(Adjust paths and venv to match your layout.)

## 6. Future: direct-to-S3 uploads (optional)

For very large batches or to keep huge bodies off Nginx entirely, consider presigned S3 (or similar) multipart uploads in a later phase; not required for a typical 100M Nginx cap plus client compression.
