# Intelligent Timetable Generator

A constraint-aware college timetable management and generation system:
administrators configure academic data, generate valid timetables with a
local OR-Tools CP-SAT engine, edit and validate them manually, and publish
versioned schedules that faculty and students can view.

## Problem statement

A college needs to generate timetables across divisions, subjects, faculty
members, classrooms, and periods while respecting hard constraints (teacher/
room/division conflicts, room requirements, faculty availability) and clearly
explaining impossible schedules.

## Key features (all implemented and tested)

* Academic configuration: departments, divisions, subjects, faculty, rooms,
  periods, faculty availability, faculty–subject assignments, division
  subject requirements
* JWT authentication with Argon2id password hashing and role-based access
  control (`SUPER_ADMIN`, `ADMIN`, `FACULTY`, `STUDENT`)
* Timetable generation with Google OR-Tools CP-SAT (runs locally — no Google
  Cloud account or API key required)
* Hard constraints (faculty/room/division conflicts, availability, capacity,
  room type/lab, assignment allow-list, break periods, weekly loads)
* Soft-constraint optimization (subject spread, consecutive classes, student
  gaps, repetition, workload balance) with documented weights
* Independent timetable validation (never trusts solver output blindly)
* Structured conflict detection with human-readable explanations and
  resolution suggestions for infeasible schedules
* Manual timetable editing with whole-timetable revalidation and
  cross-timetable clash detection
* Timetable versioning, validation-gated publishing, archiving, and cloning
* Published-timetable history with lightweight audit (`created_by`,
  `published_by`)

The React frontend covers the complete product workflow: role-based login,
dashboards, all master-data screens, availability/assignment/requirement
management, CP-SAT generation with conflict explanations, the weekly grid,
manual entry editing with validation, versioning, publishing, and
faculty/student timetable views.

## Technology stack

### Frontend

* React 19, TypeScript, Vite 8, Tailwind CSS v3, React Router 7,
  TanStack Query 5, Axios

### Backend

* Python 3.12, FastAPI, SQLAlchemy 2 (async), Pydantic v2, Alembic,
  PostgreSQL 16, PyJWT, Argon2id (argon2-cffi), Google OR-Tools CP-SAT,
  pytest

### Infrastructure

* Docker, Docker Compose

## Architecture (modular monolith)

```text
React Frontend
      ↓ REST
FastAPI REST API
      ↓
Services
      ↓
Timetable Engine
      ↓
OR-Tools CP-SAT
      ↓
Independent Validator
      ↓
PostgreSQL
```

OR-Tools is the constraint optimization solver: it receives Boolean
decision variables and returns assignments. The application owns everything
else — the scheduling domain model, candidate generation, hard-constraint
construction (H1–H11), soft-constraint objectives (S1–S5), independent
validation of every result, and human-readable conflict explanations.
See `docs/architecture.md`, `docs/approach.md`, and `docs/edge-cases.md`.

## Folder structure

```text
./
├── frontend/          # Vite React app (port 3000): auth, dashboards, CRUD,
│                      # generation + conflict UX, timetable grid/editor, role views
├── backend/
│   ├── app/
│   │   ├── core/              # config, async DB, security (JWT/Argon2id), RBAC deps
│   │   ├── api/routes/        # REST endpoints (auth, master data, timetables, generation)
│   │   ├── models/            # SQLAlchemy 2.0 entities
│   │   ├── schemas/           # Pydantic v2 request/response models
│   │   ├── services/          # business logic (timetable lifecycle included)
│   │   ├── timetable_engine/  # CP-SAT pipeline: sessions → candidates →
│   │   │                      # constraints → objectives → solver → validator
│   │   └── seed.py            # idempotent dev seed (explicit command only)
│   ├── alembic/versions/      # 0001_initial_schema, 0002_timetable_audit
│   └── tests/                 # pytest suite (models, auth, API, engine)
├── docs/              # approach, architecture, edge cases
├── docker-compose.yml # postgres + backend + frontend
├── .env.example       # root env template (placeholders only)
└── README.md
```

## Prerequisites

- Node.js 20+ and npm
- Python 3.12+
- PostgreSQL 16+ with a `timetable` database (local mode), or Docker for compose mode

## Environment variables

