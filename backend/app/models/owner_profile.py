"""Owner profile extending a user account."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models import OwnerIcon, Pet, User
    from app.models.deposit import Deposit


class OwnerProfile(TimestampMixin, Base):
    """Pet parent profile and contact preferences."""

    __tablename__ = "owner_profiles"

    __table_args__ = (
        Index(
            "ux_owner_profiles_external_id",
            "external_id",
            unique=True,
            sqlite_where=text("external_id IS NOT NULL"),
            postgresql_where=text("external_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    preferred_contact_method: Mapped[str | None] = mapped_column(String(32))
    notes: Mapped[str | None] = mapped_column(String(1024))
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email_opt_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sms_opt_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["User"] = relationship("User", back_populates="owner_profile")
    pets: Mapped[list["Pet"]] = relationship(
        "Pet", back_populates="owner", cascade="all, delete-orphan"
    )
    icon_assignments: Mapped[list["OwnerIcon"]] = relationship(
        "OwnerIcon", back_populates="owner", cascade="all, delete-orphan"
    )
    deposits: Mapped[list["Deposit"]] = relationship(
        "Deposit", back_populates="owner", cascade="all, delete-orphan"
    )
