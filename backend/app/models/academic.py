"""Core academic master data: departments, divisions, sessions, subjects, faculty, rooms, periods.

Deletion policy: master records referenced by scheduling data use ON DELETE RESTRICT
so academic history cannot be wiped accidentally. Composition (timetable -> entries)
is the only CASCADE (see timetable.py).

One-to-many collections use passive_deletes=True so the ORM never "helpfully"
NULLs children's foreign keys on parent delete (which would surface as a
misleading NOT NULL violation): the DELETE reaches PostgreSQL, RESTRICT fires,
and callers get a proper foreign-key error to translate into 409.
"""

from datetime import date as date_type
from datetime import time as time_type
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, Enum as SQLEnum, ForeignKey, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import DayOfWeek, RoomType, SubjectType


class Department(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "departments"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")

    divisions: Mapped[list["Division"]] = relationship(
        "Division", back_populates="department", passive_deletes=True
    )
    faculty_members: Mapped[list["Faculty"]] = relationship(
        "Faculty", back_populates="department", passive_deletes=True
    )


class Division(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A class/division belonging to a department (e.g. CSE-A)."""

    __tablename__ = "divisions"
    __table_args__ = (
        UniqueConstraint("department_id", "code", name="uq_divisions_department_code"),
        CheckConstraint("student_count >= 0", name="ck_divisions_student_count_non_negative"),
    )

    department_id: Mapped[UUID] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    student_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")

    department: Mapped["Department"] = relationship("Department", back_populates="divisions")
    subject_requirements: Mapped[list["DivisionSubjectRequirement"]] = relationship(
        "DivisionSubjectRequirement", back_populates="division", passive_deletes=True
    )
    faculty_assignments: Mapped[list["FacultyAssignment"]] = relationship(
        "FacultyAssignment", back_populates="division", passive_deletes=True
    )
    timetables: Mapped[list["Timetable"]] = relationship(
        "Timetable", back_populates="division", passive_deletes=True
    )


class AcademicSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An academic year/term (e.g. 2026-27).

    Single-active-session enforcement is a business-layer rule (Phase 5+),
    not a DB partial index, per spec.
    """

    __tablename__ = "academic_sessions"
    __table_args__ = (
        CheckConstraint("end_date > start_date", name="ck_sessions_date_order"),
    )

    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    start_date: Mapped[date_type] = mapped_column(Date, nullable=False)
    end_date: Mapped[date_type] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")

    subject_requirements: Mapped[list["DivisionSubjectRequirement"]] = relationship(
        "DivisionSubjectRequirement", back_populates="academic_session", passive_deletes=True
    )
    faculty_assignments: Mapped[list["FacultyAssignment"]] = relationship(
        "FacultyAssignment", back_populates="academic_session", passive_deletes=True
    )
    timetables: Mapped[list["Timetable"]] = relationship(
        "Timetable", back_populates="academic_session", passive_deletes=True
    )


class Subject(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "subjects"
    __table_args__ = (
        CheckConstraint(
            "required_periods_per_week > 0", name="ck_subjects_periods_positive"
        ),
    )

    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    subject_type: Mapped[SubjectType] = mapped_column(
        SQLEnum(SubjectType, name="subject_type"), nullable=False, default=SubjectType.LECTURE
    )
    required_periods_per_week: Mapped[int] = mapped_column(nullable=False)
    # NULL means "any room type is acceptable".
    required_room_type: Mapped[RoomType | None] = mapped_column(
        SQLEnum(RoomType, name="room_type"), nullable=True
    )
    requires_lab: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")

    subject_requirements: Mapped[list["DivisionSubjectRequirement"]] = relationship(
        "DivisionSubjectRequirement", back_populates="subject", passive_deletes=True
    )
    faculty_assignments: Mapped[list["FacultyAssignment"]] = relationship(
        "FacultyAssignment", back_populates="subject", passive_deletes=True
    )
    timetable_entries: Mapped[list["TimetableEntry"]] = relationship(
        "TimetableEntry", back_populates="subject", passive_deletes=True
    )


class Faculty(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "faculty"

    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    employee_code: Mapped[str] = mapped_column(
        String(30), nullable=False, unique=True, index=True
    )
    department_id: Mapped[UUID] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")

    user: Mapped["User | None"] = relationship("User", back_populates="faculty_profile")
    department: Mapped["Department"] = relationship("Department", back_populates="faculty_members")
    availability: Mapped[list["FacultyAvailability"]] = relationship(
        "FacultyAvailability", back_populates="faculty", passive_deletes=True
    )
    teaching_assignments: Mapped[list["FacultyAssignment"]] = relationship(
        "FacultyAssignment", back_populates="faculty", passive_deletes=True
    )
    timetable_entries: Mapped[list["TimetableEntry"]] = relationship(
        "TimetableEntry", back_populates="faculty", passive_deletes=True
    )


class Room(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_rooms_capacity_positive"),
    )

    name: Mapped[str] = mapped_column(String(60), nullable=False, unique=True, index=True)
    room_type: Mapped[RoomType] = mapped_column(
        SQLEnum(RoomType, name="room_type"), nullable=False
    )
    capacity: Mapped[int] = mapped_column(nullable=False)
    building: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")

    timetable_entries: Mapped[list["TimetableEntry"]] = relationship(
        "TimetableEntry", back_populates="room", passive_deletes=True
    )


class Period(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A schedulable time slot. Rows with is_break=True are never assignable
    (enforced by the generator/validator, not the DB)."""

    __tablename__ = "periods"
    __table_args__ = (
        UniqueConstraint("day_of_week", "period_order", name="uq_periods_day_order"),
        CheckConstraint("end_time > start_time", name="ck_periods_time_order"),
    )

    day_of_week: Mapped[DayOfWeek] = mapped_column(
        SQLEnum(DayOfWeek, name="day_of_week"), nullable=False, index=True
    )
    start_time: Mapped[time_type] = mapped_column(Time, nullable=False)
    end_time: Mapped[time_type] = mapped_column(Time, nullable=False)
    period_order: Mapped[int] = mapped_column(nullable=False)
    is_break: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")

    availability_slots: Mapped[list["FacultyAvailability"]] = relationship(
        "FacultyAvailability", back_populates="period", passive_deletes=True
    )
    timetable_entries: Mapped[list["TimetableEntry"]] = relationship(
        "TimetableEntry", back_populates="period", passive_deletes=True
    )
