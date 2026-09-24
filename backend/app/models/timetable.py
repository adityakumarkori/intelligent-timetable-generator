"""Timetables and their entries.

Design decisions (spec section 8):
- A Timetable covers exactly ONE division in ONE academic session. The division is
  therefore derivable via ``timetable.division`` and is NOT duplicated on entries.
- Division conflict (one division, one subject per period) is enforced at DB level
  by UNIQUE(timetable_id, period_id).
- Faculty/room double-booking WITHIN one timetable is transitively covered by that
  same constraint. Cross-timetable conflicts (same faculty/room booked at the same
  period in two different timetables/versions) are an application-layer concern for
  the Phase 5 validator: the DB cannot know which timetable versions are
  concurrently "active", so a global UNIQUE would wrongly forbid valid drafts and
  history.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum as SQLEnum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import TimetableStatus


class Timetable(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "timetables"
    __table_args__ = (
        UniqueConstraint(
            "academic_session_id",
            "division_id",
            "version",
            name="uq_timetables_session_division_version",
        ),
        CheckConstraint("version > 0", name="ck_timetables_version_positive"),
    )

    academic_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("academic_sessions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    division_id: Mapped[UUID] = mapped_column(
        ForeignKey("divisions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[TimetableStatus] = mapped_column(
        SQLEnum(TimetableStatus, name="timetable_status"),
        nullable=False,
        default=TimetableStatus.DRAFT,
    )
    version: Mapped[int] = mapped_column(nullable=False, default=1, server_default="1")
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Lightweight audit trail (nullable: pre-Phase-6 rows have no actor data).
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    published_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    academic_session: Mapped["AcademicSession"] = relationship(
        "AcademicSession", back_populates="timetables"
    )
    division: Mapped["Division"] = relationship("Division", back_populates="timetables")
    entries: Mapped[list["TimetableEntry"]] = relationship(
        "TimetableEntry", back_populates="timetable", cascade="all, delete-orphan"
    )


class TimetableEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "timetable_entries"
    __table_args__ = (
        # One division (via its timetable) holds at most one entry per period.
        UniqueConstraint("timetable_id", "period_id", name="uq_entries_timetable_period"),
    )

    timetable_id: Mapped[UUID] = mapped_column(
        ForeignKey("timetables.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    faculty_id: Mapped[UUID] = mapped_column(
        ForeignKey("faculty.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    room_id: Mapped[UUID] = mapped_column(
        ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    period_id: Mapped[UUID] = mapped_column(
        ForeignKey("periods.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    timetable: Mapped["Timetable"] = relationship("Timetable", back_populates="entries")
    subject: Mapped["Subject"] = relationship("Subject", back_populates="timetable_entries")
    faculty: Mapped["Faculty"] = relationship("Faculty", back_populates="timetable_entries")
    room: Mapped["Room"] = relationship("Room", back_populates="timetable_entries")
    period: Mapped["Period"] = relationship("Period", back_populates="timetable_entries")
