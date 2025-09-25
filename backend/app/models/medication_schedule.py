"""Medication schedule model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class MedicationSchedule(TimestampMixin, Base):
    """Represents a medication administration schedule for a reservation."""

    __tablename__ = "medication_schedules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, unique=True)
    reservation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reservations.id", ondelete="CASCADE"), nullable=False
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    medication: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(String(1024))

    reservation: Mapped["Reservation"] = relationship(
        "Reservation", back_populates="medication_schedules"
    )
