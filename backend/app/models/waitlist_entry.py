"""Waitlist models for reservation overflow."""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.models.reservation import ReservationType


class WaitlistStatus(str, enum.Enum):
    """Lifecycle of waitlist entries."""

    PENDING = "pending"
    OFFERED = "offered"
    CONFIRMED = "confirmed"
    CANCELED = "canceled"


class WaitlistEntry(TimestampMixin, Base):
    """A reservation request waiting for capacity."""

    __tablename__ = "waitlist_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    pet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pets.id", ondelete="CASCADE"), nullable=False
    )
    reservation_type: Mapped[ReservationType] = mapped_column(Enum(ReservationType), nullable=False)
    desired_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[WaitlistStatus] = mapped_column(
        Enum(WaitlistStatus), nullable=False, default=WaitlistStatus.PENDING
    )
    notes: Mapped[str | None] = mapped_column(String(1024))
    offered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    location = relationship("Location")
    pet = relationship("Pet")
