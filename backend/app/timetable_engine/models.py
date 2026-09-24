"""Engine domain model — the application's own scheduling representation.

OR-Tools only sees Boolean variables built from these structures; every rule
about what is valid lives here and in the builder/validator modules, never
inside the solver.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from enum import Enum
from uuid import UUID

from app.models.enums import DayOfWeek, RoomType


class GenerationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"  # defined for API compatibility; engine never persists partials
    INFEASIBLE = "INFEASIBLE"
    FAILED = "FAILED"


class SolverStatus(str, Enum):
    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    UNKNOWN = "UNKNOWN"


class ConflictType(str, Enum):
    NO_ELIGIBLE_FACULTY = "NO_ELIGIBLE_FACULTY"
    NO_ELIGIBLE_ROOM = "NO_ELIGIBLE_ROOM"
    ROOM_CAPACITY_CONFLICT = "ROOM_CAPACITY_CONFLICT"
    ROOM_TYPE_CONFLICT = "ROOM_TYPE_CONFLICT"
    NO_AVAILABLE_PERIOD = "NO_AVAILABLE_PERIOD"
    FACULTY_AVAILABILITY_CONFLICT = "FACULTY_AVAILABILITY_CONFLICT"
    INSUFFICIENT_PERIOD_CAPACITY = "INSUFFICIENT_PERIOD_CAPACITY"
    RESOURCE_CONTENTION = "RESOURCE_CONTENTION"
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"
    # Validator-side violation types (single-timetable invariants).
    WEEKLY_LOAD_MISMATCH = "WEEKLY_LOAD_MISMATCH"
    DIVISION_CONFLICT = "DIVISION_CONFLICT"
    FACULTY_CONFLICT = "FACULTY_CONFLICT"
    ROOM_CONFLICT = "ROOM_CONFLICT"
    FACULTY_UNAVAILABLE = "FACULTY_UNAVAILABLE"
    ROOM_CAPACITY = "ROOM_CAPACITY"
    ROOM_TYPE = "ROOM_TYPE"
    INVALID_ASSIGNMENT = "INVALID_ASSIGNMENT"
    BREAK_PERIOD_USED = "BREAK_PERIOD_USED"
    INACTIVE_ENTITY = "INACTIVE_ENTITY"


class ConflictSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


@dataclass(frozen=True)
class PeriodSlot:
    """One schedulable (or break) slot. Only active, non-break slots get candidates."""

    id: UUID
    day: DayOfWeek
    order: int
    start: time
    end: time
    is_break: bool
    is_active: bool

    @property
    def teachable(self) -> bool:
        return self.is_active and not self.is_break


@dataclass(frozen=True)
class FacultyInfo:
    id: UUID
    name: str
    is_active: bool
    unavailable_period_ids: frozenset[UUID] = frozenset()


@dataclass(frozen=True)
class RoomInfo:
    id: UUID
    name: str
    room_type: RoomType
    capacity: int
    is_active: bool


@dataclass(frozen=True)
class SubjectInfo:
    id: UUID
    code: str
    name: str
    required_room_type: RoomType | None
    requires_lab: bool
    is_active: bool


@dataclass(frozen=True)
class DivisionInfo:
    id: UUID
    code: str
    student_count: int
    is_active: bool


@dataclass(frozen=True)
class RequirementInfo:
    """One DivisionSubjectRequirement with resolved relations."""

    id: UUID
    division_id: UUID
    subject: SubjectInfo
    periods_per_week: int
    preferred_room_type: RoomType | None
    requires_lab: bool
    eligible_faculty_ids: tuple[UUID, ...]


@dataclass(frozen=True)
class AssignmentInfo:
    """One FacultyAssignment row (flagged, so the validator can spot deactivation)."""

    faculty_id: UUID
    subject_id: UUID
    division_id: UUID
    session_id: UUID
    is_active: bool


@dataclass(frozen=True)
class SessionSlot:
    """One schedulable session instance (e.g. Mathematics-3-of-5).

    Immutable; never persisted as a database row.
    """

    index: int  # position in the deterministic global session order
    requirement_id: UUID
    division_id: UUID
    subject_id: UUID
    subject_code: str
    session_number: int  # 1-based within its requirement
    sessions_total: int
    eligible_faculty_ids: tuple[UUID, ...]
    required_capacity: int
    required_room_type: RoomType | None  # effective (override ?? subject)
    requires_lab: bool  # effective (requirement OR subject)


@dataclass(frozen=True)
class Candidate:
    """One legal (session, period, faculty, room) combination.

    Legality here covers the pre-filterable hard constraints H5–H10:
    availability, capacity, room type/lab, assignment, break/active flags.
    H1–H4 (exact-once + per-period caps) become CP-SAT constraints; H11
    (weekly load) follows from H1 plus session expansion, and everything is
    re-checked by the independent validator.
    """

    session_index: int
    period_id: UUID
    faculty_id: UUID
    room_id: UUID


@dataclass
class ScopeData:
    """Everything the solver/validator needs, loaded once, in memory."""

    session_id: UUID
    session_name: str
    divisions: dict[UUID, DivisionInfo]
    periods: dict[UUID, PeriodSlot]
    teaching_period_ids: tuple[UUID, ...]  # active, non-break, deterministic order
    rooms: dict[UUID, RoomInfo]
    faculty: dict[UUID, FacultyInfo]
    subjects: dict[UUID, SubjectInfo]
    requirements: list[RequirementInfo]
    assignments: list[AssignmentInfo]
    warnings: list[str] = field(default_factory=list)

    @property
    def division_ids(self) -> tuple[UUID, ...]:
        return tuple(sorted(self.divisions, key=lambda d: self.divisions[d].code))


@dataclass(frozen=True)
class GeneratedEntry:
    session_index: int
    division_id: UUID
    subject_id: UUID
    period_id: UUID
    faculty_id: UUID
    room_id: UUID


@dataclass
class Conflict:
    type: ConflictType
    severity: ConflictSeverity
    message: str
    subject: str | None = None
    division: str | None = None
    details: dict = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class Violation:
    type: ConflictType
    message: str
    details: dict = field(default_factory=dict)


@dataclass
class ValidationResult:
    valid: bool
    violations: list[Violation] = field(default_factory=list)


@dataclass
class GenerationResult:
    status: GenerationStatus
    solver_status: SolverStatus
    timetable_id: UUID | None = None
    entries: list[GeneratedEntry] = field(default_factory=list)
    objective_score: int | None = None
    generation_duration_ms: int = 0
    conflicts: list[Conflict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def suggestions(self) -> list[str]:
        seen: list[str] = []
        for conflict in self.conflicts:
            for suggestion in conflict.suggestions:
                if suggestion not in seen:
                    seen.append(suggestion)
        return seen
