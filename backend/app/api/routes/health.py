"""Health-check endpoints (no DB access — pure liveness probe)."""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "backend", "version": settings.APP_VERSION}
