"""Physical location for an account."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


if TYPE_CHECKING:  # pragma: no cover - typing only imports
    from app.models.account import Account
    from app.models.location_capacity import LocationCapacityRule
    from app.models.pet import Pet
    from app.models.reservation import Reservation


class Location(TimestampMixin, Base):
    """Represents a physical facility location under an account."""

    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    address_line1: Mapped[str | None] = mapped_column(String(255))
    address_line2: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(120))
    postal_code: Mapped[str | None] = mapped_column(String(32))
    phone_number: Mapped[str | None] = mapped_column(String(32))

    account: Mapped["Account"] = relationship("Account", back_populates="locations")
    pets: Mapped[list["Pet"]] = relationship("Pet", back_populates="home_location")
    reservations: Mapped[list["Reservation"]] = relationship(
        "Reservation", back_populates="location"
    )
    capacity_rules: Mapped[list["LocationCapacityRule"]] = relationship(
        "LocationCapacityRule", back_populates="location", cascade="all, delete-orphan"
    )
