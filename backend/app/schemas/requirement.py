"""Division subject requirement schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RoomType


class DivisionSubjectRequirementCreate(BaseModel):
    division_id: UUID
    subject_id: UUID
    academic_session_id: UUID
    required_periods_per_week: int = Field(gt=0)
    preferred_room_type: RoomType | None = None
    requires_lab: bool = False
    is_active: bool = True


class DivisionSubjectRequirementUpdate(BaseModel):
    required_periods_per_week: int | None = Field(default=None, gt=0)
    preferred_room_type: RoomType | None = None
    requires_lab: bool | None = None
    is_active: bool | None = None


class DivisionSubjectRequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    division_id: UUID
    subject_id: UUID
    academic_session_id: UUID
    required_periods_per_week: int
    preferred_room_type: RoomType | None
    requires_lab: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Read-only enrichment (flat, no nesting).
    subject_code: str
    division_code: str
