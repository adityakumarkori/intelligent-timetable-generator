"""OR-Tools CP-SAT solver invocation (thin wrapper, no domain logic)."""

import time
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from app.timetable_engine.constraints import VarKey
from app.timetable_engine.models import SolverStatus


@dataclass(frozen=True)
class SolverOptions:
    time_limit_seconds: float = 30.0
    num_workers: int = 4
    random_seed: int = 42
    log_search_progress: bool = False


@dataclass
class SolverOutcome:
    status: SolverStatus
    objective_value: int | None
    wall_time_s: float
    # Decision-variable values, only populated for OPTIMAL/FEASIBLE.
    values: dict[VarKey, bool] = field(default_factory=dict)


_STATUS_MAP = {
    cp_model.OPTIMAL: SolverStatus.OPTIMAL,
    cp_model.FEASIBLE: SolverStatus.FEASIBLE,
    cp_model.INFEASIBLE: SolverStatus.INFEASIBLE,
    cp_model.UNKNOWN: SolverStatus.UNKNOWN,
}


def solve(
    model: cp_model.CpModel,
    var_index: dict[VarKey, cp_model.BoolVarT],
    options: SolverOptions,
    *,
    has_objective: bool = True,
) -> SolverOutcome:
    """Run CP-SAT synchronously (callers push this onto a worker thread)."""
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = options.time_limit_seconds
    solver.parameters.num_search_workers = options.num_workers
    solver.parameters.random_seed = options.random_seed
    solver.parameters.log_search_progress = options.log_search_progress

    started = time.perf_counter()
    raw_status = solver.Solve(model)
    elapsed = time.perf_counter() - started

    status = _STATUS_MAP[raw_status]
    values: dict[VarKey, bool] = {}
    objective: int | None = None
    if status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE):
        values = {key: bool(solver.Value(var)) for key, var in var_index.items()}
        objective = None
        if has_objective:
            try:
                objective = int(solver.ObjectiveValue())
            except RuntimeError:
                objective = None  # feasibility-only model has no objective
    return SolverOutcome(
        status=status, objective_value=objective, wall_time_s=elapsed, values=values
    )
