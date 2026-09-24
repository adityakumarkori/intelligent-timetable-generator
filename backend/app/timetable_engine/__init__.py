"""Intelligent timetable generation engine (OR-Tools CP-SAT underneath).

 Layered pipeline — OR-Tools is the constraint/optimization solver, while the
 application owns the domain model, constraint construction, validation, and
 conflict explanation:

 API -> Timetable Service -> generator.run_generation
     -> data_loader -> session_builder -> candidate_builder
     -> constraints + objectives -> solver (CP-SAT) -> solution_mapper
     -> validator; on infeasibility -> conflict_detector + conflict_explainer.
"""

from app.timetable_engine.generator import generate_from_scope, run_generation  # noqa: F401
from app.timetable_engine.candidate_builder import build_candidates  # noqa: F401
from app.timetable_engine.conflict_detector import (  # noqa: F401
    detect_contention_conflicts,
    detect_pre_solve_conflicts,
)
from app.timetable_engine.conflict_explainer import explain_conflicts  # noqa: F401
from app.timetable_engine.constraints import add_hard_constraints  # noqa: F401
from app.timetable_engine.data_loader import load_scope_data  # noqa: F401
from app.timetable_engine.exceptions import (  # noqa: F401
    ConfigurationError,
    EngineError,
    MappingError,
    SolveError,
    ValidationError,
)
from app.timetable_engine.models import (  # noqa: F401
    Candidate,
    Conflict,
    ConflictSeverity,
    ConflictType,
    GeneratedEntry,
    GenerationResult,
    GenerationStatus,
    ScopeData,
    SessionSlot,
    SolverStatus,
    ValidationResult,
    Violation,
)
from app.timetable_engine.objectives import ObjectiveWeights, add_objective  # noqa: F401
from app.timetable_engine.session_builder import build_sessions  # noqa: F401
from app.timetable_engine.solution_mapper import map_solution  # noqa: F401
from app.timetable_engine.solver import SolverOptions, SolverOutcome, solve  # noqa: F401
from app.timetable_engine.validator import validate_entries  # noqa: F401
