"""Timetable generation endpoints (Phase 5: OR-Tools CP-SAT underneath).

 ADMIN/SUPER_ADMIN only — faculty and students use the read endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.generation import (
    CloneTimetableResponse,
    GenerateTimetableRequest,
    GenerationFailureResponse,
    GenerationResultResponse,
    GenerationSuccessResponse,
    ValidateTimetableResponse,
)
from app.schemas.timetable import TimetableDetailResponse
from app.services import generation_service, timetable_write_service

router = APIRouter(tags=["generation"])

manage = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)


@router.post(
    "/generate",
    summary="Generate a timetable for one division (CP-SAT + validation)",
    description=(
        "Builds scheduling sessions from active requirements, solves with OR-Tools "
        "CP-SAT under hard constraints with soft-constraint optimization, validates "
        "the result independently, and persists a new GENERATED version. "
        "Returns 422 with structured conflicts when infeasible."
    ),
    responses={
        201: {"model": GenerationSuccessResponse},
        422: {"model": GenerationFailureResponse},
    },
)
async def generate_timetable(
    request: GenerateTimetableRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    body, http_status = await generation_service.generate_timetable(
        db, request, created_by=user.id
    )
    response.status_code = http_status
    return body


@router.post(
    "/{timetable_id}/validate",
    response_model=ValidateTimetableResponse,
    summary="Independently re-validate a timetable (promotes GENERATED to VALID)",
)
async def validate_timetable(
    timetable_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await generation_service.validate_timetable(db, timetable_id)


@router.get(
    "/{timetable_id}/generation-result",
    response_model=GenerationResultResponse,
    summary="Result view: status plus a live validation report",
)
async def generation_result(
    timetable_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await generation_service.generation_result(db, user, timetable_id)


@router.post(
    "/{timetable_id}/publish",
    response_model=TimetableDetailResponse,
    summary="Publish a VALID timetable (archives replaced versions atomically)",
    description=(
        "Validates inline (GENERATED/DRAFT that pass are publishable directly), "
        "rejects clashes with other divisions' published timetables, archives "
        "superseded versions of the same division, then publishes — all in one "
        "transaction. Invalid timetables are rejected with 422 and unchanged."
    ),
    responses={422: {"description": "Timetable invalid or clashing; unchanged"}},
)
async def publish_timetable(
    timetable_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
    if_unmodified_since: str | None = Header(default=None),
):
    return await timetable_write_service.publish_timetable(
        db, user, timetable_id, if_unmodified_since
    )


@router.post(
    "/{timetable_id}/archive",
    response_model=TimetableDetailResponse,
    summary="Retire a timetable to ARCHIVED history",
)
async def archive_timetable(
    timetable_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await timetable_write_service.archive_timetable(db, user, timetable_id)


@router.post(
    "/{timetable_id}/clone",
    response_model=CloneTimetableResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Copy any timetable into a new editable DRAFT version",
    description=(
        "New version number, new entry IDs, DRAFT status, no publication state. "
        "The source timetable is never modified. The clone is validated inline "
        "and the report is included in the response."
    ),
)
async def clone_timetable(
    timetable_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await timetable_write_service.clone_timetable(db, user, timetable_id)
