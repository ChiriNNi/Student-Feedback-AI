# Sprint 5 — Feedback analytics sidebar layout

The Manager sees **Feedback analytics** in the original SDU left sidebar with four compact subitems:
- Feedback explorer — keeps original Sprint 3 and 4 analytics and existing feedback cards.
- Overview — satisfaction, sentiment and top topics, filters, an alert summary.
- Comparisons & Trends — semester sentiment trend, alerts, compare courses, departments and services.
- Reports — authenticated PDF download and native Excel (.xlsx) export.

Only one section is visible at once. Faculty and admin continue to use the original Feedback explorer.

## Existing project: minimal update (recommended)
Extract this ZIP, copy the files from `Sprint5-Sidebar-Patch.zip` into your already running project, overwriting the matching files (frontend index.html and pulse.css, backend main.py, reports.py and requirements.txt). Then run:

    docker compose up -d --build

This preserves the existing Compose settings, DB port mapping and database volume.

## Fresh full project
The new folder still uses Compose's default PostgreSQL host port 5432. If it is occupied, change DB_PORT in .env or set the PowerShell session variable `$env:DB_PORT="5434"` before running compose.

Tests: JavaScript syntax check; HTML section and nesting check; unit tests. Browser end-to-end test with your Docker environment was not possible here.

Notes: Faculty hierarchy is not part of the current database schema; Faculty filter is disabled instead of returning fictitious data. Report Excel button downloads a native .xlsx file through the authenticated backend endpoint. Alerts depend on adequate existing semester data and recomputation.
