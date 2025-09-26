"""Confirmation token helpers."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ConfirmationMethod, ConfirmationToken


async def create_token(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    reservation_id: uuid.UUID,
    method: str,
    sent_to: str | None,
    ttl_minutes: int,
) -> ConfirmationToken:
    """Generate and persist a confirmation token."""
    try:
        confirmation_method = ConfirmationMethod(method)
    except ValueError as exc:  # pragma: no cover - validated upstream
        raise ValueError("Unsupported confirmation method") from exc

    expires_at = datetime.now(UTC) + timedelta(minutes=ttl_minutes)
    token_value = await _generate_unique_token(session)
    token = ConfirmationToken(
        account_id=account_id,
        reservation_id=reservation_id,
        token=token_value,
        method=confirmation_method,
        sent_to=sent_to,
        expires_at=expires_at,
    )
    session.add(token)
    await session.commit()
    await session.refresh(token)
    return token


async def get_token(
    session: AsyncSession, token_value: str
) -> ConfirmationToken | None:
    result = await session.execute(
        select(ConfirmationToken).where(ConfirmationToken.token == token_value)
    )
    return result.scalar_one_or_none()


async def mark_confirmed(
    session: AsyncSession, token: ConfirmationToken
) -> ConfirmationToken:
    if token.confirmed_at is None:
        token.confirmed_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(token)
    return token


async def _generate_unique_token(session: AsyncSession) -> str:
    for _ in range(5):
        candidate = secrets.token_urlsafe(24)
        existing = await get_token(session, candidate)
        if existing is None:
            return candidate
    raise RuntimeError("Failed to generate unique confirmation token")
