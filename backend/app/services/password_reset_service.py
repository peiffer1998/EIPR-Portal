"""Password reset services."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_password_hash
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.services import user_service

_RESET_TOKEN_TTL = timedelta(hours=1)

def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


async def create_reset_token(session: AsyncSession, *, email: str) -> tuple[str, datetime] | None:
    user = await user_service.get_user_by_email(session, email=email.lower())
    if user is None:
        return None

    await session.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))

    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now(UTC) + _RESET_TOKEN_TTL

    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(reset_token)
    await session.commit()
    return raw_token, expires_at


async def consume_reset_token(session: AsyncSession, *, token: str, new_password: str) -> User:
    token_hash = _hash_token(token)
    result = await session.execute(
        select(PasswordResetToken)
        .options(selectinload(PasswordResetToken.user))
        .where(PasswordResetToken.token_hash == token_hash)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise ValueError("Invalid password reset token")
    if record.consumed_at is not None:
        raise ValueError("Password reset token already used")
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        raise ValueError("Password reset token has expired")

    user = record.user
    user.hashed_password = get_password_hash(new_password)
    record.consumed_at = datetime.now(UTC)
    session.add_all([user, record])
    await session.commit()
    return user