| File                 | Key                    | Example                                              |
| -------------------- | ---------------------- | ---------------------------------------------------- |
| `backend/.env`       | `DATABASE_URL`         | `postgresql+asyncpg://postgres:password@localhost:5432/timetable` (local) / `...@postgres:5432/...` (docker) |
| `backend/.env`       | `BACKEND_CORS_ORIGINS` | `http://localhost:3000`                              |
| `backend/.env`       | `JWT_SECRET_KEY`       | required, no default (generate with `secrets.token_urlsafe(48)`) |
| `backend/.env`       | `TIMETABLE_SOLVER_TIME_LIMIT_SECONDS` | `30`                                    |
| `backend/.env`       | `TIMETABLE_SOLVER_NUM_WORKERS` | `4`                                            |
| `backend/.env`       | `TIMETABLE_SOLVER_RANDOM_SEED` | `42`                                            |
| `frontend/.env`      | `VITE_API_URL`         | `http://localhost:8000`                              |
| root `.env` (compose)| `POSTGRES_*`           | see `.env.example`                                   |

Copy each `.env.example` to `.env` and adjust. Never commit real secrets.

## Run locally (without Docker)

```powershell
# 1. Database — create databases "timetable" and "timetable_test" in your
#    local PostgreSQL (pgAdmin or createdb).

# 2. Backend
cd backend
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
copy .env.example .env   # then set DATABASE_URL, TEST_DATABASE_URL, JWT_SECRET_KEY
alembic upgrade head     # apply all migrations
python -m app.seed       # idempotent development/demo data (safe to re-run)
uvicorn app.main:app --reload --port 8000
# check: http://localhost:8000/health , http://localhost:8000/api/v1/health
# API docs: http://localhost:8000/docs (Swagger) , http://localhost:8000/redoc

# 3. Frontend (new shell)
cd frontend
npm install
copy .env.example .env
npm run dev              # http://localhost:3000 shows backend health status
```

## Run with Docker

```powershell
copy .env.example .env              # optional; defaults work out of the box
docker compose up --build
# frontend: http://localhost:3000
# backend:  http://localhost:8000/health + /api/v1/health + /docs
docker compose down                 # stop; add -v to drop the pgdata volume
```

The backend Dockerfile runs `uvicorn app.main:app --host 0.0.0.0 --port 8000`;
the frontend image builds with Vite and serves via `vite preview` on port 3000.

## API documentation (Phases 1–6)

| Method | Path                     | Purpose                        | Auth              |
| ------ | ------------------------ | ------------------------------ | ----------------- |
| GET    | `/`                      | root info                      | —                 |
| GET    | `/health`                | liveness probe                 | —                 |
| GET    | `/api/v1/health`         | versioned health check         | —                 |
| POST   | `/api/v1/auth/login`     | email + password → JWT         | —                 |
| GET    | `/api/v1/auth/me`        | current-user profile           | any active user   |
| GET    | `/api/v1/protected/admin`| admin-surface example          | ADMIN, SUPER_ADMIN|
| GET    | `/api/v1/protected/staff`| staff-surface example          | ADMIN, SUPER_ADMIN, FACULTY |

Full OpenAPI/Swagger UI: `http://localhost:8000/docs` (ReDoc: `http://localhost:8000/redoc`).
Health endpoints: `GET /health` and `GET /api/v1/health`.

### Management APIs (Phase 4)

| Resource | Base path | Write access |
| -------- | --------- | ------------ |
| Academic sessions | `/api/v1/academic-sessions` | ADMIN, SUPER_ADMIN |
| Departments | `/api/v1/departments` | ADMIN, SUPER_ADMIN |
| Divisions (+ `/timetable`) | `/api/v1/divisions` | ADMIN, SUPER_ADMIN |
| Subjects | `/api/v1/subjects` | ADMIN, SUPER_ADMIN |
| Faculty (+ `/timetable`) | `/api/v1/faculty` | ADMIN, SUPER_ADMIN |
| Rooms | `/api/v1/rooms` | ADMIN, SUPER_ADMIN |
| Periods | `/api/v1/periods` | ADMIN, SUPER_ADMIN |
| Availability | `/api/v1/faculty/{id}/availability` | ADMIN, SUPER_ADMIN (faculty: own read) |
| Faculty assignments | `/api/v1/faculty-assignments` | ADMIN, SUPER_ADMIN (faculty: own read) |
| Subject requirements | `/api/v1/division-subject-requirements` | ADMIN, SUPER_ADMIN |
| Timetables (read-only) | `/api/v1/timetables` | — (see visibility below) |

