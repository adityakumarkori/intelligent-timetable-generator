"""Shared service helpers — the only data-access pattern in Phase 4.

Design (§15): services use SQLAlchemy directly through these helpers instead
of per-entity repository classes, which would add files without behavior.
Routes stay thin: validate (schemas) -> call service -> return.
"""

from typing import Any, TypeVar
from uuid import UUID

from fastapi import status
from fastapi.exceptions import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.common import PageParams

ModelT = TypeVar("ModelT")


def not_found(resource: str, identifier: Any) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource} '{identifier}' not found",
    )


async def get_or_404(db: AsyncSession, model: type[ModelT], obj_id: UUID, resource: str) -> ModelT:
    obj = await db.get(model, obj_id)
    if obj is None:
        raise not_found(resource, obj_id)
    return obj


async def paginate(db: AsyncSession, stmt, params: PageParams) -> dict:
    """Paginate any SELECT of whole entities. Caller adds filters/ordering."""
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = (
        (
            await db.scalars(
                stmt.offset((params.page - 1) * params.page_size).limit(params.page_size)
            )
        )
        .unique()
        .all()
    )
    return {"items": list(items), "page": params.page, "page_size": params.page_size, "total": total}


def _pg_code(exc: IntegrityError) -> str | None:
    orig = getattr(exc, "orig", None)
    return getattr(orig, "pgcode", None) or getattr(orig, "sqlstate", None)


def translate_integrity(
    exc: IntegrityError,
    unique_messages: dict[str, str] | None = None,
    *,
    delete_resource: str | None = None,
) -> HTTPException:
    """Map PostgreSQL constraint failures to API errors (never leak raw DB errors)."""
    code = _pg_code(exc)
    unique_messages = unique_messages or {}
    if code == "23505":  # unique_violation
        detail = getattr(exc.orig, "diag", None)
        name = getattr(detail, "constraint_name", None) if detail else None
        message = unique_messages.get(name or "", "Resource already exists")
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)
    if code == "23503":  # foreign_key_violation
        if delete_resource:
            return HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete {delete_resource}: it is still referenced by other records",
            )
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Referenced record does not exist or is still in use",
        )
    if code == "23514":  # check_violation
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Value violates a business rule",
        )
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT, detail="Database constraint violated"
    )


async def commit_or_409(
    db: AsyncSession,
    unique_messages: dict[str, str] | None = None,
) -> None:
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise translate_integrity(exc, unique_messages) from None


async def delete_safe(db: AsyncSession, obj: Any, resource: str) -> None:
    """Delete, translating in-use FK failures into 409 instead of 500."""
    await db.delete(obj)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise translate_integrity(exc, delete_resource=resource) from None


def ensure_active(entity: Any, resource: str, identifier: Any) -> None:
    if not getattr(entity, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{resource} '{identifier}' is inactive and cannot be used",
        )
