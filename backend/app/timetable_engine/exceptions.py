"""Engine-level exceptions (transport-agnostic; services map them to HTTP)."""


class EngineError(Exception):
    """Base class for timetable engine failures."""


class ConfigurationError(EngineError):
    """Scheduling configuration is missing or contradictory.

    Raised when generation cannot even be attempted (unknown session/division,
    no active requirements, invalid weekly loads).
    """


class SolveError(EngineError):
    """The solver run itself failed unexpectedly (not mere infeasibility)."""


class MappingError(EngineError):
    """A solver solution could not be mapped back to timetable entries."""


class ValidationError(EngineError):
    """A generated timetable failed independent validation before persistence."""
