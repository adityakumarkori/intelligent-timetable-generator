"""Division schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DivisionCreate(BaseModel):
    department_id: UUID
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=20)
    student_count: int = Field(default=0, ge=0)
    is_active: bool = True


class DivisionUpdate(BaseModel):
    department_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    code: str | None = Field(default=None, min_length=1, max_length=20)
    student_count: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class DivisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    department_id: UUID
    name: str
    code: str
    student_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
