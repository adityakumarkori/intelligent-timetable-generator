# Edge cases — timetable generation

Handled (with tests):

1. **No available room** — sessions with only type-eliminated rooms yield
   `NO_ELIGIBLE_ROOM` naming the required type and active rooms by type.
2. **No suitable laboratory** — `NO_ELIGIBLE_ROOM` ("laboratory") or
   `ROOM_CAPACITY_CONFLICT` with required vs largest-compatible capacity.
3. **Faculty unavailable for all remaining slots** —
   `FACULTY_AVAILABILITY_CONFLICT` listing eligible faculty and blocked/total
   period counts.
4. **Division has insufficient periods** — exact pigeonhole check gives
   `INSUFFICIENT_PERIOD_CAPACITY` with the numeric deficit.
5. **Required sessions cannot fit** — covered by 4, else `RESOURCE_CONTENTION`.
6. **Room capacity too small** — structural exclusion + validator re-check;
   `ROOM_CAPACITY_CONFLICT` on diagnosis.
7. **Faculty assigned to incompatible subjects** — assignments are an
   allow-list; anything outside it has no candidates (`NO_ELIGIBLE_FACULTY`)
   and fails validation as `INVALID_ASSIGNMENT`.
8. **Multiple resources compete for one slot** — H2/H3/H4 caps; joint
   infeasibility aggregates into `RESOURCE_CONTENTION` with hotspots.
9. **Manual edit creates a conflict** — pre-checks plus full revalidation;
   cross-timetable clashes vs other divisions' PUBLISHED timetables rejected
   with 409; failed edits roll back completely (verified by tests).
10. **Inactive room / faculty / subject** — excluded from candidates,
    flagged as `INACTIVE_ENTITY` on validation.
11. **Inactive subject requirement** — skipped with a loader warning, not
    silently scheduled.
12. **Empty scheduling configuration** — `INVALID_CONFIGURATION` before any
    solve is attempted (no requirements, no teachable periods, bad ids,
    inactive scope).
13. **Duplicate generation request** — new version each time (`max+1`);
    history preserved, unique constraint guards races.
14. **Generated but validation fails** — treated as engine `FAILED`, never
    persisted; the API returns 500 with the violation summary.
15. **Solver timeout without solution** — `FAILED` with a raise-the-limit
    message; feasible-but-unproven solutions still succeed (`FEASIBLE`).

Deferred (documented, not handled):

- Cross-version faculty/room contention (versions are alternative futures).
- Multi-division single-request generation (model already supports it).
- Preferred-period input (S6 inactive; no schema for it yet).
- Solver-level minimal unsatisfiable subsets (diagnosis is dominant-cause,
  explicitly not claimed minimal).

Phase 6 lifecycle additions (with tests):

16. **Entry edit on PUBLISHED/ARCHIVED** — rejected 422 (immutable); clone first.
17. **Delete breaks weekly completeness** — timetable demoted VALID → DRAFT;
    publish of the incomplete draft rejected 422.
18. **Publish while another division holds the slot** — 409, both timetables
    unchanged; replacement publish archives same-division predecessors
    atomically with the new PUBLISHED.
19. **Stale concurrent edit** — `If-Unmodified-Since` mismatch → 409; absent
    header proceeds (documented opt-in concurrency).
20. **Clone numbering race** — unique (session, division, version) guards;
    409 asks the client to retry.
