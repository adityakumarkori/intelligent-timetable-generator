# Architecture — Intelligent Timetable Generator

Modular monolith: `React → REST → FastAPI → Services → Timetable Engine →
SQLAlchemy → PostgreSQL`. The engine (`backend/app/timetable_engine/`) is
importable without FastAPI and owns every scheduling rule; OR-Tools is only
the constraint/optimization subroutine.

> OR-Tools is used as the underlying constraint optimization solver. The
> application's timetable engine owns the domain model, constraint
> construction, validation, and conflict explanation.

## Timetable engine pipeline

```text
POST /api/v1/timetables/generate
  -> services/generation_service.py   (scope checks, versioning, persistence tx)
  -> engine/generator.run_generation  (async load, sync solve in threadpool)
       data_loader      load session/divisions/requirements/assignments/
                        rooms/periods/availability into ScopeData (once)
       session_builder  expand weekly requirements into SessionSlot list
                        (Mathematics 5/week -> Mathematics-1..5, stable order)
       candidate_builder enumerate legal (session, period, faculty, room)
                        combos; structural pre-filter of H5-H10 + rejection
                        tallies for diagnosis
       constraints      x(s,p,f,r) Booleans; H1 exact-once + H2/H3/H4 caps
       objectives       weighted soft-score helpers (S1-S5), model.Maximize
       solver           CP-SAT (time limit, workers, seed); OPTIMAL/FEASIBLE/
                        INFEASIBLE/UNKNOWN handled explicitly
       solution_mapper  decisions -> GeneratedEntry list (exact-once asserted)
       validator        independent H1-H11 re-check on entries + scope data
       conflict_*       typed conflicts + human explanations on infeasibility
  -> persist new GENERATED version + entries in one transaction (rollback all
     on any failure) -> 201; 422 + conflicts when infeasible
```

## CP-SAT variable model

One Boolean per legal combination: `x(session, period, faculty, room) in {0,1}`,
`1` = selected. Illegal combinations never become variables (candidate
pre-filtering), so the model stays small (seed scale: ~23 sessions, ~2.5k
variables) and hard rules H5-H10 hold structurally:

- H1: `sum(x for session) == 1` per session.
- H2/H3/H4: `sum(x) <= 1` per (division, period), (faculty, period),
  (room, period). Written across the whole scope, so multi-division
  generation stays correct without model changes.
- H5-H10: enforced by candidate legality (availability, capacity, room
  type/lab/override, assignment existence, break/active flags).
- H11: session expansion (N sessions for N/week) + H1.

Soft objectives (integer-linear, maximized; weights in
`objectives.ObjectiveWeights`): S1 distinct subject-days (+10 each), S2
faculty back-to-back pairs (-3), S3 stranded mid-day gaps (-5), S4 adjacent
same-subject repeats (-4), S5 faculty daily-peak load (-2). S6 (preferred
periods) has no backing data and is intentionally inactive.

## Validation and conflicts

The validator (`validator.validate_entries`) checks one timetable's entries
against scope data only — never the solver model — covering weekly loads,
all three per-period uniqueness rules, availability, capacity, room
type/lab/override, assignment validity, break periods, and active entities.
`POST /{id}/validate` re-runs it on persisted timetables, reports a
solver-free quality score plus warnings (`quality.evaluate_quality`, same
S1–S5 weights as the CP-SAT objective), and moves status GENERATED/DRAFT →
VALID on pass (VALID → DRAFT on newly found violations; PUBLISHED untouched).

> Generated timetables are not trusted blindly. Every manually modified
> timetable is independently validated before becoming valid or published.

Infeasibility diagnosis is domain-level, not solver-level: zero-candidate
sessions map to `NO_ELIGIBLE_FACULTY`, `ROOM_CAPACITY_CONFLICT`,
`NO_ELIGIBLE_ROOM`/`ROOM_TYPE_CONFLICT`, `FACULTY_AVAILABILITY_CONFLICT`,
or `NO_AVAILABLE_PERIOD` from rejection tallies; session-vs-slot pigeonhole
gives `INSUFFICIENT_PERIOD_CAPACITY`; otherwise load hotspots aggregate into
`RESOURCE_CONTENTION` (no claim of a minimal conflict set). The explainer
renders messages from real names/counts plus deterministic suggestions.

## Determinism, performance, logging

Inputs are sorted (division/subject codes, weekday/order, names); tests run
CP-SAT single-worker with a fixed seed for byte-stable layouts. All DB reads
happen once in the loader; the solver loop touches only in-memory maps; the
sync solve runs in a worker thread. Structured `timetable_engine` logs emit
`generation_started`, `model_built`, `solver_finished`, `validation_finished`
counts — never credentials or per-variable dumps.

## Timetable lifecycle (Phase 6)

```text
GENERATED/DRAFT --edit--> validate --> VALID/DRAFT --publish--> PUBLISHED
     |                           (invalid/published-replacement path)
     +--clone--> new DRAFT version (fresh IDs, no publication state)
PUBLISHED --publish replacement--> old ARCHIVED + new PUBLISHED (one tx)
```

Entry writes (`POST/PATCH/DELETE .../entries`, ADMIN only) run targeted
pre-checks (existence 404, active/break/requirement/assignment precision),
then cross-check faculty/room against **other divisions' PUBLISHED**
timetables of the same session, then full revalidation — rollback on any
failure, status recomputed (valid → VALID, else DRAFT). Same-division
published versions are *replaced*, not rival, so they are excluded from
cross-checks and archived atomically at publish. No global UNIQUE
constrains history; contention is a service-layer rule. `PUBLISHED`/`ARCHIVED`
are immutable (clone to edit). Optimistic concurrency via optional
`If-Unmodified-Since` against `updated_at` (stale → 409). Lightweight audit:
nullable `created_by`/`published_by` FKs (migration 0002).

## Known limitations

- Generation scope is one division per request (model already multi-division
  safe; API list support later).
- `GET .../generation-result` recomputes validation live; solver
  score/duration are returned by `POST /generate` only (no schema change for
  ephemeral telemetry).
- Cross-version faculty/room contention is out of scope: versions are
  alternative futures, validated independently.
