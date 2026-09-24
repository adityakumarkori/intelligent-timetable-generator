"""Manual timetable-entry schemas (Phase 6).

 Entry detail uses flat nested objects for display (period/subject/faculty/
 room) with no back-references, so ORM serialization can never recurse.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import RoomType
from app.schemas.timetable import PeriodBrief


class EntryCreate(BaseModel):
    subject_id: UUID
    faculty_id: UUID
    room_id: UUID
    period_id: UUID


class EntryUpdate(BaseModel):
    subject_id: UUID | None = None
    faculty_id: UUID | None = None
    room_id: UUID | None = None
    period_id: UUID | None = None


class SubjectBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str


class FacultyBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_code: str
    name: str


class RoomBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    room_type: RoomType


class TimetableEntryDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    timetable_id: UUID
    period: PeriodBrief
    subject: SubjectBrief
    faculty: FacultyBrief
    room: RoomBrief
