"""Custom icon metadata for highlighting owners and pets."""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models import OwnerProfile, Pet


class IconEntity(str, enum.Enum):
    """Entities that an icon can be attached to."""

    PET = "pet"
    OWNER = "owner"
    RESERVATION = "reservation"


class Icon(TimestampMixin, Base):
    """Account-scoped icon definition."""

    __tablename__ = "icons"
    __table_args__ = (UniqueConstraint("account_id", "slug", name="uq_icon_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(16))
    color: Mapped[str | None] = mapped_column(String(16))
    description: Mapped[str | None] = mapped_column(Text())
    applies_to: Mapped[IconEntity] = mapped_column(
        Enum(IconEntity), default=IconEntity.PET, nullable=False
    )
    popup_text: Mapped[str | None] = mapped_column(String(512))
    affects_capacity: Mapped[bool] = mapped_column(Boolean, default=False)

    owner_assignments: Mapped[list["OwnerIcon"]] = relationship(
        "OwnerIcon",
        back_populates="icon",
        cascade="all, delete-orphan",
    )
    pet_assignments: Mapped[list["PetIcon"]] = relationship(
        "PetIcon",
        back_populates="icon",
        cascade="all, delete-orphan",
    )


class OwnerIcon(TimestampMixin, Base):
    """Association between an owner and an icon."""

    __tablename__ = "owner_icons"
    __table_args__ = (UniqueConstraint("owner_id", "icon_id", name="uq_owner_icon"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("owner_profiles.id", ondelete="CASCADE"), nullable=False
    )
    icon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("icons.id", ondelete="CASCADE"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(String(512))

    owner: Mapped["OwnerProfile"] = relationship(
        "OwnerProfile", back_populates="icon_assignments"
    )
    icon: Mapped[Icon] = relationship("Icon", back_populates="owner_assignments")


class PetIcon(TimestampMixin, Base):
    """Association between a pet and an icon."""

    __tablename__ = "pet_icons"
    __table_args__ = (UniqueConstraint("pet_id", "icon_id", name="uq_pet_icon"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    pet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pets.id", ondelete="CASCADE"), nullable=False
    )
    icon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("icons.id", ondelete="CASCADE"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(String(512))

    pet: Mapped["Pet"] = relationship("Pet", back_populates="icon_assignments")
    icon: Mapped[Icon] = relationship("Icon", back_populates="pet_assignments")
