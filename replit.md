# Interview Preparation Tracker

A full-stack web application built with Flask that helps students organize and monitor their technical interview preparation.

## Run & Operate

- `cd artifacts/interview-tracker && PORT=5000 python app.py` — run the Flask app (port 5000)
- Workflow: `Start application` (auto-configured)

## Stack

- Python 3.11, Flask, Flask-SQLAlchemy
- SQLite database (auto-created as `interview_tracker.db`)
- Vanilla HTML/CSS/JS (no frontend framework)

## Where things live

- `artifacts/interview-tracker/app.py` — main Flask app, routes, models, seed data
- `artifacts/interview-tracker/templates/` — Jinja2 HTML templates
- `artifacts/interview-tracker/static/css/style.css` — all styles
- `artifacts/interview-tracker/static/js/main.js` — toggle/delete interactivity

## Architecture decisions

- SQLite via Flask-SQLAlchemy for zero-config persistence
- Seed data auto-inserts on first run (15 sample topics across all categories)
- Toggle completion is AJAX (no page reload) via `/toggle/<id>` JSON endpoint
- Categories are code-defined constants (not DB rows) for simplicity

## Product

- Dashboard with overall & per-category progress bars
- Topics page with filter by category, status, and priority
- Add / Edit / Delete preparation topics
- Progress page with detailed per-category topic lists
- Four categories: Aptitude, Programming, Data Structures, Mock Interviews

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- The SQLite database file is created at `artifacts/interview-tracker/instance/interview_tracker.db`
- Seed data only runs when the DB is empty (safe to restart)

## Pointers

- See the `pnpm-workspace` skill for workspace structure details
