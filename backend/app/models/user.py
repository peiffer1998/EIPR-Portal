"""User model for staff and pet-parent identities."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class UserRole(str, enum.Enum):
    """Role enumeration for platform permissions."""

    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    MANAGER = "manager"
    STAFF = "staff"
    PET_PARENT = "pet_parent"


class UserStatus(str, enum.Enum):
    """Enumerates user activation states."""

    INVITED = "invited"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class User(TimestampMixin, Base):
    """User entity for authentication and authorization."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(32))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus), default=UserStatus.INVITED, nullable=False
    )
    is_primary_contact: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    account: Mapped["Account"] = relationship("Account", back_populates="users")
    owner_profile: Mapped["OwnerProfile | None"] = relationship(
        "OwnerProfile", back_populates="user", uselist=False
    )
