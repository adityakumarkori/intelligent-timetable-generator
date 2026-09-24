"""Division subject requirement service.

Room-override compatibility rule: a preferred room type must not contradict
the subject's own requirement (and lab work needs a LAB room).
"""

from uuid import UUID

from fastapi import status
from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import AcademicSession, Division, DivisionSubjectRequirement, Subject
from app.models.enums import RoomType
from app.schemas.common import PageParams
from app.schemas.requirement import (
    DivisionSubjectRequirementCreate,
    DivisionSubjectRequirementUpdate,
)
from app.services.common import (
    commit_or_409,
    delete_safe,
    ensure_active,
    get_or_404,
    not_found,
    paginate,
)

UNIQUE_MESSAGES = {
    "uq_requirements_division_subject_session": "This subject requirement already exists",
}


async def _require_active(db: AsyncSession, model, obj_id: UUID, label: str):
    obj = await db.get(model, obj_id)
    if obj is None:
        raise not_found(label, obj_id)
    ensure_active(obj, label, obj_id)
    return obj


def check_room_compatible(
    subject: Subject, preferred: RoomType | None, requires_lab: bool
) -> None:
    if preferred is None:
        return
    if subject.required_room_type is not None and preferred != subject.required_room_type:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Preferred room type {preferred.value} conflicts with the subject's "
                f"required room type {subject.required_room_type.value}"
            ),
        )
    if (requires_lab or subject.requires_lab) and preferred != RoomType.LAB:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Lab work requires preferred room type LAB",
        )


def _to_dict(r: DivisionSubjectRequirement) -> dict:
    return {
        "id": r.id,
        "division_id": r.division_id,
        "subject_id": r.subject_id,
        "academic_session_id": r.academic_session_id,
        "required_periods_per_week": r.required_periods_per_week,
        "preferred_room_type": r.preferred_room_type,
        "requires_lab": r.requires_lab,
        "is_active": r.is_active,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
        "subject_code": r.subject.code,
        "division_code": r.division.code,
    }


def _options():
    return (
        joinedload(DivisionSubjectRequirement.subject),
        joinedload(DivisionSubjectRequirement.division),
    )


async def list_requirements(
    db: AsyncSession,
    params: PageParams,
    *,
    division_id: UUID | None = None,
    subject_id: UUID | None = None,
    academic_session_id: UUID | None = None,
    is_active: bool | None = None,
) -> dict:
    stmt = (
        select(DivisionSubjectRequirement)
        .options(*_options())
        .order_by(DivisionSubjectRequirement.created_at)
    )
    if division_id is not None:
        stmt = stmt.where(DivisionSubjectRequirement.division_id == division_id)
    if subject_id is not None:
        stmt = stmt.where(DivisionSubjectRequirement.subject_id == subject_id)
    if academic_session_id is not None:
        stmt = stmt.where(DivisionSubjectRequirement.academic_session_id == academic_session_id)
    if is_active is not None:
        stmt = stmt.where(DivisionSubjectRequirement.is_active == is_active)
    page = await paginate(db, stmt, params)
    page["items"] = [_to_dict(r) for r in page["items"]]
    return page


async def get_requirement(db: AsyncSession, requirement_id: UUID) -> dict:
    stmt = (
        select(DivisionSubjectRequirement)
        .options(*_options())
        .where(DivisionSubjectRequirement.id == requirement_id)
    )
    obj = await db.scalar(stmt)
    if obj is None:
        raise not_found("Subject requirement", requirement_id)
    return _to_dict(obj)


async def create_requirement(db: AsyncSession, data: DivisionSubjectRequirementCreate) -> dict:
    await _require_active(db, Division, data.division_id, "Division")
    subject = await _require_active(db, Subject, data.subject_id, "Subject")
    await _require_active(db, AcademicSession, data.academic_session_id, "Academic session")
    check_room_compatible(subject, data.preferred_room_type, data.requires_lab)

    duplicate = await db.scalar(
        select(DivisionSubjectRequirement).where(
            DivisionSubjectRequirement.division_id == data.division_id,
            DivisionSubjectRequirement.subject_id == data.subject_id,
            DivisionSubjectRequirement.academic_session_id == data.academic_session_id,
        )
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This subject requirement already exists",
        )
    obj = DivisionSubjectRequirement(
        division_id=data.division_id,
        subject_id=data.subject_id,
        academic_session_id=data.academic_session_id,
        required_periods_per_week=data.required_periods_per_week,
        preferred_room_type=data.preferred_room_type,
        requires_lab=data.requires_lab,
        is_active=data.is_active,
    )
    db.add(obj)
    await commit_or_409(db, UNIQUE_MESSAGES)
    return await get_requirement(db, obj.id)


async def update_requirement(
    db: AsyncSession, requirement_id: UUID, data: DivisionSubjectRequirementUpdate
) -> dict:
    obj = await get_or_404(db, DivisionSubjectRequirement, requirement_id, "Subject requirement")
    patch = data.model_dump(exclude_unset=True)
    for field, value in patch.items():
        setattr(obj, field, value)
    await db.flush()
    subject = await db.get(Subject, obj.subject_id)
    check_room_compatible(subject, obj.preferred_room_type, obj.requires_lab)
    await commit_or_409(db, UNIQUE_MESSAGES)
    return await get_requirement(db, obj.id)


async def delete_requirement(db: AsyncSession, requirement_id: UUID) -> None:
    await delete_safe(
        db,
        await get_or_404(db, DivisionSubjectRequirement, requirement_id, "Subject requirement"),
        "subject requirement",
    )
