"""Model registry — importing this module registers every entity on Base.metadata."""

from app.models.academic import (  # noqa: F401
    AcademicSession,
    Department,
    Division,
    Faculty,
    Period,
    Room,
    Subject,
)
from app.models.base import Base  # noqa: F401
from app.models.scheduling import (  # noqa: F401
    DivisionSubjectRequirement,
    FacultyAssignment,
    FacultyAvailability,
)
from app.models.timetable import Timetable, TimetableEntry  # noqa: F401
from app.models.user import User  # noqa: F401

__all__ = [
    "AcademicSession",
    "Base",
    "Department",
    "Division",
    "DivisionSubjectRequirement",
    "Faculty",
    "FacultyAssignment",
    "FacultyAvailability",
    "Period",
    "Room",
    "Subject",
    "Timetable",
    "TimetableEntry",
    "User",
]
