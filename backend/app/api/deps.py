"""Common API dependencies."""

from __future__ import annotations

import uuid
from typing import Annotated
from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.user import User, UserRole, UserStatus
from app.models.owner_profile import OwnerProfile

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/token")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session."""
    async for session in get_session():
        yield session


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """Authenticate request via bearer token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
    except JWTError as exc:  # pragma: no cover - handled as HTTP 401
        raise credentials_exception from exc

    subject = payload.get("sub")
    if subject is None:
        raise credentials_exception

    try:
        user_id = uuid.UUID(subject)
    except (ValueError, TypeError) as exc:
        raise credentials_exception from exc

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or user.status != UserStatus.ACTIVE:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure the current user is active."""
    return current_user


async def get_current_owner_profile(
    session: AsyncSession, current_user: User
) -> OwnerProfile | None:
    """Return the owner profile for the current pet parent, if any."""
    if current_user.role != UserRole.PET_PARENT:
        return None
    result = await session.execute(
        select(OwnerProfile)
        .options(selectinload(OwnerProfile.pets))
        .where(OwnerProfile.user_id == current_user.id)
    )
    return result.scalar_one_or_none()
