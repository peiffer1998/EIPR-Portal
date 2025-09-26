"""SMS conversation helpers for outbound and inbound messaging."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models import (
    OwnerProfile,
    SMSConversation,
    SMSDirection,
    SMSMessage,
    SMSStatus,
)

logger = logging.getLogger(__name__)


_PHONE_CLEAN_RE = re.compile(r"[^0-9+]")


def normalize_phone(raw: str) -> str:
    """Normalize a phone number to E.164 format (US default)."""

    if not raw:
        raise ValueError("Phone number is required")
    cleaned = _PHONE_CLEAN_RE.sub("", raw)
    if cleaned.startswith("+"):
        digits = cleaned[1:]
    else:
        digits = cleaned
    if digits.startswith("1") and len(digits) == 11:
        return "+" + digits
    if len(digits) == 10:
        return "+1" + digits
    if cleaned.startswith("+") and len(digits) >= 8:
        return "+" + digits
    raise ValueError("Unsupported phone number format")


async def _load_owner(session: AsyncSession, owner_id: UUID) -> OwnerProfile:
    stmt = (
        select(OwnerProfile)
        .options(selectinload(OwnerProfile.user))
        .where(OwnerProfile.id == owner_id)
    )
    result = await session.execute(stmt)
    owner = result.scalar_one_or_none()
    if owner is None or owner.user is None:
        raise ValueError("Owner not found")
    return owner


async def ensure_conversation(
    session: AsyncSession,
    *,
    account_id: UUID,
    owner_id: UUID,
    phone_e164: str,
) -> UUID:
    stmt = select(SMSConversation).where(
        SMSConversation.account_id == account_id,
        SMSConversation.owner_id == owner_id,
        SMSConversation.phone_e164 == phone_e164,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing:
        return existing.id

    conversation = SMSConversation(
        account_id=account_id,
        owner_id=owner_id,
        phone_e164=phone_e164,
        last_message_at=datetime.now(UTC),
    )
    session.add(conversation)
    await session.flush()
    return conversation.id


async def send_sms(
    session: AsyncSession,
    *,
    owner_id: UUID,
    body: str,
) -> UUID:
    owner = await _load_owner(session, owner_id)
    if not owner.sms_opt_in:
        raise ValueError("Owner has opted out of SMS communication")
    phone_raw: Optional[str] = owner.user.phone_number
    if not phone_raw:
        raise ValueError("Owner does not have a phone number")
    phone_e164 = normalize_phone(phone_raw)

    conversation_id = await ensure_conversation(
        session,
        account_id=owner.user.account_id,
        owner_id=owner_id,
        phone_e164=phone_e164,
    )

    settings = get_settings()
    echo_mode = getattr(settings, "dev_sms_echo", settings.app_env != "production")
    has_twilio = (
        getattr(settings, "twilio_account_sid", None)
        and getattr(settings, "twilio_auth_token", None)
        and getattr(settings, "twilio_messaging_service_sid", None)
    )
    status = SMSStatus.SENT if (echo_mode or not has_twilio) else SMSStatus.QUEUED

    message = SMSMessage(
        conversation_id=conversation_id,
        direction=SMSDirection.OUTBOUND,
        body=body,
        status=status,
        created_at=datetime.now(UTC),
    )
    session.add(message)

    await session.execute(
        select(SMSConversation)
        .where(SMSConversation.id == conversation_id)
        .execution_options(populate_existing=True)
    )
    conversation = await session.get(SMSConversation, conversation_id)
    if conversation is not None:
        conversation.last_message_at = datetime.now(UTC)

    await session.commit()
    return message.id


async def record_inbound(
    session: AsyncSession,
    *,
    account_id: UUID,
    owner_id: UUID,
    phone_e164: str,
    body: str,
    provider_message_id: str | None = None,
) -> UUID:
    conversation_id = await ensure_conversation(
        session,
        account_id=account_id,
        owner_id=owner_id,
        phone_e164=phone_e164,
    )

    message = SMSMessage(
        conversation_id=conversation_id,
        direction=SMSDirection.INBOUND,
        body=body,
        status=SMSStatus.RECEIVED,
        provider_message_id=provider_message_id,
        created_at=datetime.now(UTC),
    )
    session.add(message)

    conversation = await session.get(SMSConversation, conversation_id)
    if conversation is not None:
        conversation.last_message_at = datetime.now(UTC)

    await session.commit()
    return message.id
