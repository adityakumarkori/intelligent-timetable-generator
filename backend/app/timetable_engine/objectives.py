"""Soft-constraint objective system (S1–S5).

 Soft objectives NEVER affect feasibility: they only rank feasible solutions.
 All weights live in ObjectiveWeights (no magic numbers in the builders) and
 every term is an integer-linear expression over helper Booleans channeled to
 the x(s,p,f,r) decision variables. S6 (preferred periods) has no backing
 data in the current schema, so it is documented-but-inactive.
"""

from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from app.timetable_engine.constraints import VarKey
from app.timetable_engine.models import ScopeData, SessionSlot


@dataclass(frozen=True)
class ObjectiveWeights:
    """Points per unit. Tune these without touching constraint code.

    - spread_per_subject_day: reward each distinct day a subject is taught (S1).
    - consecutive_faculty: penalty per back-to-back faculty slot pair (S2).
    - student_gap: penalty per empty slot stranded between classes (S3).
    - repetition: penalty per adjacent same-subject pair (S4).
    - workload_peak: penalty per unit of a faculty member's busiest day (S5).
    """

    spread_per_subject_day: int = 10
    consecutive_faculty: int = 3
    student_gap: int = 5
    repetition: int = 4
    workload_peak: int = 2


@dataclass
class ObjectiveReport:
    weights: ObjectiveWeights
    spread_terms: int = 0
    consecutive_terms: int = 0
    gap_terms: int = 0
    repetition_terms: int = 0
    workload_terms: int = 0
    extra: dict = field(default_factory=dict)


def _or(model: cp_model.CpModel, name: str, members: list) -> cp_model.BoolVarT:
    """Helper Boolean that is true iff at least one member is true."""
    helper = model.NewBoolVar(name)
    if not members:
        model.Add(helper == 0)
        return helper
    model.AddMaxEquality(helper, members)
    return helper


def _and2(
    model: cp_model.CpModel,
    name: str,
    left: cp_model.BoolVarT,
    right: cp_model.BoolVarT,
) -> cp_model.BoolVarT:
    helper = model.NewBoolVar(name)
    model.Add(helper <= left)
    model.Add(helper <= right)
    model.Add(helper >= left + right - 1)
    return helper


