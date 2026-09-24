"""Initial schema: users, academic master data, scheduling config, timetables.

Revision ID: 0001_initial
Revises: None
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _enums(create_type: bool = True) -> dict[str, postgresql.ENUM]:
    """Enum type objects.

    create_type=True: standalone instances used for explicit CREATE/DROP TYPE.
    create_type=False: instances bound to table columns so the table-level
    create/drop events stay no-ops (Alembic dispatches them with
    checkfirst=False, which would otherwise re-emit CREATE TYPE and fail
    with "type already exists").
    """
    kw = {"create_type": create_type} if not create_type else {}
    return {
        "user_role": postgresql.ENUM(
            "SUPER_ADMIN", "ADMIN", "FACULTY", "STUDENT", name="user_role", **kw
        ),
        "subject_type": postgresql.ENUM(
            "LECTURE", "LAB", "TUTORIAL", "PRACTICAL", "OTHER", name="subject_type", **kw
        ),
        "room_type": postgresql.ENUM(
            "CLASSROOM", "LAB", "SEMINAR_ROOM", "OTHER", name="room_type", **kw
        ),
        "day_of_week": postgresql.ENUM(
            "MONDAY",
            "TUESDAY",
            "WEDNESDAY",
            "THURSDAY",
            "FRIDAY",
            "SATURDAY",
            "SUNDAY",
            name="day_of_week",
            **kw,
        ),
        "availability_status": postgresql.ENUM(
            "AVAILABLE", "UNAVAILABLE", name="availability_status", **kw
        ),
        "timetable_status": postgresql.ENUM(
            "DRAFT", "GENERATED", "VALID", "PUBLISHED", "ARCHIVED",
            name="timetable_status",
            **kw,
        ),
    }


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    for enum in _enums().values():
        enum.create(op.get_bind(), checkfirst=True)
    enums = _enums(create_type=False)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", enums["user_role"], nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_departments_code", "departments", ["code"], unique=True)

    op.create_table(
        "academic_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("end_date > start_date", name="ck_sessions_date_order"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_academic_sessions_name", "academic_sessions", ["name"], unique=True)

    op.create_table(
        "divisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("student_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("student_count >= 0", name="ck_divisions_student_count_non_negative"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("department_id", "code", name="uq_divisions_department_code"),
    )
    op.create_index("ix_divisions_department_id", "divisions", ["department_id"], unique=False)

    op.create_table(
        "subjects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("subject_type", enums["subject_type"], nullable=False),
        sa.Column("required_periods_per_week", sa.Integer(), nullable=False),
        sa.Column("required_room_type", enums["room_type"], nullable=True),
        sa.Column("requires_lab", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("required_periods_per_week > 0", name="ck_subjects_periods_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_subjects_code", "subjects", ["code"], unique=True)

    op.create_table(
        "faculty",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("employee_code", sa.String(length=30), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_code"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_faculty_department_id", "faculty", ["department_id"], unique=False)
    op.create_index("ix_faculty_employee_code", "faculty", ["employee_code"], unique=True)

    op.create_table(
        "rooms",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("room_type", enums["room_type"], nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("building", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("capacity > 0", name="ck_rooms_capacity_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_rooms_name", "rooms", ["name"], unique=True)

    op.create_table(
        "periods",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day_of_week", enums["day_of_week"], nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("period_order", sa.Integer(), nullable=False),
        sa.Column("is_break", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("end_time > start_time", name="ck_periods_time_order"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("day_of_week", "period_order", name="uq_periods_day_order"),
    )
    op.create_index("ix_periods_day_of_week", "periods", ["day_of_week"], unique=False)

    op.create_table(
        "faculty_availability",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("faculty_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", enums["availability_status"], nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["faculty_id"], ["faculty.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["period_id"], ["periods.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("faculty_id", "period_id", name="uq_availability_faculty_period"),
    )
    op.create_index("ix_faculty_availability_faculty_id", "faculty_availability", ["faculty_id"], unique=False)
    op.create_index("ix_faculty_availability_period_id", "faculty_availability", ["period_id"], unique=False)

    op.create_table(
        "faculty_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("faculty_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("division_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["academic_session_id"], ["academic_sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["division_id"], ["divisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["faculty_id"], ["faculty.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "faculty_id", "subject_id", "division_id", "academic_session_id",
            name="uq_assignments_faculty_subject_division_session",
        ),
    )
    op.create_index("ix_faculty_assignments_academic_session_id", "faculty_assignments", ["academic_session_id"], unique=False)
    op.create_index("ix_faculty_assignments_division_id", "faculty_assignments", ["division_id"], unique=False)
    op.create_index("ix_faculty_assignments_faculty_id", "faculty_assignments", ["faculty_id"], unique=False)
    op.create_index("ix_faculty_assignments_subject_id", "faculty_assignments", ["subject_id"], unique=False)

    op.create_table(
        "division_subject_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("division_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("required_periods_per_week", sa.Integer(), nullable=False),
        sa.Column("preferred_room_type", enums["room_type"], nullable=True),
        sa.Column("requires_lab", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("required_periods_per_week > 0", name="ck_requirements_periods_positive"),
        sa.ForeignKeyConstraint(["academic_session_id"], ["academic_sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["division_id"], ["divisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "division_id", "subject_id", "academic_session_id",
            name="uq_requirements_division_subject_session",
        ),
    )
    op.create_index("ix_division_subject_requirements_academic_session_id", "division_subject_requirements", ["academic_session_id"], unique=False)
    op.create_index("ix_division_subject_requirements_division_id", "division_subject_requirements", ["division_id"], unique=False)
    op.create_index("ix_division_subject_requirements_subject_id", "division_subject_requirements", ["subject_id"], unique=False)

    op.create_table(
        "timetables",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("academic_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("division_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", enums["timetable_status"], nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("version > 0", name="ck_timetables_version_positive"),
        sa.ForeignKeyConstraint(["academic_session_id"], ["academic_sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["division_id"], ["divisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "academic_session_id", "division_id", "version",
            name="uq_timetables_session_division_version",
        ),
    )
    op.create_index("ix_timetables_academic_session_id", "timetables", ["academic_session_id"], unique=False)
    op.create_index("ix_timetables_division_id", "timetables", ["division_id"], unique=False)

    op.create_table(
        "timetable_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timetable_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("faculty_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_id", postgresql.UUID(as_uuid=True), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["faculty_id"], ["faculty.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["period_id"], ["periods.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["timetable_id"], ["timetables.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("timetable_id", "period_id", name="uq_entries_timetable_period"),
    )
    op.create_index("ix_timetable_entries_faculty_id", "timetable_entries", ["faculty_id"], unique=False)
    op.create_index("ix_timetable_entries_period_id", "timetable_entries", ["period_id"], unique=False)
    op.create_index("ix_timetable_entries_room_id", "timetable_entries", ["room_id"], unique=False)
    op.create_index("ix_timetable_entries_subject_id", "timetable_entries", ["subject_id"], unique=False)
    op.create_index("ix_timetable_entries_timetable_id", "timetable_entries", ["timetable_id"], unique=False)


def downgrade() -> None:
    for table, indexes in [
        ("timetable_entries", ["ix_timetable_entries_timetable_id", "ix_timetable_entries_subject_id", "ix_timetable_entries_room_id", "ix_timetable_entries_period_id", "ix_timetable_entries_faculty_id"]),
        ("timetables", ["ix_timetables_division_id", "ix_timetables_academic_session_id"]),
        ("division_subject_requirements", ["ix_division_subject_requirements_subject_id", "ix_division_subject_requirements_division_id", "ix_division_subject_requirements_academic_session_id"]),
        ("faculty_assignments", ["ix_faculty_assignments_subject_id", "ix_faculty_assignments_faculty_id", "ix_faculty_assignments_division_id", "ix_faculty_assignments_academic_session_id"]),
        ("faculty_availability", ["ix_faculty_availability_period_id", "ix_faculty_availability_faculty_id"]),
        ("periods", ["ix_periods_day_of_week"]),
        ("rooms", ["ix_rooms_name"]),
        ("faculty", ["ix_faculty_employee_code", "ix_faculty_department_id"]),
        ("subjects", ["ix_subjects_code"]),
        ("divisions", ["ix_divisions_department_id"]),
        ("academic_sessions", ["ix_academic_sessions_name"]),
        ("departments", ["ix_departments_code"]),
        ("users", ["ix_users_email"]),
    ]:
        for index in indexes:
            op.drop_index(index, table_name=table)
        op.drop_table(table)

    for enum in reversed(list(_enums().values())):
        enum.drop(op.get_bind(), checkfirst=True)
