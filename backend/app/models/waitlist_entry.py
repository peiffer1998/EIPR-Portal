"""Waitlist models for reservation overflow and confirmations."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models import (
        Account,
        Location,
        OwnerProfile,
        Reservation,
    )


JSONB_TYPE = JSONB(astext_type=Text()).with_variant(JSON(), "sqlite")


class WaitlistStatus(str, enum.Enum):
    """Lifecycle of waitlist entries."""

    OPEN = "open"
    OFFERED = "offered"
    CONVERTED = "converted"
    CANCELED = "canceled"
    EXPIRED = "expired"


class WaitlistServiceType(str, enum.Enum):
    """Supported service types for waitlist entries."""

    BOARDING = "boarding"
    DAYCARE = "daycare"
    GROOMING = "grooming"


class WaitlistEntry(TimestampMixin, Base):
    """A reservation request waiting for capacity."""

    __tablename__ = "waitlist_entries"
    __table_args__ = (
        Index("ix_waitlist_account", "account_id"),
        Index("ix_waitlist_location", "location_id"),
        Index("ix_waitlist_start_date", "start_date"),
        Index("ix_waitlist_status", "status"),
        Index(
            "ix_waitlist_open_status",
            "status",
            unique=False,
            postgresql_where=text("status = 'open'"),
            sqlite_where=text("status = 'open'"),
        ),
        Index(
            "ux_waitlist_owner_service_span_open",
            "owner_id",
            "service_type",
            "start_date",
            "end_date",
            unique=True,
            postgresql_where=text("status = 'open'"),
            sqlite_where=text("status = 'open'"),
        ),
        CheckConstraint("start_date <= end_date", name="ck_waitlist_date_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("owner_profiles.id", ondelete="CASCADE"), nullable=False
    )
    reservation_request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reservations.id", ondelete="SET NULL"), nullable=True
    )
    service_type: Mapped[WaitlistServiceType] = mapped_column(
        Enum(WaitlistServiceType), nullable=False
    )
    lodging_type_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lodging_types.id", ondelete="SET NULL"), nullable=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    pets_json: Mapped[list[dict]] = mapped_column(JSONB_TYPE, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1024))
    status: Mapped[WaitlistStatus] = mapped_column(
        Enum(WaitlistStatus), nullable=False, default=WaitlistStatus.OPEN
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    offered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    converted_reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reservations.id", ondelete="SET NULL"), nullable=True
    )

    account: Mapped["Account"] = relationship("Account")
    location: Mapped["Location"] = relationship("Location")
    owner: Mapped["OwnerProfile"] = relationship("OwnerProfile")
    reservation_request: Mapped["Reservation | None"] = relationship(
        "Reservation", foreign_keys=[reservation_request_id]
    )
    converted_reservation: Mapped["Reservation | None"] = relationship(
        "Reservation", foreign_keys=[converted_reservation_id]
    )
