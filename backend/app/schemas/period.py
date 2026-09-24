"""Period schemas."""

from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import DayOfWeek


class PeriodCreate(BaseModel):
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    period_order: int = Field(ge=1)
    is_break: bool = False
    is_active: bool = True

    @model_validator(mode="after")
    def _check_times(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class PeriodUpdate(BaseModel):
    day_of_week: DayOfWeek | None = None
    start_time: time | None = None
    end_time: time | None = None
    period_order: int | None = Field(default=None, ge=1)
    is_break: bool | None = None
    is_active: bool | None = None


class PeriodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    period_order: int
    is_break: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
