"""Reservation models."""
from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class ReservationStatus(str, enum.Enum):
    """Lifecycle states for reservations."""

    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELED = "canceled"


class ReservationType(str, enum.Enum):
    """Service types available for booking."""

    BOARDING = "boarding"
    DAYCARE = "daycare"
    GROOMING = "grooming"
    TRAINING = "training"
    OTHER = "other"


class Reservation(TimestampMixin, Base):
    """Represents a booked service for a pet."""

    __tablename__ = "reservations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    pet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pets.id", ondelete="CASCADE"), nullable=False
    )
    reservation_type: Mapped[ReservationType] = mapped_column(
        Enum(ReservationType), nullable=False
    )
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus), default=ReservationStatus.REQUESTED, nullable=False
    )
    start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(UTC), nullable=False
    )
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    base_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1024))
    kennel_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    check_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    check_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    account: Mapped["Account"] = relationship("Account")
    location: Mapped["Location"] = relationship("Location", back_populates="reservations")
    pet: Mapped["Pet"] = relationship("Pet", back_populates="reservations")
    feeding_schedules: Mapped[list["FeedingSchedule"]] = relationship("FeedingSchedule", back_populates="reservation", cascade="all, delete-orphan")
    medication_schedules: Mapped[list["MedicationSchedule"]] = relationship("MedicationSchedule", back_populates="reservation", cascade="all, delete-orphan")
    invoice: Mapped["Invoice | None"] = relationship("Invoice", back_populates="reservation", uselist=False)
