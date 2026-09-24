# Assumptions

Recorded during GitHub preparation from verified project state
(readable code, docs, and configuration — no guesswork).

## Domain and scheduling

- One timetable covers exactly one division in one academic session;
  versions distinguish history (`uq_timetables_session_division_version`).
- A missing faculty-availability row means AVAILABLE; only explicit
  UNAVAILABLE rows block scheduling.
- Generation scope is one division per request; the CP-SAT model is
  written scope-wide so multi-division requests stay correct later.
- Same-division published versions are *replaced*, not rival: publishing a
  new version archives its predecessors atomically. Cross-timetable
  faculty/room checks compare against *other* divisions' PUBLISHED
  timetables only. Drafts and versions are alternative futures and are
  never checked against each other.
- Statuses mean: GENERATED (solver output, machine-checked once), VALID
  (independently re-checked), PUBLISHED (committed reality, immutable),
  ARCHIVED (retired history), DRAFT (needs work).
- The seed login (`admin@college.edu` / `college123`) exists for local
  development and demos only.

## Configuration and environments

- Backend reads `backend/.env` (never committed); Docker Compose supplies
  working defaults (`postgres` / `password` / `timetable`) when no `.env`
  exists, so `docker compose up --build` works out of the box.
- Local PostgreSQL uses two databases: `timetable` (dev) and
  `timetable_test` (destructively truncated after every test).
- `JWT_SECRET_KEY` has no default and must be set; generate with
  `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- The seed script is idempotent and never runs on startup.
- The bundled React app is a backend health-check page plus a dashboard
  placeholder; all product workflows live in the REST API (`/docs`).

## Verification status at last full run

- 166 pytest tests passing (models, auth, API, engine suites).
- Migrations: `0001_initial_schema` → `0002_timetable_audit` (audit columns
  verified through a downgrade/upgrade cycle on a scratch database).
- OR-Tools CP-SAT runs locally; no Google Cloud account or API key needed.
