"""User data access helpers."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Return a user by email address."""
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Return a user by ID."""
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def list_users(session: AsyncSession, *, skip: int = 0, limit: int = 50) -> list[User]:
    """Return paginated users."""
    result = await session.execute(
        select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
    )
    return list(result.scalars().all())


async def create_user(session: AsyncSession, payload: UserCreate) -> User:
    """Persist a new user with hashed password."""
    hashed_password = get_password_hash(payload.password)
    user = User(
        account_id=payload.account_id,
        email=payload.email.lower(),
        hashed_password=hashed_password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone_number=payload.phone_number,
        role=payload.role,
        status=payload.status,
        is_primary_contact=payload.is_primary_contact,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise exc
    await session.refresh(user)
    return user


async def update_user(session: AsyncSession, user: User, payload: UserUpdate) -> User:
    """Update mutable fields on a user."""
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await session.commit()
    await session.refresh(user)
    return user
