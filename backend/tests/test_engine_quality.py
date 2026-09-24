"""Quality evaluation tests: S1–S5 scoring mirrors the solver objective."""

from app.timetable_engine.models import GeneratedEntry
from app.timetable_engine.quality import evaluate_quality
from tests.engine_helpers import basic_case, solve_case


def _entry(case, subject_code, period_key, faculty_name="F1", room_key=None):
    subject = case.subjects[subject_code]
    default_room = "L1" if subject_code == "LABX" else "R1"
    return GeneratedEntry(
        session_index=0,
        division_id=case.divisions["D1"].id,
        subject_id=subject.id,
        period_id=case.periods[period_key].id,
        faculty_id=case.faculty[faculty_name].id,
        room_id=case.rooms[room_key or default_room].id,
    )


def test_empty_timetable_scores_zero_without_warnings():
    case = basic_case()
    report = evaluate_quality([], case.scope)
    assert report.score == 0
    assert report.warnings == []


def test_single_entry_score_matches_formula():
    # S1: 1 distinct subject-day (+10). S5: peak 1 (-2). Nothing else.
    case = basic_case()
    report = evaluate_quality([_entry(case, "MATH", "MONDAY1")], case.scope)
    assert report.score == 10 - 2
    assert report.details["distinct_subject_days"] == 1
    assert report.warnings == []


def test_gap_warning_names_division_and_day():
    case = basic_case(days=("MONDAY",), slots_per_day=3)
    entries = [_entry(case, "MATH", "MONDAY1"), _entry(case, "MATH", "MONDAY3")]
    report = evaluate_quality(entries, case.scope)
    assert report.details["student_gaps"] == 1
    assert any("D1" in w and "Monday" in w for w in report.warnings)
    # 1 subject-day*10 - 1 gap*5 - peak 2*2 = 1 (no consecutive pairs, no repeats).
    assert report.score == 10 - 5 - 4


def test_repetition_and_consecutive_warnings():
    case = basic_case()
    entries = [_entry(case, "MATH", "MONDAY1"), _entry(case, "MATH", "MONDAY2")]
    report = evaluate_quality(entries, case.scope)
    assert report.details["adjacent_repeats"] == 1
    assert report.details["consecutive_faculty_pairs"] == 1
    assert any("back-to-back" in w for w in report.warnings)


def test_consecutive_run_warning_at_three():
    case = basic_case(days=("MONDAY",), slots_per_day=3)
    entries = [
        _entry(case, "MATH", "MONDAY1"),
        _entry(case, "MATH", "MONDAY2"),
        _entry(case, "MATH", "MONDAY3"),
    ]
    report = evaluate_quality(entries, case.scope)
    assert any("3 consecutive" in w and "F1" in w for w in report.warnings)


def test_solved_timetable_quality_matches_solver_objective():
    # Same weights, same formula: solver optimum must equal quality score.
    case = basic_case(math_per_week=3, lab_per_week=1)
    result = solve_case(case)
    assert result.status.value == "SUCCESS"
    report = evaluate_quality(result.entries, case.scope)
    assert report.score == result.objective_score
