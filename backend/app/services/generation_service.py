"""Timetable generation service: engine orchestration + transactional persistence.

 Generate → validate (inside engine) → persist only if valid. A failed
 persist rolls back fully: the database never holds a partial timetable.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import status
from fastapi.exceptions import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AcademicSession, Division, Timetable, TimetableEntry, User
from app.models.enums import TimetableStatus
from app.schemas.generation import GenerateTimetableRequest
from app.services import timetable_service
from app.services.common import get_or_404
from app.timetable_engine import (
    GenerationStatus,
    GeneratedEntry,
    load_scope_data,
    run_generation,
)
from app.timetable_engine.exceptions import ConfigurationError
from app.timetable_engine.models import ValidationResult
from app.timetable_engine.quality import evaluate_quality
from app.timetable_engine.solver import SolverOptions
from app.timetable_engine.validator import validate_entries


def _conflict_to_dict(conflict) -> dict:
    return {
        "type": conflict.type.value,
        "severity": conflict.severity.value,
        "message": conflict.message,
        "subject": conflict.subject,
        "division": conflict.division,
        "details": conflict.details,
        "suggestions": conflict.suggestions,
    }


def _violation_to_dict(violation) -> dict:
    return {
        "type": violation.type.value,
        "message": violation.message,
        "details": violation.details,
    }


def _solver_options(request: GenerateTimetableRequest) -> SolverOptions:
    opts = request.options
    return SolverOptions(
        time_limit_seconds=opts.time_limit_seconds
        if opts.time_limit_seconds
        else settings.TIMETABLE_SOLVER_TIME_LIMIT_SECONDS,
        num_workers=opts.num_workers or settings.TIMETABLE_SOLVER_NUM_WORKERS,
        random_seed=opts.random_seed
        if opts.random_seed is not None
        else settings.TIMETABLE_SOLVER_RANDOM_SEED,
    )


async def generate_timetable(
    db: AsyncSession, request: GenerateTimetableRequest, *, created_by: UUID | None = None
) -> tuple[dict, int]:
    """Run generation; persist only validated SUCCESS. Returns (body, http_status)."""
    await get_or_404(db, AcademicSession, request.academic_session_id, "Academic session")
    await get_or_404(db, Division, request.division_id, "Division")

    result = await run_generation(
        db,
        request.academic_session_id,
        [request.division_id],
        _solver_options(request),
        optimize=request.options.optimize,
    )

    if result.status == GenerationStatus.INFEASIBLE:
        return (
            {
                "status": result.status.value,
                "solver_status": result.solver_status.value,
                "conflicts": [_conflict_to_dict(c) for c in result.conflicts],
                "suggestions": result.suggestions,
                "generation_duration_ms": result.generation_duration_ms,
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    if result.status != GenerationStatus.SUCCESS:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="; ".join(result.warnings)
            or "Timetable generation failed unexpectedly",
        )

    timetable_id = await _persist_validated(
        db, request.academic_session_id, request.division_id, result.entries,
        created_by=created_by,
    )
    return (
        {
            "status": result.status.value,
            "timetable_id": str(timetable_id),
            "solver_status": result.solver_status.value,
            "objective_score": result.objective_score,
            "generation_duration_ms": result.generation_duration_ms,
            "warnings": result.warnings,
        },
        status.HTTP_201_CREATED,
    )


async def _persist_validated(
    db: AsyncSession,
    session_id: UUID,
    division_id: UUID,
    entries: list[GeneratedEntry],
    *,
    created_by: UUID | None = None,
) -> UUID:
    """Insert one new version + entries atomically (rollback on any failure)."""
    try:
        max_version = await db.scalar(
            select(func.max(Timetable.version)).where(
                Timetable.academic_session_id == session_id,
                Timetable.division_id == division_id,
            )
        )
        timetable = Timetable(
            academic_session_id=session_id,
            division_id=division_id,
            status=TimetableStatus.GENERATED,
            version=(max_version or 0) + 1,
            generated_at=datetime.now(timezone.utc),
            created_by=created_by,
        )
        db.add(timetable)
        await db.flush()
        for entry in entries:
            db.add(
                TimetableEntry(
                    timetable_id=timetable.id,
                    subject_id=entry.subject_id,
                    faculty_id=entry.faculty_id,
                    room_id=entry.room_id,
                    period_id=entry.period_id,
                )
            )
        await db.commit()
        return timetable.id
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist generated timetable: {exc.orig}",
        ) from None


async def validate_timetable(
    db: AsyncSession, timetable_id: UUID, *, promote: bool = True
) -> dict:
    """Independently re-validate a persisted timetable, with quality scoring.

    Status transitions on explicit validation (promote=True): GENERATED or
    DRAFT that passes becomes VALID; a VALID timetable that fails is demoted
    to DRAFT so it can never stay VALID while invalid. PUBLISHED timetables
    are immutable and keep their status — validation only reports.
    Publishing stays a separate decision; invalid timetables can never be
    published because only VALID states feed that flow.
    """
    timetable = await get_or_404(db, Timetable, timetable_id, "Timetable")
    try:
        scope = await load_scope_data(
            db, timetable.academic_session_id, [timetable.division_id]
        )
    except ConfigurationError as exc:
        violation = {"type": "INVALID_CONFIGURATION", "message": str(exc), "details": {}}
        return {
            "timetable_id": str(timetable_id),
            "valid": False,
            "violations": [violation],
            "status": "INVALID",
            "errors": [violation],
            "warnings": [],
            "score": None,
        }

    rows = (
        await db.scalars(
            select(TimetableEntry).where(TimetableEntry.timetable_id == timetable_id)
        )
    ).all()
    generated = [
        GeneratedEntry(
            session_index=index,
            division_id=timetable.division_id,
            subject_id=row.subject_id,
            period_id=row.period_id,
            faculty_id=row.faculty_id,
            room_id=row.room_id,
        )
        for index, row in enumerate(rows)
    ]
    report: ValidationResult = validate_entries(generated, scope)
    quality = evaluate_quality(generated, scope)
    if promote:
        if report.valid and timetable.status in (
            TimetableStatus.GENERATED,
            TimetableStatus.DRAFT,
        ):
            timetable.status = TimetableStatus.VALID
            await db.commit()
        elif not report.valid and timetable.status == TimetableStatus.VALID:
            timetable.status = TimetableStatus.DRAFT
            await db.commit()

    violations = [_violation_to_dict(v) for v in report.violations]
    return {
        "timetable_id": str(timetable_id),
        "valid": report.valid,
        "violations": violations,
        "status": "VALID" if report.valid else "INVALID",
        "errors": violations,
        "warnings": quality.warnings,
        "score": quality.score,
    }


async def generation_result(db: AsyncSession, actor: User, timetable_id: UUID) -> dict:
    """Recomputed-on-demand result view: status plus a live validation report.

    Generation-time score/duration are returned by POST /generate and are not
    stored (no schema change for ephemeral solver telemetry).
    """
    # Visibility + existence first (404 for invisible/missing, all roles).
    detail = await timetable_service.get_timetable_detail(db, actor, timetable_id)
    report = await validate_timetable(db, timetable_id, promote=False)
    timetable = await get_or_404(db, Timetable, timetable_id, "Timetable")
    generated_at = timetable.generated_at
    return {
        "timetable_id": str(timetable_id),
        "status": timetable.status,
        "version": timetable.version,
        "generated_at": generated_at.isoformat() if generated_at else None,
        "entry_count": len(detail["entries"]),
        "valid": report["valid"],
        "violations": report["violations"],
    }
