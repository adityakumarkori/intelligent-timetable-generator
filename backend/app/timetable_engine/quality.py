"""Timetable quality evaluation — soft-constraint scoring without a solver.

 Mirrors the Phase 5 CP-SAT objective (S1–S5, same ObjectiveWeights) as pure
 counting logic over entries + scope data, so validation responses can report
 a score and warnings. Advisory only: warnings never affect validity.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from uuid import UUID

from app.timetable_engine.models import GeneratedEntry, ScopeData
from app.timetable_engine.objectives import ObjectiveWeights

_DAY_ORDER = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]


@dataclass
class QualityReport:
    score: int
    warnings: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


def _teaching_by_day(scope: ScopeData) -> dict[str, list[UUID]]:
    by_day: dict[str, list[UUID]] = {}
    for pid in scope.teaching_period_ids:
        by_day.setdefault(scope.periods[pid].day.value, []).append(pid)
    order = {day: i for i, day in enumerate(_DAY_ORDER)}
    return {
        day: sorted(pids, key=lambda p: scope.periods[p].order)
        for day, pids in sorted(by_day.items(), key=lambda kv: order[kv[0]])
    }


def evaluate_quality(
    entries: list[GeneratedEntry],
    scope: ScopeData,
    weights: ObjectiveWeights | None = None,
) -> QualityReport:
    """Score entries with the S1–S5 formula; collect human-readable warnings."""
    weights = weights or ObjectiveWeights()
    warnings: list[str] = []
    teaching_by_day = _teaching_by_day(scope)

    by_subject_day: dict[tuple[UUID, str], int] = defaultdict(int)
    faculty_day: dict[tuple[UUID, str], list[UUID]] = defaultdict(list)
    div_day_used: dict[tuple[UUID, str], dict[UUID, bool]] = {}
    subj_day_used: dict[tuple[UUID, str], dict[UUID, bool]] = {}
    for entry in entries:
        period = scope.periods.get(entry.period_id)
        if period is None:
            continue
        day = period.day.value
        by_subject_day[(entry.subject_id, day)] += 1
        faculty_day[(entry.faculty_id, day)].append(entry.period_id)
        div_day_used.setdefault((entry.division_id, day), {})[entry.period_id] = True
        subj_day_used.setdefault((entry.subject_id, day), {})[entry.period_id] = True

    def day_label(day: str) -> str:
        return day.capitalize()

    # S1 — distinct subject-days.
    spread = len(by_subject_day)
    days_per_subject: dict[UUID, set[str]] = defaultdict(set)
    for subject_id, day in by_subject_day:
        days_per_subject[subject_id].add(day)
    for (subject_id, day), count in sorted(
        by_subject_day.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])
    ):
        subject = scope.subjects.get(subject_id)
        if subject is not None and count >= 3 and len(days_per_subject[subject_id]) == 1:
            warnings.append(
                f"'{subject.code}' is taught {count} times on a single day "
                f"({day_label(day)}); spreading across days improves the timetable."
            )

    # S2 — consecutive faculty load; S5 — peak daily load per faculty
    # (mirrors the solver: peak = busiest day, not total load).
    consecutive = 0
    peak_total = 0
    faculty_daily: dict[UUID, list[int]] = defaultdict(list)
    for (faculty_id, day), pids in sorted(
        faculty_day.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])
    ):
        # Adjacency spans ALL teaching slots — gaps break runs.
        ordered = teaching_by_day.get(day, [])
        used = set(pids)
        consecutive += sum(1 for a, b in zip(ordered, ordered[1:]) if a in used and b in used)
        faculty_daily[faculty_id].append(len(used))
        faculty = scope.faculty.get(faculty_id)
        name = faculty.name if faculty else str(faculty_id)[:8]
        if _longest_run(ordered, used) >= 3:
            warnings.append(
                f"Faculty '{name}' teaches {_longest_run(ordered, used)} consecutive "
                f"classes on {day_label(day)}; consider inserting a break."
            )
    peak_total = sum(max(loads) for loads in faculty_daily.values())

    # S3 — student gaps.
    gaps = 0
    for (division_id, day), used_map in sorted(
        div_day_used.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])
    ):
        ordered = teaching_by_day.get(day, [])
        flags = [used_map.get(p, False) for p in ordered]
        day_gaps = sum(
            1 for i, on in enumerate(flags)
            if not on and any(flags[:i]) and any(flags[i + 1 :])
        )
        gaps += day_gaps
        if day_gaps:
            division = scope.divisions.get(division_id)
            code = division.code if division else str(division_id)[:8]
            warnings.append(
                f"Division '{code}' has {day_gaps} idle gap(s) between classes on "
                f"{day_label(day)}."
            )

    # S4 — adjacent same-subject repeats.
    repeats = 0
    for (subject_id, day), used_map in sorted(
        subj_day_used.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])
    ):
        ordered = teaching_by_day.get(day, [])
        flags = [used_map.get(p, False) for p in ordered]
        day_repeats = sum(1 for a, b in zip(flags, flags[1:]) if a and b)
        repeats += day_repeats
        if day_repeats:
            subject = scope.subjects.get(subject_id)
            code = subject.code if subject else str(subject_id)[:8]
            warnings.append(
                f"'{code}' is taught in back-to-back periods on {day_label(day)}; "
                "spacing sessions out aids retention."
            )

    score = (
        weights.spread_per_subject_day * spread
        - weights.consecutive_faculty * consecutive
        - weights.student_gap * gaps
        - weights.repetition * repeats
        - weights.workload_peak * peak_total
    )
    return QualityReport(
        score=score,
        warnings=warnings,
        details={
            "distinct_subject_days": spread,
            "consecutive_faculty_pairs": consecutive,
            "student_gaps": gaps,
            "adjacent_repeats": repeats,
            "faculty_peak_load": peak_total,
        },
    )


def _longest_run(ordered: list[UUID], used: set[UUID]) -> int:
    best = run = 0
    for pid in ordered:
        run = run + 1 if pid in used else 0
        best = max(best, run)
    return best
