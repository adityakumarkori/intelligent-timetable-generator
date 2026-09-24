# Approach — why this design

## Why CP-SAT instead of backtracking/greedy

Timetabling is combinatorial: sessions x periods x faculty x rooms with
all-different constraints across three dimensions. Hand-rolled backtracking
needs bespoke propagation and ordering heuristics ("difficult items first")
that rot as rules grow; greedy search cannot prove infeasibility and gets
stuck. CP-SAT gives complete search with propagation, unsatisfiability
proofs, and weighted optimization in one locally-runnable library — no
cloud, keys, or network. The tradeoff is accepted deliberately: a larger
binary dependency in exchange for a solver we do not have to maintain.

## Why the solver does not own the domain

An opaque "solve()" hides the product's actual rules. So the engine keeps
OR-Tools behind a narrow interface (Booleans in, values out):

1. **Sessions** make weekly loads countable (H11 becomes "schedule each
   session once").
2. **Candidates** make legality explicit and auditable — every excluded
   combination records *why*, which is what powers conflict explanations.
   Rejection tallies are a first-class output, not debug leftovers.
3. **Constraints H1–H4** are the only joint rules the solver sees; H5–H10
   hold structurally, which shrinks the model and makes "why is X placed
   here" answerable from the candidate set.
4. **Objectives S1–S5** only rank feasible solutions; they can never veto
   one (verified by test: tight scopes still solve optimally).
5. **The validator** re-derives correctness from entries + scope data, so a
   bug in mapping or persistence fails loudly instead of publishing garbage.
6. **Conflicts** are diagnosed from domain data, never from solver
   internals — CP-SAT's INFEASIBLE is treated as a trigger for analysis,
   not as an explanation.

## Why per-division timetables with scoped uniqueness

One timetable = one division + one session + one version keeps the
division-conflict rule a simple unique constraint and versions as plain
history rows. Faculty/room contention *across* versions is intentionally
not enforced: versions are competing futures, and only publication
decides which future is real. Publication is the operation that checks a
candidate against the *other* divisions' published timetables — the only
set that represents simultaneous reality.

## Why published means immutable, and edits revalidate everything

A published timetable is a promise to staff and students; mutating it would
rewrite history silently. So fixes flow PUBLISHED → clone → edit DRAFT →
validate → publish-replacement (old archived atomically). Edits validate the
*whole* timetable, not just the changed field, because constraints are
global (moving a room can expose a capacity problem two entries away).
Status is recomputed from validation, never asserted by the client.

## Why generation persists as GENERATED, not VALID

Producing a solution and trusting it are separate claims. The engine
validates pre-persistence (nothing invalid is ever stored as valid), and
the explicit validate step promotes to VALID, leaving an audit trail:
GENERATED = "solver output, machine-checked once", VALID = "re-checked on
demand". Publishing later consumes only VALID/PUBLISHED states.

## Test strategy

Unit tests use small in-memory scopes (no DB, milliseconds each) asserting
*invariants*, not layouts: counts, filtering rules, violation types.
Determinism tests pin seed + single worker and compare canonical layouts.
Integration tests run the real API against PostgreSQL on realistic data and
assert end-to-end properties (201, persisted, valid, versioned) plus the
infeasible path (422, typed conflicts, nothing persisted).
