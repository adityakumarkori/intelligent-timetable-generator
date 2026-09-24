"""Faculty assignment schemas (faculty x subject x division x session)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FacultyAssignmentCreate(BaseModel):
    faculty_id: UUID
    subject_id: UUID
    division_id: UUID
    academic_session_id: UUID
    is_active: bool = True


class FacultyAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    faculty_id: UUID
    subject_id: UUID
    division_id: UUID
    academic_session_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Read-only enrichment (flat, no nesting).
    faculty_name: str
    subject_code: str
    division_code: str
