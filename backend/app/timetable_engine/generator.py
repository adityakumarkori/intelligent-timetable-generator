"""End-to-end generation orchestration (no HTTP, no persistence).

 Flow: load scope → expand sessions → build candidates → early-exit on
 provable conflicts → CP-SAT solve → map → independent validate.
 Persistence happens in the service layer, only for validated SUCCESS.
"""

import logging
import time
from uuid import UUID

from ortools.sat.python import cp_model
from starlette.concurrency import run_in_threadpool

from app.timetable_engine.candidate_builder import build_candidates
from app.timetable_engine.conflict_detector import (
    detect_contention_conflicts,
    detect_pre_solve_conflicts,
    tight_session_warnings,
)
from app.timetable_engine.conflict_explainer import explain_conflicts
from app.timetable_engine.constraints import add_hard_constraints
from app.timetable_engine.data_loader import load_scope_data
from app.timetable_engine.exceptions import ConfigurationError, MappingError
from app.timetable_engine.models import (
    Conflict,
    ConflictSeverity,
    ConflictType,
    GenerationResult,
    GenerationStatus,
    ScopeData,
    SolverStatus,
)
from app.timetable_engine.objectives import ObjectiveWeights, add_objective
from app.timetable_engine.session_builder import build_sessions
from app.timetable_engine.solution_mapper import map_solution
from app.timetable_engine.solver import SolverOptions, solve
from app.timetable_engine.validator import validate_entries

logger = logging.getLogger("timetable_engine")


def _invalid_config(message: str) -> GenerationResult:
    conflict = Conflict(
        type=ConflictType.INVALID_CONFIGURATION,
        severity=ConflictSeverity.ERROR,
        message="",
        details={"reason": message},
    )
    explain_conflicts([conflict])
    return GenerationResult(
        status=GenerationStatus.INFEASIBLE,
        solver_status=SolverStatus.UNKNOWN,
        conflicts=[conflict],
    )


def generate_from_scope(
    scope: ScopeData,
    solver_options: SolverOptions | None = None,
    *,
    optimize: bool = True,
    weights: ObjectiveWeights | None = None,
) -> GenerationResult:
    """Run the full pipeline on loaded scope data (synchronous, CPU-bound)."""
    solver_options = solver_options or SolverOptions()
    started = time.perf_counter()

    try:
        sessions = build_sessions(scope)
    except ConfigurationError as exc:
        return _invalid_config(str(exc))

    build = build_candidates(scope, sessions)
    logger.info(
        "generation_started sessions=%d candidates=%d periods=%d",
        len(sessions),
        len(build.candidates),
        len(scope.teaching_period_ids),
    )

    pre_conflicts = detect_pre_solve_conflicts(scope, sessions, build)
    if pre_conflicts:
        explain_conflicts(pre_conflicts)
        logger.info("generation_infeasible reason=pre_solve conflicts=%d", len(pre_conflicts))
        return GenerationResult(
            status=GenerationStatus.INFEASIBLE,
            solver_status=SolverStatus.UNKNOWN,
            conflicts=pre_conflicts,
            warnings=list(scope.warnings),
            generation_duration_ms=int((time.perf_counter() - started) * 1000),
        )

    warnings = list(scope.warnings)
    warnings.extend(tight_session_warnings(sessions, build))

    model = cp_model.CpModel()
    var_index, constraint_report = add_hard_constraints(model, sessions, build.candidates)
    objective_report = None
    if optimize:
        objective_report = add_objective(model, scope, sessions, var_index, weights)
    logger.info(
        "model_built variables=%d constraints=%d objective=%s",
        len(var_index),
        constraint_report.total,
        "on" if optimize else "off",
    )

    outcome = solve(model, var_index, solver_options, has_objective=optimize)
    logger.info(
        "solver_finished status=%s objective=%s wall_time=%.2fs",
        outcome.status.value,
        outcome.objective_value,
        outcome.wall_time_s,
    )

    if outcome.status == SolverStatus.INFEASIBLE:
        contention = detect_contention_conflicts(scope, sessions, build)
        explain_conflicts(contention)
        return GenerationResult(
            status=GenerationStatus.INFEASIBLE,
            solver_status=outcome.status,
            conflicts=contention,
            warnings=warnings,
            generation_duration_ms=int((time.perf_counter() - started) * 1000),
        )

    if outcome.status == SolverStatus.UNKNOWN:
        return GenerationResult(
            status=GenerationStatus.FAILED,
            solver_status=outcome.status,
            warnings=warnings
            + [
                f"Solver stopped after {outcome.wall_time_s:.1f}s without a solution. "
                "Raise the time limit and try again."
            ],
            generation_duration_ms=int((time.perf_counter() - started) * 1000),
        )

    try:
        entries = map_solution(sessions, build.candidates, outcome.values)
    except MappingError as exc:
        return GenerationResult(
            status=GenerationStatus.FAILED,
            solver_status=outcome.status,
            warnings=warnings + [f"Solution mapping failed: {exc}"],
            generation_duration_ms=int((time.perf_counter() - started) * 1000),
        )

    validation = validate_entries(entries, scope)
    logger.info(
        "validation_finished valid=%s violations=%d",
        validation.valid,
        len(validation.violations),
    )
    if not validation.valid:
        details = "; ".join(v.message for v in validation.violations[:5])
        return GenerationResult(
            status=GenerationStatus.FAILED,
            solver_status=outcome.status,
            warnings=warnings + [f"Generated timetable failed validation: {details}"],
            generation_duration_ms=int((time.perf_counter() - started) * 1000),
        )

    return GenerationResult(
        status=GenerationStatus.SUCCESS,
        solver_status=outcome.status,
        entries=entries,
        objective_score=outcome.objective_value,
        conflicts=[],
        warnings=warnings,
        generation_duration_ms=int((time.perf_counter() - started) * 1000),
    )


async def run_generation(
    db,
    session_id: UUID,
    division_ids: list[UUID],
    solver_options: SolverOptions | None = None,
    *,
    optimize: bool = True,
    weights: ObjectiveWeights | None = None,
) -> GenerationResult:
    """Load scope asynchronously, then solve off the event loop."""
    try:
        scope = await load_scope_data(db, session_id, division_ids)
    except ConfigurationError as exc:
        return _invalid_config(str(exc))
    return await run_in_threadpool(
        generate_from_scope, scope, solver_options, optimize=optimize, weights=weights
    )
