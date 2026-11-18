# Student Feedback AI — Sprint 5 (final integrated manager dashboard)

## What stays unchanged
- Student feedback form and account registration (Sprint 1–2).
- Original Feedback analytics cards, Summary, sentiment, common problems, topic analysis, suggestions, keyword cloud, quotes and individual anonymized response explorer (Sprint 3–4).
- Original `frontend/public/pulse.css` restored exactly from the provided original project. Manager-only CSS is in `frontend/public/sprint5.css`.
- No destructive database migrations. The existing data volume is retained when running a normal `docker compose up -d --build`. Never use `down -v` unless you intend to delete the database.

## Manager UX
- On manager sign-in, Overview is displayed.
- Click **Feedback analytics** in the sidebar to expand or collapse its submenu:
  - Feedback explorer: the old Feedback analytics page and all Sprint 3–4 material.
  - Overview: Sprint 5 KPI, sentiment, topics, database-wide counts of users by role, departments, courses, services, and negative alerts.
  - Comparisons & Trends: sentiment and topic changes across recorded semesters, alerts, and 2-bar course / department / service comparison for current and previous semesters, with hover/focus values.
  - Reports: choose the CONTENT (overview, trends, course/department/service comparison, alerts), then the FORMAT (PDF or .xlsx), then download.
- Sidebar changes and manager cards do not change student, faculty or admin routes.

## Demo vs actual data
- Manager indicators and charts come from stored database records and manager-scoped APIs, not hardcoded totals.
- The app's own demo mode (`SEED_DEMO_DATA=true`) creates **synthetic, clearly labelled** `source='seed'` historical data for Fall 2025, Spring 2026 and Fall 2026, to demonstrate real three-semester grouping and negative trend alerts. It does not delete or rewrite student submissions. The historic demo surveys are marked closed and will not appear in student feedback forms.
- In production set `SEED_DEMO_DATA=false`. The number of semesters shown then depends on actual survey data. No invented trend points are shown in production.
- The original data model has a single `Department` catalogue and no separate faculty hierarchy. The Faculty and Department filters currently use the same underlying organisational catalogue. A future faculty/department hierarchy needs an explicit schema change.
- Alert thresholds are controlled by `ALERT_THRESHOLD_PP` (default 12 percentage points) and `ALERT_MIN_FEEDBACK` (default 8 in each compared period). Alerts are recalculated on manager dashboard load or via Refresh alerts. They are displayed on-screen and are not email/push notifications.

## Windows quick start
1. Unzip the full project. Open Docker Desktop.
2. Open PowerShell inside the `Student-Feedback-AI-main` folder containing `docker-compose.yml`.
3. Run `docker compose up -d --build`.
4. Run `docker compose ps` and open http://localhost:8080.
5. Demo manager: `manager@sdu.edu.kz` / `Pulse#2026`.
6. If an old cached page appears, use Ctrl+Shift+R.

**Port note:** The exposed host PostgreSQL port defaults to `5434` (internally it is still `5432`). Override using `DB_PORT` in `.env` if necessary. Existing projects on the same computer may still share the default Docker Compose project name, so do not run two extracted copies simultaneously.

## Modified files (vs the initial provided project)
- `frontend/public/index.html` — integrated sidebar, isolated manager views, UI wiring and export selection.
- `frontend/public/sprint5.css` — NEW, manager-only styles.
- `backend/app/routers/management.py` — NEW, management counts, paired comparisons, PDF and Excel reports.
- `backend/app/routers/analytics.py` — instructor filter and instructor metadata.
- `backend/app/routers/evaluations.py` — department/instructor ids needed for filtering the existing response UI.
- `backend/app/services.py` — instructor filter support.
- `backend/app/routers/reports.py` — retains the previous protected summary PDF/.xlsx exports.
- `backend/app/main.py` — management router registration and existing report router.
- `backend/app/seed.py` — synthetic demo history only, idempotent, no rewrite of real data.
- `backend/requirements.txt` — existing PDF/Excel dependencies.
- `docker-compose.yml` — external DB port default `5434` to avoid the user's occupied/restricted `5432` port.

## Testing notes
- JavaScript `node --check`, Python module compilation, HTML id checks passed.
- Existing NLP unit tests: 13 tests and 25 subtests passed.
- SQLite smoke checks (with auth dependency stubs purely for testing): three historical semesters, 3 sample alerts, manager role counts, course comparisons, PDF and Excel report code paths.
- Headless Chromium smoke checks using mocked API responses: collapsed sidebar -> expand on click, Overview, Comparisons, original 7 insights cards in Feedback explorer, no page errors.
- The actual user's Docker/PostgreSQL installation was not accessible, so a full live end-to-end test against their dataset is not claimed.
