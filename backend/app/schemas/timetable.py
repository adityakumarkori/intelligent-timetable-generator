"""Timetable read schemas (Phase 4 exposes retrieval only — no generation)."""

from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import DayOfWeek, TimetableStatus


class PeriodBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    period_order: int
    is_break: bool


class TimetableEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    timetable_id: UUID
    division_code: str
    subject_id: UUID
    subject_code: str
    subject_name: str
    faculty_id: UUID
    faculty_name: str
    room_id: UUID
    room_name: str
    period: PeriodBrief


class TimetableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    academic_session_id: UUID
    session_name: str
    division_id: UUID
    division_code: str
    status: TimetableStatus
    version: int
    generated_at: datetime | None
    published_at: datetime | None
    entry_count: int
    created_at: datetime
    updated_at: datetime


class TimetableDetailResponse(TimetableResponse):
    entries: list[TimetableEntryResponse]
