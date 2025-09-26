"""Store models: packages, gift certificates, store credit, credit applications."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime, date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models import Account, Invoice, OwnerProfile, Reservation


class PackageApplicationType(str, enum.Enum):
    """Services that a package can apply to."""

    DAYCARE = "daycare"
    BOARDING = "boarding"
    GROOMING = "grooming"
    CURRENCY = "currency"


class PackageCreditSource(str, enum.Enum):
    """Origins of package credit adjustments."""

    PURCHASE = "purchase"
    CONSUME = "consume"
    ADJUST = "adjust"


class StoreCreditSource(str, enum.Enum):
    """Reasons store credit ledger entries are created."""

    PURCHASE_GC = "purchase_gc"
    REDEEM_GC = "redeem_gc"
    REFUND = "refund"
    MANUAL = "manual"
    CONSUME = "consume"


class CreditApplicationType(str, enum.Enum):
    """Types of credits applied to invoices."""

    PACKAGE = "package"
    STORE_CREDIT = "store_credit"
    GIFT_CERTIFICATE = "gift_certificate"


class PackageType(TimestampMixin, Base):
    """Configures purchasable credit packages."""

    __tablename__ = "package_types"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    applies_to: Mapped[PackageApplicationType] = mapped_column(
        Enum(PackageApplicationType), nullable=False
    )
    credits_per_package: Mapped[int] = mapped_column(nullable=False, default=1)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    account: Mapped["Account"] = relationship("Account")
    credits: Mapped[list["PackageCredit"]] = relationship(
        "PackageCredit", back_populates="package_type"
    )


class PackageCredit(Base):
    """Ledger of package credits purchased and consumed."""

    __tablename__ = "package_credits"

    __table_args__ = (
        Index(
            "ux_package_credits_account_external",
            "account_id",
            "external_id",
            unique=True,
            sqlite_where=text("external_id IS NOT NULL"),
            postgresql_where=text("external_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("owner_profiles.id", ondelete="CASCADE"), nullable=False
    )
    package_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("package_types.id", ondelete="CASCADE"), nullable=False
    )
    credits: Mapped[int] = mapped_column(nullable=False)
    source: Mapped[PackageCreditSource] = mapped_column(
        Enum(PackageCreditSource), nullable=False
    )
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True
    )
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reservations.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    package_type: Mapped[PackageType] = relationship(
        "PackageType", back_populates="credits"
    )
    owner: Mapped["OwnerProfile"] = relationship("OwnerProfile")
    invoice: Mapped[Optional["Invoice"]] = relationship(
        "Invoice", back_populates="package_credits"
    )
    reservation: Mapped[Optional["Reservation"]] = relationship("Reservation")


class GiftCertificate(TimestampMixin, Base):
    """Gift certificates that generate store credit upon redemption."""

    __tablename__ = "gift_certificates"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    original_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    remaining_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    purchaser_owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("owner_profiles.id", ondelete="CASCADE"), nullable=False
    )
    recipient_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("owner_profiles.id", ondelete="SET NULL"), nullable=True
    )
    recipient_email: Mapped[str | None] = mapped_column(String(255))
    expires_on: Mapped[Optional[date]] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    purchaser: Mapped["OwnerProfile"] = relationship(
        "OwnerProfile", foreign_keys=[purchaser_owner_id]
    )
    recipient: Mapped[Optional["OwnerProfile"]] = relationship(
        "OwnerProfile", foreign_keys=[recipient_owner_id]
    )


class StoreCreditLedger(Base):
    """Ledger of store credit debits and credits."""

    __tablename__ = "store_credit_ledger"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("owner_profiles.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    source: Mapped[StoreCreditSource] = mapped_column(
        Enum(StoreCreditSource), nullable=False
    )
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    owner: Mapped["OwnerProfile"] = relationship("OwnerProfile")
    invoice: Mapped[Optional["Invoice"]] = relationship(
        "Invoice", back_populates="store_credit_entries"
    )


class CreditApplication(Base):
    """Credits applied against an invoice balance."""

    __tablename__ = "credit_applications"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_credit_app_amount_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[CreditApplicationType] = mapped_column(
        Enum(CreditApplicationType), nullable=False
    )
    reference_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    units: Mapped[int | None] = mapped_column(nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    invoice: Mapped["Invoice"] = relationship(
        "Invoice", back_populates="credit_applications"
    )
