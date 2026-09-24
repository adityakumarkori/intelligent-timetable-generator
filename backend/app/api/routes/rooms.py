"""Room endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models import User
from app.models.enums import RoomType, UserRole
from app.schemas.common import Page, PageParams
from app.schemas.room import RoomCreate, RoomResponse, RoomUpdate
from app.services import room_service

router = APIRouter(tags=["rooms"])

manage = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)
read = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.FACULTY, UserRole.STUDENT)


@router.get("", response_model=Page[RoomResponse], summary="List rooms")
async def list_rooms(
    params: PageParams = Depends(),
    q: str | None = Query(default=None, description="Search room name"),
    room_type: RoomType | None = None,
    min_capacity: int | None = Query(default=None, ge=1, description="Minimum capacity"),
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(read),
):
    return await room_service.list_rooms(
        db, params, q=q, room_type=room_type, min_capacity=min_capacity, is_active=is_active
    )


@router.get("/{room_id}", response_model=RoomResponse, summary="Get a room")
async def get_room(
    room_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(read),
):
    return await room_service.get_room(db, room_id)


@router.post(
    "",
    response_model=RoomResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a room",
)
async def create_room(
    data: RoomCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await room_service.create_room(db, data)


@router.patch("/{room_id}", response_model=RoomResponse, summary="Update a room")
async def update_room(
    room_id: UUID,
    data: RoomUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await room_service.update_room(db, room_id, data)


@router.delete(
    "/{room_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a room (blocked while in use)",
)
async def delete_room(
    room_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    await room_service.delete_room(db, room_id)
