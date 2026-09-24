"""User entity — authentication foundation (no auth logic in Phase 2)."""

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import UserRole


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    # Real password hashing lands in Phase 3; column exists so the schema is stable.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role"), nullable=False, default=UserRole.ADMIN
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")

    # One user backs at most one faculty profile.
    faculty_profile: Mapped["Faculty | None"] = relationship(
        "Faculty", back_populates="user", uselist=False
    )
