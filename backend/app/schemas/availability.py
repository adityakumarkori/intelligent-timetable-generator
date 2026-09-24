"""Faculty availability schemas.

Domain rule: a missing row means AVAILABLE — clients only send exceptions.
"""

from datetime import time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AvailabilityStatus, DayOfWeek


class AvailabilityItem(BaseModel):
    period_id: UUID
    status: AvailabilityStatus = AvailabilityStatus.AVAILABLE


class AvailabilityBulkUpdate(BaseModel):
    """Full replacement of one faculty member's availability rows."""

    items: list[AvailabilityItem] = Field(default_factory=list)


class AvailabilityStatusUpdate(BaseModel):
    status: AvailabilityStatus


class PeriodBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    period_order: int
    is_break: bool


class AvailabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    faculty_id: UUID
    period_id: UUID
    status: AvailabilityStatus
    period: PeriodBrief
