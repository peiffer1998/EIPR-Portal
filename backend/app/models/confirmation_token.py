"""Confirmation tokens for pending reservations."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models import Account, Reservation


class ConfirmationMethod(str, enum.Enum):
    """Delivery channels for confirmation links."""

    EMAIL = "email"
    SMS = "sms"


class ConfirmationToken(TimestampMixin, Base):
    """Token issued to confirm a pending reservation."""

    __tablename__ = "confirmation_tokens"
    __table_args__ = (
        Index("ix_confirmation_account", "account_id"),
        Index("ix_confirmation_reservation", "reservation_id"),
        Index("ix_confirmation_expires", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    reservation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reservations.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    method: Mapped[ConfirmationMethod] = mapped_column(
        Enum(ConfirmationMethod), nullable=False
    )
    sent_to: Mapped[str | None] = mapped_column(String(320))
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    account: Mapped["Account"] = relationship("Account")
    reservation: Mapped["Reservation"] = relationship("Reservation")
