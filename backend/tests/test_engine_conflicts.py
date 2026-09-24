"""Conflict analysis tests: typed conflicts, real-data explanations, suggestions."""

from app.timetable_engine.conflict_explainer import explain_conflicts
from app.timetable_engine.generator import generate_from_scope
from app.timetable_engine.models import ConflictType, GenerationStatus
from app.timetable_engine.solver import SolverOptions
from tests.engine_helpers import basic_case


def _run(case):
    return generate_from_scope(
        case.scope, SolverOptions(time_limit_seconds=10.0, num_workers=1, random_seed=42)
    )


def _by_type(result):
    return {c.type: c for c in result.conflicts}


def test_no_eligible_faculty_conflict():
    case = basic_case(math_faculty=(), lab_faculty=())
    result = _run(case)
    assert result.status == GenerationStatus.INFEASIBLE
    conflicts = _by_type(result)
    assert ConflictType.NO_ELIGIBLE_FACULTY in conflicts
    conflict = conflicts[ConflictType.NO_ELIGIBLE_FACULTY]
    assert conflict.subject in ("MATH", "LABX")
    assert conflict.division == "D1"
    assert any("ssign" in s for s in conflict.suggestions)  # assign faculty
    assert "MATH" in conflict.message or "LABX" in conflict.message


def test_room_capacity_conflict_names_real_numbers():
    case = basic_case(div_students=100, room_capacity=40)
    result = _run(case)
    assert result.status == GenerationStatus.INFEASIBLE
    conflicts = _by_type(result)
    assert ConflictType.ROOM_CAPACITY_CONFLICT in conflicts
    conflict = conflicts[ConflictType.ROOM_CAPACITY_CONFLICT]
    assert conflict.details["division_size"] == 100
    assert conflict.details["required_capacity"] == 100
    assert "100" in conflict.message
    assert any("capacity" in s.lower() for s in conflict.suggestions)


def test_no_suitable_lab_conflict():
    import dataclasses

    case = basic_case()
    lab = case.rooms["L1"]
    case.scope.rooms[lab.id] = dataclasses.replace(lab, is_active=False)
    result = _run(case)
    assert result.status == GenerationStatus.INFEASIBLE
    conflicts = _by_type(result)
    assert ConflictType.NO_ELIGIBLE_ROOM in conflicts
    conflict = conflicts[ConflictType.NO_ELIGIBLE_ROOM]
    assert conflict.subject == "LABX"
    assert "laboratory" in conflict.message
    assert conflict.suggestions, "suggestions must never be empty"


def test_insufficient_period_capacity_conflict():
    case = basic_case(math_per_week=6, lab_per_week=0, days=("MONDAY",), slots_per_day=2)
    result = _run(case)
    assert result.status == GenerationStatus.INFEASIBLE
    conflicts = _by_type(result)
    assert ConflictType.INSUFFICIENT_PERIOD_CAPACITY in conflicts
    conflict = conflicts[ConflictType.INSUFFICIENT_PERIOD_CAPACITY]
    assert conflict.details["sessions_required"] == 6
    assert conflict.details["teaching_periods_available"] == 2
    assert conflict.details["deficit"] == 4


def test_faculty_availability_conflict():
    all_periods = ["MONDAY1", "MONDAY2", "TUESDAY1", "TUESDAY2"]
    # F1 blocked everywhere; F2 only eligible for MATH -> LABX has faculty
    # options but never an available one.
    case = basic_case(unavailable={"F1": all_periods}, lab_faculty=("F1",))
    result = _run(case)
    assert result.status == GenerationStatus.INFEASIBLE
    conflicts = _by_type(result)
    assert ConflictType.FACULTY_AVAILABILITY_CONFLICT in conflicts
    conflict = conflicts[ConflictType.FACULTY_AVAILABILITY_CONFLICT]
    assert conflict.subject == "LABX"
    assert "F1" in conflict.message
    assert any("vailability" in s for s in conflict.suggestions)


def test_resource_contention_when_individually_feasible():
    # Two sessions, two periods, but ONE shared room and ONE shared faculty
    # member available in only ONE period -> jointly infeasible.
    case = basic_case(
        math_per_week=2,
        lab_per_week=0,
        days=("MONDAY",),
        slots_per_day=2,
        math_faculty=("F1",),
        unavailable={"F1": ["MONDAY2"]},
    )
    result = _run(case)
    assert result.status == GenerationStatus.INFEASIBLE
    conflicts = _by_type(result)
    assert ConflictType.RESOURCE_CONTENTION in conflicts
    conflict = conflicts[ConflictType.RESOURCE_CONTENTION]
    assert "F1" in conflict.message
    assert conflict.details["sessions_total"] == 2
    assert conflict.suggestions


def test_explanations_cite_real_data_not_templates():
    case = basic_case(math_faculty=(), lab_faculty=())
    result = _run(case)
    for conflict in result.conflicts:
        assert conflict.message and "{d." not in conflict.message
        assert conflict.suggestions
    assert result.suggestions  # flattened, de-duplicated
    assert len(result.suggestions) == len(set(result.suggestions))


def test_explainer_is_deterministic():
    case = basic_case(div_students=100, room_capacity=40)
    first = [c.message for c in _run(case).conflicts]
    second = [c.message for c in _run(case).conflicts]
    assert first == second


def test_empty_requirements_is_invalid_configuration():
    case = basic_case(math_per_week=0, lab_per_week=0)
    case.scope.requirements.clear()
    result = _run(case)
    assert result.status == GenerationStatus.INFEASIBLE
    assert ConflictType.INVALID_CONFIGURATION in _by_type(result)
