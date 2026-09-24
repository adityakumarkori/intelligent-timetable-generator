"""Room service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Room
from app.models.enums import RoomType
from app.schemas.common import PageParams
from app.schemas.room import RoomCreate, RoomUpdate
from app.services.common import commit_or_409, delete_safe, get_or_404, paginate

UNIQUE_MESSAGES = {
    "rooms_name_key": "Room name already exists",
    "ix_rooms_name": "Room name already exists",
}


async def list_rooms(
    db: AsyncSession,
    params: PageParams,
    *,
    q: str | None = None,
    room_type: RoomType | None = None,
    min_capacity: int | None = None,
    is_active: bool | None = None,
) -> dict:
    stmt = select(Room).order_by(Room.name)
    if q:
        stmt = stmt.where(Room.name.ilike(f"%{q.strip()}%"))
    if room_type is not None:
        stmt = stmt.where(Room.room_type == room_type)
    if min_capacity is not None:
        stmt = stmt.where(Room.capacity >= min_capacity)
    if is_active is not None:
        stmt = stmt.where(Room.is_active == is_active)
    return await paginate(db, stmt, params)


async def get_room(db: AsyncSession, room_id: UUID) -> Room:
    return await get_or_404(db, Room, room_id, "Room")


async def create_room(db: AsyncSession, data: RoomCreate) -> Room:
    obj = Room(
        name=data.name.strip(),
        room_type=data.room_type,
        capacity=data.capacity,
        building=data.building.strip() if data.building else None,
        is_active=data.is_active,
    )
    db.add(obj)
    await commit_or_409(db, UNIQUE_MESSAGES)
    await db.refresh(obj)
    return obj


async def update_room(db: AsyncSession, room_id: UUID, data: RoomUpdate) -> Room:
    obj = await get_room(db, room_id)
    patch = data.model_dump(exclude_unset=True)
    if isinstance(patch.get("name"), str):
        patch["name"] = patch["name"].strip()
    if "building" in patch and patch["building"] is not None:
        patch["building"] = patch["building"].strip() or None
    for field, value in patch.items():
        setattr(obj, field, value)
    await commit_or_409(db, UNIQUE_MESSAGES)
    await db.refresh(obj)
    return obj


async def delete_room(db: AsyncSession, room_id: UUID) -> None:
    await delete_safe(db, await get_room(db, room_id), "room")
