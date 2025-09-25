"""Document metadata for uploaded files."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Document(TimestampMixin, Base):
    """Stores metadata for owner or pet documents."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("owner_profiles.id", ondelete="CASCADE"), nullable=True
    )
    pet_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pets.id", ondelete="CASCADE"), nullable=True
    )
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128))
    url: Mapped[str | None] = mapped_column(String(1024))
    notes: Mapped[str | None] = mapped_column(String(1024))

    owner = relationship("OwnerProfile")
    pet = relationship("Pet")
