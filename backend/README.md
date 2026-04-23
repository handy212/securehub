# Backend Scaffold

This Django scaffold is organized around the core Alarm Hub domains:

- `apps.accounts` handles user profile data and JWT auth endpoints
- `apps.sites` handles sites, customer access, devices, subsystems, and zones
- `apps.alarms` handles events, alarm commands, and notification delivery records
- `apps.hik_adapter` isolates Hik-Partner Pro integration logic

## Planned API surface

- `POST /api/v1/auth/login/`
- `POST /api/v1/auth/refresh/`
- `GET /api/v1/profile/`
- `GET /`
- `GET /healthz/`
- `GET /api/v1/sites/`
- `GET /api/v1/sites/<site_id>/`
- `GET /api/v1/sites/<site_id>/status/`
- `POST /api/v1/sites/<site_id>/subsystems/<subsystem_id>/arm/`
- `POST /api/v1/sites/<site_id>/subsystems/<subsystem_id>/disarm/`
- `POST /api/v1/sites/<site_id>/subsystems/<subsystem_id>/stay-arm/`
- `POST /api/v1/sites/<site_id>/subsystems/<subsystem_id>/clear-alarm/`
- `GET /api/v1/sites/<site_id>/events/`
- `GET /api/v1/sites/<site_id>/commands/`

## Local setup

1. Create a virtual environment.
2. Install `requirements.txt`.
3. Copy `.env.example` to `.env`.
4. Run `python manage.py makemigrations`.
5. Run `python manage.py migrate`.
6. Create a superuser.
7. Start the API with `python manage.py runserver`.
8. Run `python manage.py test` to verify the backend.
9. Run `python manage.py seed_demo` for demo users, sites, devices, and events.

### Database note

The scaffold defaults to SQLite for local development via `DJANGO_USE_SQLITE=True`, which uses `backend/db.sqlite3`.

If you want PostgreSQL instead, set `DJANGO_USE_SQLITE=False` in `backend/.env` and make sure a Postgres server is running and accepting connections on the configured host and port before starting Django.

### Celery note

There are two supported local Celery modes:

- `CELERY_TASK_ALWAYS_EAGER=True`: tasks run inline in the web process for simple local development. Do not run `celery beat` in this mode.
- `CELERY_TASK_ALWAYS_EAGER=False`: tasks are queued through Redis. Run both `celery -A config worker -l info` and `celery -A config beat -l info`.

For safe local Hikvision testing, set `HIK_PARTNER_DRY_RUN=True`. With `HIK_PARTNER_DRY_RUN=False`, periodic tasks and command actions will call the live Hik-Partner API.

## PDF-Verified Integration Notes

- `POST /api/hpcgw/v1/token/get` returns an access token and an `areaDomain`; follow-up calls should use that returned area domain.
- alarm control uses `/api/hpcgw/v1/device/transparent/{isapi uri}` with `Authorization: Bearer <accessToken>` and `X-Devserial`
- AX Pro operations can additionally require `X-Username`, `X-Password`, and `X-Userlevel`
- `arm` uses partition numbers in the ISAPI URI, with `ways=away` or `ways=stay`
- `clearAlarm` and `disarm` also operate on partition numbers
- `POST /api/hpcgw/v2/site/assign` is for installer/site-manager assignment, not customer assignment
- end-user access is based on `POST /api/hpcgw/v2/site/handover/share` and the `site/customer/*` APIs
- webhook push still depends on a prior `POST /api/hpcgw/v1/mq/subscribe`

The Hik integration service is still intentionally stubbed, but the transparent request shape now matches the PDF much more closely.


## 🚀 Development Services (tmux Mode)

You can start all required development services (Django, Celery, ngrok) in separate terminal "windows" using the upgraded script:

```bash
./start_services.sh
```

This script uses `tmux` to run each service in its own process. When you run it:
1. It starts a new tmux session named `securehub`.
2. It splits services into labeled windows:
   - `Django`: The web server.
   - `Worker`: Celery task processor.
   - `Beat`: Celery scheduler.
   - `Tunnel`: Webhook registration and ngrok.
3. It automatically attaches your current terminal to this session.

### ⌨️ Navigation Shortcuts
- **Switch windows**: Press `Ctrl+B`, then `n` (next) or `p` (previous).
- **Detach** (hide session BUT keep services running): Press `Ctrl+B`, then `d`.
- **Re-attach**: Run `tmux attach -t securehub`.
- **Shut down everything**: Hold `Ctrl+B`, then type `:kill-session` and press Enter (or just run `tmux kill-session -t securehub` from a regular terminal).
