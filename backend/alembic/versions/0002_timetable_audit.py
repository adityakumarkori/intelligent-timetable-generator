"""Add lightweight timetable audit columns (Phase 6).

Revision ID: 0002_timetable_audit
Revises: 0001_initial
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_timetable_audit"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "timetables",
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "timetables",
        sa.Column("published_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_timetables_created_by_users",
        "timetables",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_timetables_published_by_users",
        "timetables",
        "users",
        ["published_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_timetables_created_by", "timetables", ["created_by"])
    op.create_index("ix_timetables_published_by", "timetables", ["published_by"])


def downgrade() -> None:
    op.drop_index("ix_timetables_published_by", table_name="timetables")
    op.drop_index("ix_timetables_created_by", table_name="timetables")
    op.drop_constraint("fk_timetables_published_by_users", "timetables", type_="foreignkey")
    op.drop_constraint("fk_timetables_created_by_users", "timetables", type_="foreignkey")
    op.drop_column("timetables", "published_by")
    op.drop_column("timetables", "created_by")
