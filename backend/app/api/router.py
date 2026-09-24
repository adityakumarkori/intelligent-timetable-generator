"""Versioned API router."""

from fastapi import APIRouter

from app.api.routes.academic_sessions import router as sessions_router
from app.api.routes.assignments import router as assignments_router
from app.api.routes.auth import router as auth_router
from app.api.routes.availability import router as availability_router
from app.api.routes.departments import router as departments_router
from app.api.routes.divisions import router as divisions_router
from app.api.routes.faculty import router as faculty_router
from app.api.routes.generation import router as generation_router
from app.api.routes.health import router as health_router
from app.api.routes.periods import router as periods_router
from app.api.routes.protected import router as protected_router
from app.api.routes.requirements import router as requirements_router
from app.api.routes.rooms import router as rooms_router
from app.api.routes.subjects import router as subjects_router
from app.api.routes.timetable_entries import router as timetable_entries_router
from app.api.routes.timetables import router as timetables_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router, prefix="/auth")
api_router.include_router(protected_router, prefix="/protected")
api_router.include_router(sessions_router, prefix="/academic-sessions")
api_router.include_router(departments_router, prefix="/departments")
api_router.include_router(divisions_router, prefix="/divisions")
api_router.include_router(subjects_router, prefix="/subjects")
api_router.include_router(faculty_router, prefix="/faculty")
api_router.include_router(rooms_router, prefix="/rooms")
api_router.include_router(periods_router, prefix="/periods")
api_router.include_router(availability_router, prefix="")
api_router.include_router(assignments_router, prefix="/faculty-assignments")
api_router.include_router(requirements_router, prefix="/division-subject-requirements")
api_router.include_router(timetables_router, prefix="/timetables")
api_router.include_router(timetable_entries_router, prefix="/timetables")
api_router.include_router(generation_router, prefix="/timetables")
