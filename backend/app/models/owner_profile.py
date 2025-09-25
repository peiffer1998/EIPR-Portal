"""Owner profile extending a user account."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models import OwnerIcon, Pet, User


class OwnerProfile(TimestampMixin, Base):
    """Pet parent profile and contact preferences."""

    __tablename__ = "owner_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    preferred_contact_method: Mapped[str | None] = mapped_column(String(32))
    notes: Mapped[str | None] = mapped_column(String(1024))

    user: Mapped["User"] = relationship("User", back_populates="owner_profile")
    pets: Mapped[list["Pet"]] = relationship(
        "Pet", back_populates="owner", cascade="all, delete-orphan"
    )
    icon_assignments: Mapped[list["OwnerIcon"]] = relationship(
        "OwnerIcon", back_populates="owner", cascade="all, delete-orphan"
    )