def add_objective(
    model: cp_model.CpModel,
    scope: ScopeData,
    sessions: list[SessionSlot],
    var_index: dict[VarKey, cp_model.BoolVarT],
    weights: ObjectiveWeights | None = None,
) -> ObjectiveReport:
    """Maximize soft-constraint score. Returns a report of emitted terms."""
    weights = weights or ObjectiveWeights()
    report = ObjectiveReport(weights=weights)
    score_terms: list = []

    by_session_period: dict[tuple[int, str], list] = {}
    by_faculty_period: dict[tuple[str, str], list] = {}
    by_subject_period: dict[tuple[str, str], list] = {}
    for key, var in var_index.items():
        si = int(key[0])
        by_session_period.setdefault((si, key[1]), []).append(var)
        by_faculty_period.setdefault((key[2], key[1]), []).append(var)
        by_subject_period.setdefault((str(sessions[si].subject_id), key[1]), []).append(var)

    # Per (session, period) placement helper.
    placed: dict[tuple[int, str], cp_model.BoolVarT] = {
        sp: _or(model, f"placed_s{sp[0]}_p{sp[1][:8]}", members)
        for sp, members in by_session_period.items()
    }
    # Per (faculty, period) and (subject, period) aggregates.
    fused = {
        fp: _or(model, f"fteach_{fp[0][:8]}_p{fp[1][:8]}", members)
        for fp, members in by_faculty_period.items()
    }
    subj_used = {
        sp: _or(model, f"sdone_{sp[0][:8]}_p{sp[1][:8]}", members)
        for sp, members in by_subject_period.items()
    }

    day_order = {day: i for i, day in enumerate(scope_day_sequence(scope))}
    teaching_by_day: dict[str, list[str]] = {}
    for pid in scope.teaching_period_ids:
        teaching_by_day.setdefault(scope.periods[pid].day.value, []).append(str(pid))

    sessions_by_subject: dict[str, list[SessionSlot]] = {}
    for s in sessions:
        sessions_by_subject.setdefault(str(s.subject_id), []).append(s)

    # S1 — spread subjects across days.
    for subject_id, subject_sessions in sessions_by_subject.items():
        for day in teaching_by_day:
            count = [
                placed[(s.index, pid)]
                for s in subject_sessions
                for pid in teaching_by_day[day]
                if (s.index, pid) in placed
            ]
            if not count:
                continue
            used_day = model.NewBoolVar(f"useday_{subject_id[:8]}_{day}")
            model.Add(sum(count) > 0).OnlyEnforceIf(used_day)
            model.Add(sum(count) == 0).OnlyEnforceIf(used_day.Not())
            score_terms.append(weights.spread_per_subject_day * used_day)
            report.spread_terms += 1

    for day, pids in teaching_by_day.items():
        pairs = list(zip(pids, pids[1:]))

        # S2 — faculty back-to-back pairs.
        faculty_ids = {key[0] for key in by_faculty_period}
        for fid in faculty_ids:
            for p, q in pairs:
                left, right = fused.get((fid, p)), fused.get((fid, q))
                if left is None or right is None:
                    continue
                both = _and2(model, f"consec_{fid[:8]}_{day}_{p[:4]}", left, right)
                score_terms.append(-weights.consecutive_faculty * both)
                report.consecutive_terms += 1

        # S3 — student gaps: unused slot with class both before and after.
        for division_id in scope.division_ids:
            div_key = str(division_id)
            used_seq = [
                _or(
                    model,
                    f"dused_{div_key[:8]}_{day}_{i}",
                    [
                        placed[(s.index, pid)]
                        for s in sessions
                        if str(s.division_id) == div_key and (s.index, pid) in placed
                    ],
                )
                for i, pid in enumerate(pids)
            ]
            for i in range(len(pids)):
                earlier = _or(model, f"earlier_{div_key[:8]}_{day}_{i}", used_seq[:i])
                later = _or(model, f"later_{div_key[:8]}_{day}_{i}", used_seq[i + 1 :])
                hole = model.NewBoolVar(f"hole_{div_key[:8]}_{day}_{i}")
                model.Add(hole <= 1 - used_seq[i])
                model.Add(hole <= earlier)
                model.Add(hole <= later)
                model.Add(hole >= (1 - used_seq[i]) + earlier + later - 2)
                score_terms.append(-weights.student_gap * hole)
                report.gap_terms += 1

        # S4 — same subject in adjacent slots.
        for subject_id in sessions_by_subject:
            for p, q in pairs:
                left, right = subj_used.get((subject_id, p)), subj_used.get((subject_id, q))
                if left is None or right is None:
                    continue
                both = _and2(model, f"repeat_{subject_id[:8]}_{day}_{p[:4]}", left, right)
                score_terms.append(-weights.repetition * both)
                report.repetition_terms += 1

    # S5 — balance faculty workload by minimizing each faculty's peak day.
    faculty_ids = {key[0] for key in by_faculty_period}
    for fid in faculty_ids:
        peak = model.NewIntVar(0, len(scope.teaching_period_ids), f"peak_{fid[:8]}")
        for day, pids in teaching_by_day.items():
            daily = [fused[(fid, p)] for p in pids if (fid, p) in fused]
            if daily:
                model.Add(peak >= sum(daily))
        score_terms.append(-weights.workload_peak * peak)
        report.workload_terms += 1

    model.Maximize(sum(score_terms))
    return report


def scope_day_sequence(scope: ScopeData) -> list[str]:
    """Distinct days present in teaching periods, in weekday order."""
    order = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
    present = {scope.periods[pid].day.value for pid in scope.teaching_period_ids}
    return [day for day in order if day in present]
