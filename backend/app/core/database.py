"""Async SQLAlchemy engine/session (no models yet — Phase 2).

Phase 1 only proves the wiring: engine can be created from DATABASE_URL
and a session dependency exists for future routes.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
