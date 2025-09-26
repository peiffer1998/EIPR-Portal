"""Payment transaction and event models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.invoice import Invoice
    from app.models.owner_profile import OwnerProfile


JSONB_TYPE = JSONB(astext_type=Text()).with_variant(JSON(), "sqlite")


class PaymentTransactionStatus(str, enum.Enum):
    """Lifecycle states for payment transactions."""

    REQUIRES_PAYMENT_METHOD = "requires_payment_method"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIAL_REFUND = "partial_refund"


class PaymentTransaction(TimestampMixin, Base):
    """Represents a payment attempt for an invoice."""

    __tablename__ = "payment_transactions"

    __table_args__ = (
        Index(
            "ux_payment_transactions_account_external",
            "account_id",
            "external_id",
            unique=True,
            sqlite_where=text("external_id IS NOT NULL"),
            postgresql_where=text("external_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("owner_profiles.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="stripe")
    provider_payment_intent_id: Mapped[str | None] = mapped_column(
        String(255), unique=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(12), nullable=False, default="usd")
    status: Mapped[PaymentTransactionStatus] = mapped_column(
        Enum(PaymentTransactionStatus), nullable=False
    )
    failure_reason: Mapped[str | None] = mapped_column(Text())
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    invoice: Mapped["Invoice"] = relationship(
        "Invoice", back_populates="payment_transactions"
    )
    owner: Mapped["OwnerProfile"] = relationship("OwnerProfile")


class PaymentEvent(Base):
    """Raw provider webhook events for auditing and idempotency."""

    __tablename__ = "payment_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider_event_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),  # type: ignore[arg-type]
    )
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB_TYPE, nullable=False)
