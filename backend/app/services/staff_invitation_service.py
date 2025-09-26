"""Services for managing staff invitations."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.staff_invitation import StaffInvitation, StaffInvitationStatus
from app.models.user import UserStatus
from app.schemas.user import StaffInvitationCreate, UserCreate


def _coerce_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


if TYPE_CHECKING:  # pragma: no cover - imported for type checking only
    from app.models.user import User


async def list_invitations(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
) -> list[StaffInvitation]:
    """Return invitations for an account ordered by creation time."""
    stmt = (
        select(StaffInvitation)
        .where(StaffInvitation.account_id == account_id)
        .order_by(StaffInvitation.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def create_invitation(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    invited_by_user_id: uuid.UUID | None,
    payload: StaffInvitationCreate,
    expires_in_hours: int,
) -> tuple[StaffInvitation, str]:
    """Create an invitation and return it alongside the raw token."""
    from app.services import user_service  # local import to avoid cycle

    existing_user = await user_service.get_user_by_email(
        session, email=payload.email.lower()
    )
    if existing_user is not None:
        raise ValueError("User with this email already exists")

    pending_stmt = select(StaffInvitation).where(
        StaffInvitation.account_id == account_id,
        StaffInvitation.email == payload.email.lower(),
        StaffInvitation.status == StaffInvitationStatus.PENDING,
    )
    existing_invitation = (await session.execute(pending_stmt)).scalar_one_or_none()
    if existing_invitation is not None:
        existing_invitation.status = StaffInvitationStatus.REVOKED
        await session.flush()

    while True:
        raw_token = secrets.token_urlsafe(32)
        token_prefix = raw_token[:16]
        existing_token = await session.execute(
            select(StaffInvitation.id).where(
                StaffInvitation.token_prefix == token_prefix
            )
        )
        if existing_token.scalar_one_or_none() is None:
            break
    token_hash = get_password_hash(raw_token)

    invitation = StaffInvitation(
        account_id=account_id,
        invited_by_user_id=invited_by_user_id,
        email=payload.email.lower(),
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone_number=payload.phone_number,
        role=payload.role,
        status=StaffInvitationStatus.PENDING,
        token_hash=token_hash,
        token_prefix=token_prefix,
        expires_at=datetime.now(UTC) + timedelta(hours=expires_in_hours),
    )
    session.add(invitation)
    await session.commit()
    await session.refresh(invitation)
    return invitation, raw_token


async def accept_invitation(
    session: AsyncSession,
    *,
    token: str,
    password: str,
    first_name: str | None = None,
    last_name: str | None = None,
    phone_number: str | None = None,
) -> tuple[StaffInvitation, "User"]:
    """Consume an invitation token and create the corresponding user."""
    from app.services import user_service  # local import to avoid cycle

    if len(token) < 16:
        raise ValueError("Invalid invitation token")
    token_prefix = token[:16]
    stmt = select(StaffInvitation).where(StaffInvitation.token_prefix == token_prefix)
    invitation = (await session.execute(stmt)).scalar_one_or_none()
    if invitation is None:
        raise ValueError("Invitation not found")

    if invitation.status != StaffInvitationStatus.PENDING:
        raise ValueError("Invitation is no longer valid")

    expires_at = _coerce_utc(invitation.expires_at)
    if expires_at < datetime.now(UTC):
        invitation.status = StaffInvitationStatus.EXPIRED
        await session.commit()
        raise ValueError("Invitation has expired")

    if not verify_password(token, invitation.token_hash):
        raise ValueError("Invalid invitation token")

    existing_user = await user_service.get_user_by_email(
        session, email=invitation.email
    )
    if existing_user is not None:
        invitation.status = StaffInvitationStatus.REVOKED
        await session.commit()
        raise ValueError("User already exists for this invitation")

    user_payload = UserCreate(
        email=invitation.email,
        password=password,
        account_id=invitation.account_id,
        first_name=first_name or invitation.first_name,
        last_name=last_name or invitation.last_name,
        phone_number=phone_number or invitation.phone_number,
        role=invitation.role,
        status=UserStatus.ACTIVE,
        is_primary_contact=False,
    )
    user = await user_service.create_user(session, user_payload)

    invitation.status = StaffInvitationStatus.ACCEPTED
    invitation.accepted_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(invitation)
    return invitation, user


async def update_invitation_status(
    session: AsyncSession,
    *,
    invitation: StaffInvitation,
    status: StaffInvitationStatus,
) -> StaffInvitation:
    """Update the status on an invitation."""
    invitation.status = status
    if status == StaffInvitationStatus.ACCEPTED:
        invitation.accepted_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(invitation)
    return invitation