Conventions: `GET` list (paged) → `GET` detail → `POST` (201) → `PATCH` → `DELETE`
(204; blocked with 409 while referenced). Errors are always `{"detail": "..."}`:
401 unauthenticated, 403 forbidden, 404 missing, 409 conflict/duplicate/in-use,
422 validation. Lists use `?page=&page_size=` (max 100) and return
`{items, page, page_size, total}` with resource-specific filters (`department_id`,
`day_of_week`, `room_type`, `q` search, …).

Timetable visibility: ADMIN/SUPER_ADMIN see all; FACULTY sees published timetables
plus drafts containing their own classes (own-only on `/faculty/{id}/timetable`);
STUDENT sees published only (drafts return 404, never leak existence).

### Timetable generation (Phase 5, ADMIN/SUPER_ADMIN)

| Method | Path | Purpose |
| ------ | ---- | ------- |
| POST | `/api/v1/timetables/generate` | Solve + validate + persist new version (201; 422 + typed conflicts when infeasible) |
| POST | `/api/v1/timetables/{id}/validate` | Independent re-validation + quality score (GENERATED/DRAFT → VALID on pass) |
| GET | `/api/v1/timetables/{id}/generation-result` | Status + live validation report |

Request: `{academic_session_id, division_id, options: {optimize, time_limit_seconds,
num_workers, random_seed}}`. Engine: OR-Tools CP-SAT locally (no cloud/keys);
hard constraints H1–H11 enforced, soft objectives S1–S5 optimized with documented
weights (`objectives.ObjectiveWeights`); infeasible runs persist nothing and return
structured conflicts (`NO_ELIGIBLE_FACULTY`, `ROOM_CAPACITY_CONFLICT`,
`FACULTY_AVAILABILITY_CONFLICT`, `INSUFFICIENT_PERIOD_CAPACITY`,
`RESOURCE_CONTENTION`, …) with resolution suggestions. Details:
`docs/architecture.md`, `docs/approach.md`, `docs/edge-cases.md`.

### Timetable editing & publishing (Phase 6, ADMIN/SUPER_ADMIN)

| Method | Path | Purpose |
| ------ | ---- | ------- |
| POST | `/api/v1/timetables/{id}/entries` | Add entry (201; 409 + typed conflicts on any violation) |
| PATCH | `/api/v1/timetables/{id}/entries/{entry_id}` | Move/edit entry (whole timetable revalidated) |
| DELETE | `/api/v1/timetables/{id}/entries/{entry_id}` | Remove entry (204; timetable reclassified) |
| POST | `/api/v1/timetables/{id}/publish` | Validate + publish (archives replaced versions atomically) |
| POST | `/api/v1/timetables/{id}/archive` | Retire to history |
| POST | `/api/v1/timetables/{id}/clone` | Copy into a new editable DRAFT version (201) |

Lifecycle: `DRAFT → GENERATED → VALID → PUBLISHED` (`ARCHIVED` for history).
Only editable states (`DRAFT`/`GENERATED`/`VALID`) accept writes; `PUBLISHED`/
`ARCHIVED` are immutable — clone to edit. Edit conflicts return 409 with
`{error, conflicts[], suggestions[]}` (409 = clash with live published data,
422 = own-timetable invalid). Cross-timetable faculty/room checks run against
other divisions' `PUBLISHED` timetables only — same-division versions are
replaced, not rival. Opt-in optimistic concurrency: `If-Unmodified-Since`
header (stale → 409). Audit: `created_by`/`published_by` (migration 0002).

## Authentication (Phase 3)

- Email login returns a signed JWT (`sub` = user id, `role`, `exp`). Send it as
  `Authorization: Bearer <token>`.
- Passwords are hashed with Argon2id (argon2-cffi); hashes never appear in API responses.
- Token lifetime: `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60). Signing key: `JWT_SECRET_KEY`
  (required — generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"`).
- RBAC: SUPER_ADMIN = full access; ADMIN = everything except managing SUPER_ADMIN
  accounts; FACULTY = staff surfaces only; STUDENT = published-schedule viewing only
  (real timetable-view endpoints land in later phases).
- Dev seed users (`admin@college.edu`, `alice@college.edu`, …) all use password `college123`.

  > Development-only credential. Never use in production.

## Database migrations

Alembic (async) manages the schema. `DATABASE_URL` comes from `backend/.env` or the environment.

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head              # apply all migrations
alembic downgrade base            # roll everything back (dev only)
alembic upgrade head              # re-apply — must succeed after a downgrade
```

New migrations (Phase 3+): `alembic revision --autogenerate -m "describe change"`, review, apply.

## Development seed

Explicit command only — never runs on startup:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.seed
```

