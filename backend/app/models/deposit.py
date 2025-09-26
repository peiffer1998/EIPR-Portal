"""Deposit model for reservation prepayments."""

from __future__ import annotations

import enum
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models import Account, OwnerProfile, Reservation


class DepositStatus(str, enum.Enum):
    """Lifecycle states for a reservation deposit."""

    HELD = "held"
    CONSUMED = "consumed"
    REFUNDED = "refunded"
    FORFEITED = "forfeited"


class Deposit(TimestampMixin, Base):
    """Money collected ahead of a reservation."""

    __tablename__ = "deposits"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    reservation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reservations.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("owner_profiles.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[DepositStatus] = mapped_column(Enum(DepositStatus), nullable=False)

    reservation: Mapped["Reservation"] = relationship(
        "Reservation", back_populates="deposits"
    )
    owner: Mapped["OwnerProfile"] = relationship("OwnerProfile")
    account: Mapped["Account"] = relationship("Account", back_populates="deposits")
