"""Faculty schemas — never include user credentials or password hashes."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FacultyCreate(BaseModel):
    user_id: UUID | None = None
    employee_code: str = Field(min_length=1, max_length=30)
    department_id: UUID
    name: str = Field(min_length=1, max_length=120)
    is_active: bool = True


class FacultyUpdate(BaseModel):
    user_id: UUID | None = None
    employee_code: str | None = Field(default=None, min_length=1, max_length=30)
    department_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_active: bool | None = None


class FacultyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None
    employee_code: str
    department_id: UUID
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