Seeds 1 department, 2 divisions, 7 subjects, 4 faculty, 4 rooms, Mon–Fri periods,
availability, requirements, and assignments (idempotent — skips if already seeded).
Seed data is for local development/demo purposes only.

> The seed login (`admin@college.edu` / `college123`) is a
> development-only credential. Never use in production.

## Development/Demo Login

The following credentials are seeded by `python -m app.seed` for local development and demo purposes only:

| Role | Email | Password |
|------|-------|----------|
| SUPER_ADMIN | `admin@college.edu` | `college123` |
| ADMIN | `alice@college.edu` | `college123` |
| FACULTY | `bob@college.edu` | `college123` |
| STUDENT | `student@college.edu` | `college123` |

> **Warning:** These are development-only credentials with a weak default password. Never use in production. Always change passwords and remove seed users before deploying to production.

## Frontend (Phase 7)

Role-based single-page app (React 19 + TypeScript strict + Tailwind + Radix
primitives + React Hook Form/Zod + TanStack Query + Axios + Sonner toasts):

- **Login** (`/login`): validation, credential errors, JWT in localStorage
  (never displayed), role-based redirect, 401 interceptor → logout.
- **Admin** (`/admin/...`): dashboard with live counts + recent timetables;
  CRUD for sessions, departments, divisions, subjects, faculty, rooms,
  periods (search, filters, pagination, dialogs, delete confirms);
  availability matrix (missing = available); assignments with duplicate
  guard; weekly requirements with a generation explainer.
- **Timetables**: filterable list incl. version history; **Generate** screen
  (session + division + solver options) showing solver status, quality
  score, and a structured conflict panel with suggestions on failure;
  weekly grid built dynamically from periods; detail page with grid,
  validation tab (violations + quality warnings + score), and versions tab.
- **Editor** (admin, editable statuses only): add/edit/delete entries with
  backend-compatible selects; whole-timetable revalidation; 409 conflict
  and `STALE_TIMETABLE` handling with refresh; `If-Unmodified-Since` sent
  automatically; validate → publish (with confirmation + replacement info)
  → archive → clone-to-draft.
- **Faculty** (`/faculty/...`): dashboard, personal timetable (auto-resolved
  faculty profile), published browser. **Student** (`/student/...`):
  dashboard, division-published schedule. Students/faculty see no admin
  actions; routes enforce roles beyond sidebar hiding, and every screen
  handles loading/empty/error states.

```powershell
cd frontend
npm install
copy .env.example .env   # VITE_API_URL=http://localhost:8000
npm run dev              # http://localhost:3000
npm test                 # vitest suite (23 tests)
npm run build            # strict tsc + production bundle
```

## Testing

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
# create the timetable_test database first, then:
pytest
```

`TEST_DATABASE_URL` (default `.../timetable_test`) selects the test database, which is
truncated after every test. Run the suite with `pytest` from `backend/`
(verified: **166 tests passing**). Suites: `test_models` (creation, relationships,
unique/check/FK constraints, versioning, scoped entry uniqueness), `test_auth`
(login, JWT, RBAC gates, hashing, account rules), `test_api_crud` (master-data
CRUD, safe-delete, session activation, read matrix), `test_api_scheduling`
(availability scoping, assignment/requirement domain rules), `test_api_visibility`
(draft vs published visibility per role), `test_api_generation` (CP-SAT
end-to-end, versioning, infeasible path), `test_api_lifecycle` (edit/validate/
publish/archive/clone, RBAC, concurrency), `test_engine_*` (sessions, candidates,
solver invariants, validator violations, conflicts, loader, quality scoring).

Frontend: `npm test` from `frontend/` (verified: **23 tests passing** —
login flow, route guards, role navigation, grid rendering, conflict display,
validation panel, generation success/failure UX, API error mapping).

## Known limitations

- Generation scope is one division per request (model already multi-division safe).
- Generation-result view recomputes validation live; solver score/duration come
  from `POST /generate` only (no schema change for ephemeral telemetry).
- Cross-version faculty/room contention is out of scope (alternative futures).
- Preferred-period input (S6) has no backing data yet.
- Conflict diagnosis reports dominant evidenced causes, not proven minimal sets.
- Student "relevant division" scoping is publication-based (no enrollment model yet).
- `alembic check` reports a representation-only diff: single-column uniqueness is
  enforced via unique indexes rather than named constraints — no missing enforcement.
- Health endpoints don't touch the database.
- `psql` CLI is not required; any Postgres admin tool works for creating the local DB.
