"""Digital agreement templates and signatures."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models import OwnerProfile, Pet, User


class AgreementTemplate(TimestampMixin, Base):
    """Reusable agreement template configured per account."""

    __tablename__ = "agreement_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text(), nullable=False)
    requires_signature: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(default=1)

    signatures: Mapped[list["AgreementSignature"]] = relationship(
        "AgreementSignature",
        back_populates="agreement",
        cascade="all, delete-orphan",
    )


class AgreementSignature(TimestampMixin, Base):
    """A captured signature for an agreement template."""

    __tablename__ = "agreement_signatures"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agreement_template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agreement_templates.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("owner_profiles.id", ondelete="CASCADE"), nullable=True
    )
    pet_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pets.id", ondelete="CASCADE"), nullable=True
    )
    signed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(String(64))
    notes: Mapped[str | None] = mapped_column(String(512))

    agreement: Mapped[AgreementTemplate] = relationship(
        "AgreementTemplate", back_populates="signatures"
    )
    owner: Mapped["OwnerProfile | None"] = relationship("OwnerProfile")
    pet: Mapped["Pet | None"] = relationship("Pet")
    signed_by_user: Mapped["User | None"] = relationship("User")
