"""Pytest fixtures — model tests run against a real PostgreSQL test database.

The test database is TRUNCATEd after every test (never production data).
Configure via TEST_DATABASE_URL (see backend/.env.example).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password
from app.main import app as fastapi_app
from app.models import Base, Department, Faculty, User
from app.models.enums import UserRole

ALL_TABLES = ", ".join(
    [
        "timetable_entries",
        "timetables",
        "division_subject_requirements",
        "faculty_assignments",
        "faculty_availability",
        "periods",
        "rooms",
        "faculty",
        "subjects",
        "divisions",
        "academic_sessions",
        "departments",
        "users",
    ]
)


@pytest.fixture(scope="session")
def engine():
    engine = create_async_engine(settings.TEST_DATABASE_URL)
    return engine


@pytest.fixture(scope="session", autouse=True)
async def _schema(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest.fixture
async def db(engine):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest.fixture(autouse=True)
async def _clean(engine):
    """Truncate after every test — also covers tests that only use HTTP."""
    yield
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        await session.execute(text(f"TRUNCATE {ALL_TABLES} RESTART IDENTITY CASCADE"))
        await session.commit()


@pytest.fixture(scope="session")
def app_test_engine():
    """Separate engine for HTTP tests: NullPool opens each connection in the
    calling loop and closes it on checkin, so TestClient portal threads never
    share pooled asyncpg connections across event loops (Windows-safe)."""
    engine = create_async_engine(settings.TEST_DATABASE_URL, poolclass=NullPool)
    yield engine
    engine.sync_engine.dispose()


@pytest.fixture
def client(app_test_engine):
    """HTTP client with the app's DB dependency pointed at the test database."""
    maker = async_sessionmaker(app_test_engine, expire_on_commit=False)

    async def override_get_db():
        async with maker() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(fastapi_app) as http:
            yield http
    finally:
        fastapi_app.dependency_overrides.clear()


TEST_PASSWORD = "Test123!"


def login_headers(http, email, password=TEST_PASSWORD) -> dict:
    token = http.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def accounts(engine):
    """Admin / faculty-with-profile / student logins plus a department."""
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        admin = User(
            name="Admin", email="a@x.edu", password_hash=hash_password(TEST_PASSWORD),
            role=UserRole.ADMIN,
        )
        fac_user = User(
            name="Fac", email="f@x.edu", password_hash=hash_password(TEST_PASSWORD),
            role=UserRole.FACULTY,
        )
        student = User(
            name="Stu", email="s@x.edu", password_hash=hash_password(TEST_PASSWORD),
            role=UserRole.STUDENT,
        )
        dept = Department(name="Test Dept", code="TST")
        session.add_all([admin, fac_user, student, dept])
        await session.flush()
        profile = Faculty(
            user_id=fac_user.id, employee_code="EMP-T1",
            department_id=dept.id, name="Test Faculty",
        )
        session.add(profile)
        await session.commit()
        for obj in (admin, fac_user, student, dept, profile):
            await session.refresh(obj)
    return {
        "admin": admin, "faculty": fac_user, "student": student,
        "profile": profile, "department": dept,
    }
