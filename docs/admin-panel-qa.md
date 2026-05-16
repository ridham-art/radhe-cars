# Admin panel production QA (Session 24)

Use after deploy to https://radheauto.com/admin-panel/ (hard refresh or incognito). DevTools: **Network** (disable cache), **Console**.

## Deploy

- [ ] `git pull` on server
- [ ] `bash scripts/deploy.sh` — nav JS + inventory CSS checks pass
- [ ] `python manage.py migrate` — no failed migrations (warning about unmigrated model changes is OK if you did not change models)
- [ ] Restart Gunicorn
- [ ] Hard refresh admin

## Shell and navigation

- [ ] Sidebar: Dashboard → Inventory → Sell car inquiries — no full document reload
- [ ] `body[data-ap-nav-ready="1"]` present
- [ ] Console: no `[AdminPanel] asset load failed`
- [ ] Add / Edit vehicle — full page load (expected)
- [ ] Back / forward — content matches URL

## Performance

- [ ] Inventory: below-fold images lazy-load
- [ ] Dashboard / inventory repeat visit feels snappier (cached counts)
- [ ] After add, edit, delete, or CSV import — tab counts and dashboard stats update (may need refresh if within cache TTL)

## Pages

| Route | Pass |
|-------|------|
| `/admin-panel/` | [ ] Charts, recent listings |
| `/admin-panel/cars/` | [ ] Tabs, filter, sort, pagination (in-page, no full reload) |
| `/admin-panel/cars/add/`, `.../edit/` | [ ] Save, brand/model cascade |
| `/admin-panel/sell-car-inquiries/` | [ ] Approve / reject, badges |
| `/admin-panel/inquiries/`, `.../<id>/` | [ ] Detail, read, delete |
| `/admin-panel/customers/`, `/wishlists/` | [ ] Lists |
| `/admin-panel/vehicle-master/` | [ ] CRUD |
| `/admin-panel/csv/import/` | [ ] Upload → preview → confirm |

## Known limitations

- Brand/carmodel legacy URLs still use old `base.html` shell.
- Cached headline counts may lag up to ~3 minutes unless a mutation invalidates cache.
- Single-server LocMem cache; use Redis if you run multiple Gunicorn workers.

## Sign-off

- [ ] Production admin OK for daily use
- Date: ___________
