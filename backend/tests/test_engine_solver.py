"""Solver tests: hard-constraint invariants, infeasibility, soft-objective effect."""

from collections import Counter

from app.timetable_engine.models import GenerationStatus, SolverStatus
from app.timetable_engine.validator import validate_entries
from tests.engine_helpers import basic_case, solve_case, spread_score


def test_feasible_scope_solves_optimal_and_validates():
    case = basic_case()
    result = solve_case(case)
    assert result.status == GenerationStatus.SUCCESS
    assert result.solver_status == SolverStatus.OPTIMAL
    assert result.timetable_id is None  # persistence is the service layer's job
    assert len(result.entries) == 3
    report = validate_entries(result.entries, case.scope)
    assert report.valid, [v.message for v in report.violations]


def test_hard_invariants_hold_on_solution():
    case = basic_case(math_per_week=4, lab_per_week=2, days=("MONDAY", "TUESDAY", "WEDNESDAY"))
    result = solve_case(case)
    assert result.status == GenerationStatus.SUCCESS
    # H1+H11: weekly counts per subject.
    counts = Counter(
        (e.division_id, e.subject_id) for e in result.entries
    )
    assert len(result.entries) == 6
    for (division_id, subject_id), count in counts.items():
        subject = case.scope.subjects[subject_id]
        expected = next(
            r.periods_per_week for r in case.scope.requirements
            if r.division_id == division_id and r.subject.id == subject_id
        )
        assert count == expected, subject.code
    # H2/H3/H4: uniqueness per period.
    assert len({(e.division_id, e.period_id) for e in result.entries}) == 6
    assert len({(e.faculty_id, e.period_id) for e in result.entries}) == 6
    assert len({(e.room_id, e.period_id) for e in result.entries}) == 6


def test_overconstrained_scope_is_infeasible():
    # 3 sessions but a single teachable period.
    case = basic_case(days=("MONDAY",), slots_per_day=1)
    result = solve_case(case)
    assert result.status == GenerationStatus.INFEASIBLE


def test_optimization_improves_spread_without_breaking_hard_rules():
    # 4 MATH sessions over 2 days: feasibility-only may pile them on one day.
    case = basic_case(math_per_week=4, lab_per_week=0, days=("MONDAY", "TUESDAY"))
    optimized = solve_case(case, optimize=True)
    feasible_only = solve_case(case, optimize=False)
    assert optimized.status == GenerationStatus.SUCCESS
    assert feasible_only.status == GenerationStatus.SUCCESS
    assert optimized.objective_score is not None
    assert feasible_only.objective_score is None  # no objective built
    assert spread_score(optimized.entries, case.scope) >= spread_score(
        feasible_only.entries, case.scope
    )
    for result in (optimized, feasible_only):
        assert validate_entries(result.entries, case.scope).valid


def test_soft_constraints_never_override_hard_constraints():
    # One slot, one session: optimum is forced; objective must not break it.
    case = basic_case(math_per_week=1, lab_per_week=0, days=("MONDAY",), slots_per_day=1)
    result = solve_case(case)
    assert result.status == GenerationStatus.SUCCESS
    assert validate_entries(result.entries, case.scope).valid


def test_generation_is_deterministic_with_fixed_seed():
    case = basic_case(
        math_per_week=4, lab_per_week=2, days=("MONDAY", "TUESDAY", "WEDNESDAY")
    )
    first = solve_case(case)
    second = solve_case(case)

    def canonical(result):
        scope = case.scope
        return sorted(
            (
                e.session_index,
                scope.periods[e.period_id].day.value,
                scope.periods[e.period_id].order,
                scope.faculty[e.faculty_id].name,
                scope.rooms[e.room_id].name,
            )
            for e in result.entries
        )

    assert first.status.value == "SUCCESS"
    assert canonical(first) == canonical(second)
