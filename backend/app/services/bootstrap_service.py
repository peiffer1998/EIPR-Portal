"""Bootstrap helpers for default data."""

from __future__ import annotations

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.models import Account, User, UserRole, UserStatus
from app.schemas.user import UserCreate
from app.services.user_service import create_user

DEFAULT_ACCOUNT_NAME = "Eastern Iowa Pet Resort"
DEFAULT_ACCOUNT_SLUG = "eipr"
DEFAULT_ADMIN_EMAIL = "peiffer1998@gmail.com"
DEFAULT_ADMIN_PASSWORD = "Madyn2020!"
DEFAULT_ADMIN_FIRST = "Shawn"
DEFAULT_ADMIN_LAST = "Peiffer"
DEFAULT_ADMIN_PHONE = "3194504027"


async def ensure_default_admin() -> None:
    """Create a default admin user if one does not yet exist."""

    settings = get_settings()
    sessionmaker = get_sessionmaker(settings.database_url)
    async with sessionmaker() as session:
        existing = await session.execute(
            select(User).where(User.email == DEFAULT_ADMIN_EMAIL.lower())
        )
        if existing.scalar_one_or_none() is not None:
            return

        account_result = await session.execute(
            select(Account).order_by(Account.created_at.asc()).limit(1)
        )
        account = account_result.scalar_one_or_none()
        if account is None:
            account = Account(name=DEFAULT_ACCOUNT_NAME, slug=DEFAULT_ACCOUNT_SLUG)
            session.add(account)
            await session.commit()
            await session.refresh(account)

        payload = UserCreate(
            account_id=account.id,
            email=DEFAULT_ADMIN_EMAIL,
            password=DEFAULT_ADMIN_PASSWORD,
            first_name=DEFAULT_ADMIN_FIRST,
            last_name=DEFAULT_ADMIN_LAST,
            phone_number=DEFAULT_ADMIN_PHONE,
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            is_primary_contact=True,
        )
        await create_user(session, payload)
