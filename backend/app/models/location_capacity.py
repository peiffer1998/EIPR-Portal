"""Location-specific capacity rules by reservation type."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.models.reservation import ReservationType


if TYPE_CHECKING:  # pragma: no cover - typing only imports
    from app.models.location import Location


class LocationCapacityRule(TimestampMixin, Base):
    """Defines maximum concurrent reservations per type for a location."""

    __tablename__ = "location_capacity_rules"
    __table_args__ = (
        UniqueConstraint(
            "location_id", "reservation_type", name="uq_capacity_location_type"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    reservation_type: Mapped[ReservationType] = mapped_column(nullable=False)
    max_active: Mapped[int | None] = mapped_column(Integer())
    waitlist_limit: Mapped[int | None] = mapped_column(Integer())

    location: Mapped["Location"] = relationship(
        "Location", back_populates="capacity_rules"
    )
