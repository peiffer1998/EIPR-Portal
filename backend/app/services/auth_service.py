"""Authentication service helpers."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.models.user import User, UserStatus
from app.schemas.user import UserCreate
from app.services import user_service


async def authenticate_user(
    session: AsyncSession, email: str, password: str
) -> User | None:
    """Validate credentials and return a user if correct."""
    user = await user_service.get_user_by_email(session, email=email.lower())
    if user is None:
        return None
    if user.status != UserStatus.ACTIVE:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def create_access_token_for_user(user: User) -> str:
    """Generate a JWT for a user."""
    return create_access_token(str(user.id), role=user.role.value)


async def bootstrap_superuser(session: AsyncSession, payload: UserCreate) -> User:
    """Create the first superuser if none exists."""
    existing = await user_service.get_user_by_email(session, email=payload.email)
    if existing:
        return existing
    return await user_service.create_user(session, payload)
