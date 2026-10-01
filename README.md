# Pulse — AI Student Feedback Analysis System (Login)

A secure, containerized login stack for the Pulse student feedback platform:
**PostgreSQL + FastAPI backend + nginx/static frontend**, orchestrated with
Docker Compose and started with a single PowerShell script.

Current scope: a production-shaped **authentication system** (sign in, roles,
server-side lockout, password change) backed by a real database. The rest of
the application (feedback collection, sentiment analysis, dashboards) exists
in the codebase but is not yet wired into the running stack.

---

## Requirements

- **Windows** with **PowerShell**
- **[Docker Desktop](https://www.docker.com/products/docker-desktop/)**, running

No Python, Node.js, or PostgreSQL installation is needed on your machine —
everything runs inside containers.

---

## Quick start

From the project root (`C:\SDU\pulse`):

```powershell
.\start.ps1
```

This script will:
1. Check that Docker Desktop is running (and start it for you if it isn't).
2. Create `.env` from `.env.example` on first run, with a random `JWT_SECRET`.
3. Build and start three containers: `db` (PostgreSQL), `backend` (FastAPI),
   `frontend` (nginx).
4. Wait for the backend health check and the frontend to respond.
5. Open **http://localhost:8080** in your default browser.

The first build downloads base images and Python packages, so it can take a
few minutes depending on your connection. Every run after that reuses Docker's
build cache and starts in seconds.

### Demo accounts

Seeded automatically on first startup (password for all of them: `Pulse#2026`):

| Login | Role |
|---|---|
| `240103083` | Student |
| `faculty@sdu.edu.kz` | Faculty |
| `manager@sdu.edu.kz` | Manager |
| `admin@sdu.edu.kz` | Administrator |

You do **not** select a role when signing in — the backend looks up the
account by login and returns whatever role it actually has.

---

## Stopping / resetting

```powershell
.\start.ps1 -Down            # stop containers, keep the database
.\start.ps1 -Down -Volumes   # stop containers AND wipe the database
.\start.ps1 -Rebuild         # rebuild images from scratch (no cache) and start
```

Or with plain Docker Compose:

```bash
docker compose stop     # pause everything, no rebuild needed to resume
docker compose start    # resume
docker compose down     # stop and remove containers (keeps the named volume)
```

---

## Inspecting the database

The `db` service publishes PostgreSQL on `127.0.0.1:5433` by default (bound to
localhost only — not reachable from outside this machine).

**Quick way, no extra tools:**
```bash
docker compose exec db psql -U pulse -d pulse
```
```sql
\dt                          -- list tables
SELECT * FROM users;
\q
```

**GUI client** (e.g. [DBeaver](https://dbeaver.io/), pgAdmin, TablePlus) —
connect with:

| Field | Value |
|---|---|
| Host | `localhost` |
| Port | `5433` |
| Database | `pulse` |
| User | `pulse` |
| Password | `pulse` (or your `POSTGRES_PASSWORD` from `.env`) |

If port `5433` is already in use on your machine, change `DB_PORT` in `.env`.

---

## Configuration

All settings live in `.env` (created from `.env.example` on first run — see
that file for the full list and defaults). Notable ones:

| Variable | Purpose |
|---|---|
| `JWT_SECRET` | Signs login session tokens. `start.ps1` generates a random one automatically. |
| `MAX_LOGIN_ATTEMPTS` / `LOCK_SECONDS` | Server-side brute-force lockout (default: 5 attempts, 30s lock). |
| `JWT_HOURS` / `JWT_REMEMBER_HOURS` | Session length — normal vs. "Remember me". |
| `SEED_DEMO_DATA` / `DEMO_PASSWORD` | Controls the demo accounts above. Set `SEED_DEMO_DATA=false` once you add real users. |
| `BACKEND_PORT` / `FRONTEND_PORT` / `DB_PORT` | Host ports, in case the defaults (8000 / 8080 / 5433) conflict with something else running on your machine. |

`.env` is git-ignored — never commit it.

---

## What's implemented

- Password hashing with **bcrypt** (never stored or logged in plain text).
- **JWT** session tokens with configurable expiry.
- Server-side **account lockout** after repeated failed attempts (enforced in
  the database, not the browser — cannot be bypassed by clearing local storage).
- Role is **never chosen by the client** — the backend resolves it from the
  account record, so the frontend can't claim a different role.
- Distinct, specific error responses: unknown login (404), wrong password
  (401, with remaining-attempts count), disabled account (403), temporary
  lock (423).
- **Change password** flow (current password verified before the change).
- The database port is bound to `127.0.0.1` only; the backend port is never
  required to be exposed beyond `nginx`'s proxy in a real deployment.

See [`.env.example`](.env.example) for the security-relevant settings to
review before deploying this anywhere beyond your own machine.

---

## Project structure

```
pulse/
├── backend/                 FastAPI application
│   ├── app/
│   │   ├── routers/auth.py  Login, /me, change-password, forgot-password
│   │   ├── models.py        SQLAlchemy models (users, courses, feedback, ...)
│   │   ├── security.py      JWT + bcrypt helpers
│   │   ├── seed.py          Demo departments & users (login-focused seed)
│   │   └── main.py          App entrypoint (currently mounts only `auth`)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── public/index.html    The sign-in page (single static file)
│   ├── nginx.conf           Proxies /api/* to the backend
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── start.ps1
```

> Note: several backend routers and models (surveys, feedback analytics,
> admin management, etc.) exist in the codebase for future use but are
> intentionally not mounted in `main.py` yet, since the current scope is the
> login system only.
