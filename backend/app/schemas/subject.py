"""Subject schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RoomType, SubjectType


class SubjectCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=150)
    subject_type: SubjectType = SubjectType.LECTURE
    required_periods_per_week: int = Field(gt=0)
    required_room_type: RoomType | None = None
    requires_lab: bool = False
    is_active: bool = True


class SubjectUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=20)
    name: str | None = Field(default=None, min_length=1, max_length=150)
    subject_type: SubjectType | None = None
    required_periods_per_week: int | None = Field(default=None, gt=0)
    required_room_type: RoomType | None = None
    requires_lab: bool | None = None
    is_active: bool | None = None


class SubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    subject_type: SubjectType
    required_periods_per_week: int
    required_room_type: RoomType | None
    requires_lab: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
