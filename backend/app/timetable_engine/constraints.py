"""CP-SAT hard constraints H1–H4.

 H5–H10 are enforced structurally by candidate pre-filtering (see
 candidate_builder) and re-verified by the independent validator — a
 deliberate, documented split: the solver only decides among combinations
 that are already individually legal, while H1–H4 govern their joint
 selection. H11 (weekly load) follows from session expansion + H1.
"""

from dataclasses import dataclass

from ortools.sat.python import cp_model

from app.timetable_engine.models import Candidate, SessionSlot

# Decision-variable key: (session_index, period_id, faculty_id, room_id) as strings.
VarKey = tuple[str, str, str, str]


@dataclass
class ConstraintReport:
    exactly_once: int = 0  # H1
    division_caps: int = 0  # H2
    faculty_caps: int = 0  # H3
    room_caps: int = 0  # H4

    @property
    def total(self) -> int:
        return self.exactly_once + self.division_caps + self.faculty_caps + self.room_caps


def _key(candidate: Candidate) -> VarKey:
    return (
        str(candidate.session_index),
        str(candidate.period_id),
        str(candidate.faculty_id),
        str(candidate.room_id),
    )


def add_hard_constraints(
    model: cp_model.CpModel,
    sessions: list[SessionSlot],
    candidates: list[Candidate],
) -> tuple[dict[VarKey, cp_model.BoolVarT], ConstraintReport]:
    """Create x(s,p,f,r) Booleans and post H1–H4. Returns var index + report."""
    report = ConstraintReport()
    by_session: dict[int, list[VarKey]] = {s.index: [] for s in sessions}
    by_division_period: dict[tuple[str, str], list[VarKey]] = {}
    by_faculty_period: dict[tuple[str, str], list[VarKey]] = {}
    by_room_period: dict[tuple[str, str], list[VarKey]] = {}

    var_index: dict[VarKey, cp_model.BoolVarT] = {}
    session_of = {s.index: s for s in sessions}
    for candidate in candidates:
        key = _key(candidate)
        var = model.NewBoolVar(
            f"x_s{key[0]}_p{key[1][:8]}_f{key[2][:8]}_r{key[3][:8]}"
        )
        var_index[key] = var
        by_session[candidate.session_index].append(key)
        division_id = str(session_of[candidate.session_index].division_id)
        by_division_period.setdefault((division_id, key[1]), []).append(key)
        by_faculty_period.setdefault((key[2], key[1]), []).append(key)
        by_room_period.setdefault((key[3], key[1]), []).append(key)

    # H1 — every scheduling session exactly once.
    for session in sessions:
        keys = by_session[session.index]
        model.Add(sum(var_index[k] for k in keys) == 1)
        report.exactly_once += 1

    # H2 — division + period → at most one class.
    for keys in by_division_period.values():
        if len(keys) > 1:
            model.Add(sum(var_index[k] for k in keys) <= 1)
            report.division_caps += 1

    # H3 — faculty + period → at most one class (works across divisions).
    for keys in by_faculty_period.values():
        if len(keys) > 1:
            model.Add(sum(var_index[k] for k in keys) <= 1)
            report.faculty_caps += 1

    # H4 — room + period → at most one class.
    for keys in by_room_period.values():
        if len(keys) > 1:
            model.Add(sum(var_index[k] for k in keys) <= 1)
            report.room_caps += 1

    return var_index, report
