"""Staff notification helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification, NotificationType


async def notify(
    session: AsyncSession,
    *,
    account_id: UUID,
    user_id: UUID,
    type: NotificationType,
    title: str,
    body: str,
) -> UUID:
    notification = Notification(
        account_id=account_id,
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        created_at=datetime.now(UTC),
    )
    session.add(notification)
    await session.commit()
    return notification.id


async def list_for_user(
    session: AsyncSession,
    *,
    account_id: UUID,
    user_id: UUID,
    unread_only: bool = False,
) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(
            Notification.account_id == account_id,
            Notification.user_id == user_id,
        )
        .order_by(Notification.created_at.desc())
    )
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def mark_read(
    session: AsyncSession,
    *,
    notification_id: UUID,
    user_id: UUID,
) -> None:
    notification = await session.get(Notification, notification_id)
    if notification is None or notification.user_id != user_id:
        raise ValueError("Notification not found")
    notification.read_at = datetime.now(UTC)
    await session.commit()
