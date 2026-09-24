"""Room schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RoomType


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    room_type: RoomType
    capacity: int = Field(gt=0)
    building: str | None = Field(default=None, max_length=100)
    is_active: bool = True


class RoomUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    room_type: RoomType | None = None
    capacity: int | None = Field(default=None, gt=0)
    building: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None


class RoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    room_type: RoomType
    capacity: int
    building: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
