"""Pet profile model."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class PetType(str, enum.Enum):
    """Supported pet categories."""

    DOG = "dog"
    CAT = "cat"
    OTHER = "other"


class Pet(TimestampMixin, Base):
    """Represents a pet enrolled with the resort."""

    __tablename__ = "pets"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("owner_profiles.id", ondelete="CASCADE"), nullable=False
    )
    home_location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    pet_type: Mapped[PetType] = mapped_column(Enum(PetType), nullable=False)
    breed: Mapped[str | None] = mapped_column(String(120))
    color: Mapped[str | None] = mapped_column(String(120))
    date_of_birth: Mapped[Date | None] = mapped_column(Date())
    notes: Mapped[str | None] = mapped_column(String(1024))

    owner: Mapped["OwnerProfile"] = relationship("OwnerProfile", back_populates="pets")
    home_location: Mapped["Location" | None] = relationship("Location", back_populates="pets")
    reservations: Mapped[list["Reservation"]] = relationship(
        "Reservation", back_populates="pet"
    )
