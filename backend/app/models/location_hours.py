"""Location hours and closures."""
from __future__ import annotations

import uuid
from datetime import date, time

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class LocationHour(TimestampMixin, Base):
    """Weekly operating hours for a location."""

    __tablename__ = "location_hours"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    open_time: Mapped[time | None] = mapped_column(Time())
    close_time: Mapped[time | None] = mapped_column(Time())
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class LocationClosure(TimestampMixin, Base):
    """Special closure periods for a location."""

    __tablename__ = "location_closures"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))
