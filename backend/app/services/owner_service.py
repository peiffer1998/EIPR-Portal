"""Owner management service helpers."""
from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.sql import Select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_password_hash
from app.models.owner_profile import OwnerProfile
from app.models.user import User, UserRole, UserStatus


def _base_owner_query(account_id: uuid.UUID) -> Select[tuple[OwnerProfile]]:
    """Return a base selectable for owners scoped to an account."""
    return (
        select(OwnerProfile)
        .join(OwnerProfile.user)
        .options(selectinload(OwnerProfile.user))
        .where(User.account_id == account_id)
        .order_by(OwnerProfile.created_at.desc())
    )


async def list_owners(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> Sequence[OwnerProfile]:
    """Return paginated owners for an account."""
    stmt = _base_owner_query(account_id)
    stmt = stmt.offset(skip).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().unique().all()


async def get_owner(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> OwnerProfile | None:
    """Return a single owner scoped to the account."""
    stmt = _base_owner_query(account_id)
    stmt = stmt.where(OwnerProfile.id == owner_id)
    result = await session.execute(stmt)
    return result.scalars().unique().one_or_none()


async def create_owner(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    phone_number: str | None,
    preferred_contact_method: str | None,
    notes: str | None,
    is_primary_contact: bool,
) -> OwnerProfile:
    """Create a pet-parent owner profile and linked user."""
    user = User(
        account_id=account_id,
        email=email.lower(),
        hashed_password=get_password_hash(password),
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
        role=UserRole.PET_PARENT,
        status=UserStatus.ACTIVE,
        is_primary_contact=is_primary_contact,
    )
    owner = OwnerProfile(
        user=user,
        preferred_contact_method=preferred_contact_method,
        notes=notes,
    )

    session.add(owner)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(owner)
    await session.refresh(owner, attribute_names=["user"])
    return owner


async def update_owner(
    session: AsyncSession,
    *,
    owner: OwnerProfile,
    account_id: uuid.UUID,
    email: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    phone_number: str | None = None,
    preferred_contact_method: str | None = None,
    notes: str | None = None,
    is_primary_contact: bool | None = None,
    password: str | None = None,
) -> OwnerProfile:
    """Apply changes to an owner and related user."""
    user = owner.user
    if user.account_id != account_id:
        raise ValueError("Owner does not belong to the provided account")

    if email is not None:
        user.email = email.lower()
    if first_name is not None:
        user.first_name = first_name
    if last_name is not None:
        user.last_name = last_name
    if phone_number is not None:
        user.phone_number = phone_number
    if password is not None:
        user.hashed_password = get_password_hash(password)
    if is_primary_contact is not None:
        user.is_primary_contact = is_primary_contact

    if preferred_contact_method is not None:
        owner.preferred_contact_method = preferred_contact_method
    if notes is not None:
        owner.notes = notes

    session.add(owner)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(owner)
    await session.refresh(owner, attribute_names=["user"])
    return owner
