"""Scheduling configuration: availability, teaching assignments, division requirements."""

from uuid import UUID

from sqlalchemy import CheckConstraint, Enum as SQLEnum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AvailabilityStatus, RoomType


class FacultyAvailability(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Per-period availability. Absence of a row means AVAILABLE (generator default)."""

    __tablename__ = "faculty_availability"
    __table_args__ = (
        UniqueConstraint("faculty_id", "period_id", name="uq_availability_faculty_period"),
    )

    faculty_id: Mapped[UUID] = mapped_column(
        ForeignKey("faculty.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    period_id: Mapped[UUID] = mapped_column(
        ForeignKey("periods.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[AvailabilityStatus] = mapped_column(
        SQLEnum(AvailabilityStatus, name="availability_status"),
        nullable=False,
        default=AvailabilityStatus.AVAILABLE,
    )

    faculty: Mapped["Faculty"] = relationship("Faculty", back_populates="availability")
    period: Mapped["Period"] = relationship("Period", back_populates="availability_slots")


class FacultyAssignment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Which faculty may teach which subject to which division in a session.

    The generator must only schedule valid assignments — never arbitrary pairs.
    """

    __tablename__ = "faculty_assignments"
    __table_args__ = (
        UniqueConstraint(
            "faculty_id",
            "subject_id",
            "division_id",
            "academic_session_id",
            name="uq_assignments_faculty_subject_division_session",
        ),
    )

    faculty_id: Mapped[UUID] = mapped_column(
        ForeignKey("faculty.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    subject_id: Mapped[UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    division_id: Mapped[UUID] = mapped_column(
        ForeignKey("divisions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    academic_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("academic_sessions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")

    faculty: Mapped["Faculty"] = relationship("Faculty", back_populates="teaching_assignments")
    subject: Mapped["Subject"] = relationship("Subject", back_populates="faculty_assignments")
    division: Mapped["Division"] = relationship("Division", back_populates="faculty_assignments")
    academic_session: Mapped["AcademicSession"] = relationship(
        "AcademicSession", back_populates="faculty_assignments"
    )


class DivisionSubjectRequirement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Subjects a division must study in a session, with per-division overrides.

    required_periods_per_week lives here (not only on Subject) because the same
    subject can need different weekly loads for different divisions/sessions.
    """

    __tablename__ = "division_subject_requirements"
    __table_args__ = (
        UniqueConstraint(
            "division_id",
            "subject_id",
            "academic_session_id",
            name="uq_requirements_division_subject_session",
        ),
        CheckConstraint(
            "required_periods_per_week > 0", name="ck_requirements_periods_positive"
        ),
    )

    division_id: Mapped[UUID] = mapped_column(
        ForeignKey("divisions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    subject_id: Mapped[UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    academic_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("academic_sessions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    required_periods_per_week: Mapped[int] = mapped_column(nullable=False)
    preferred_room_type: Mapped[RoomType | None] = mapped_column(
        SQLEnum(RoomType, name="room_type"), nullable=True
    )
    requires_lab: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")

    division: Mapped["Division"] = relationship("Division", back_populates="subject_requirements")
    subject: Mapped["Subject"] = relationship("Subject", back_populates="subject_requirements")
    academic_session: Mapped["AcademicSession"] = relationship(
        "AcademicSession", back_populates="subject_requirements"
    )
