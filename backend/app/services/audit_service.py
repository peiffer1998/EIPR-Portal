"""Helper utilities for recording audit events."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import AuditEvent


async def record_event(
    session: AsyncSession,
    *,
    event_type: str,
    account_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    description: str | None = None,
    payload: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditEvent:
    """Persist an audit event and return it."""
    event = AuditEvent(
        account_id=account_id,
        user_id=user_id,
        event_type=event_type,
        description=description,
        payload=payload,
        ip_address=ip_address,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event
