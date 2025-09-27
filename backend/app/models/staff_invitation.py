"""Staff invitation model for onboarding employees."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.security.encryption import EncryptedStr
from app.models.mixins import TimestampMixin
from app.models.user import UserRole


if TYPE_CHECKING:  # pragma: no cover - typing only imports
    from app.models.user import User


class StaffInvitationStatus(str, enum.Enum):
    """Lifecycle states for staff invitations."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"
    EXPIRED = "expired"


class StaffInvitation(TimestampMixin, Base):
    """Stores pending invitations for staff accounts."""

    __tablename__ = "staff_invitations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    invited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    email: Mapped[str] = mapped_column(EncryptedStr(768), nullable=False)
    first_name: Mapped[str] = mapped_column(EncryptedStr(256), nullable=False)
    last_name: Mapped[str] = mapped_column(EncryptedStr(256), nullable=False)
    phone_number: Mapped[str | None] = mapped_column(EncryptedStr(256))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    status: Mapped[StaffInvitationStatus] = mapped_column(
        Enum(StaffInvitationStatus),
        default=StaffInvitationStatus.PENDING,
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    token_prefix: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    invited_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[invited_by_user_id]
    )

    __table_args__ = ({"sqlite_autoincrement": True},)
