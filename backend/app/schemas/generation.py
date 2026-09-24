"""Generation API schemas (Phase 5).

 Success and infeasibility share a status discriminator; HTTP codes: 201 on
 SUCCESS, 422 when the configuration is provably infeasible, 500 on solver
 or persistence failure (consistent {"detail"} error schema).
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TimetableStatus


class GenerationOptions(BaseModel):
    optimize: bool = Field(
        default=True,
        description="False runs feasibility-only (faster, no soft-constraint ranking)",
    )
    time_limit_seconds: float = Field(default=30.0, ge=1, le=300)
    num_workers: int | None = Field(
        default=None, ge=1, le=32,
        description="Defaults to server configuration when omitted",
    )
    random_seed: int | None = Field(
        default=None,
        description="Defaults to server configuration; fixes CP-SAT search for reproducibility",
    )


class GenerateTimetableRequest(BaseModel):
    """Single-division scope today; structured so multi-division scopes fit later."""

    academic_session_id: UUID
    division_id: UUID
    options: GenerationOptions = Field(default_factory=GenerationOptions)


class ConflictSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: str
    severity: str
    message: str
    subject: str | None = None
    division: str | None = None
    details: dict = Field(default_factory=dict)
    suggestions: list[str] = Field(default_factory=list)


class GenerationSuccessResponse(BaseModel):
    status: str = "SUCCESS"
    timetable_id: UUID
    solver_status: str
    objective_score: int | None = None
    generation_duration_ms: int = 0
    warnings: list[str] = Field(default_factory=list)


class GenerationFailureResponse(BaseModel):
    status: str  # INFEASIBLE
    solver_status: str
    conflicts: list[ConflictSchema] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    generation_duration_ms: int = 0


class ViolationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: str
    message: str
    details: dict = Field(default_factory=dict)


class ValidateTimetableResponse(BaseModel):
    timetable_id: UUID
    valid: bool
    violations: list[ViolationSchema] = Field(default_factory=list)
    # Phase 6 additions (all optional-shaped: existing clients keep working).
    status: str = "UNKNOWN"
    errors: list[ViolationSchema] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    score: int | None = None


class GenerationResultResponse(BaseModel):
    timetable_id: UUID
    status: TimetableStatus
    version: int
    generated_at: str | None = None
    entry_count: int = 0
    valid: bool
    violations: list[ViolationSchema] = Field(default_factory=list)


class CloneTimetableResponse(BaseModel):
    id: UUID
    academic_session_id: UUID
    division_id: UUID
    status: TimetableStatus
    version: int
    entry_count: int
    valid: bool
    violations: list[ViolationSchema] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
