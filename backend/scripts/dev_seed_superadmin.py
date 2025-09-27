from __future__ import annotations

import asyncio
import os
import uuid

from sqlalchemy import select

from app.db.session import async_session_maker
from app.models.user import User, UserRole, UserStatus
from app.core.security import get_password_hash

EMAIL = os.environ.get("DEV_SUPERADMIN_EMAIL", "admin@eipr.local")
PASSWORD = os.environ.get("DEV_SUPERADMIN_PASS", "admin123")


async def main() -> None:
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.email == EMAIL))
        user = result.scalars().first()
        if user is None:
            user = User(
                id=uuid.uuid4(),
                account_id=None,  # placeholder until bootstrap assigns
                email=EMAIL,
                hashed_password=get_password_hash(PASSWORD),
                first_name="Admin",
                last_name="User",
                role=UserRole.SUPERADMIN,
                status=UserStatus.ACTIVE,
            )
            session.add(user)
            await session.commit()
            print(f"Created superadmin {EMAIL} / {PASSWORD}")
        else:
            print(f"Superadmin {EMAIL} already exists")


if __name__ == "__main__":
    asyncio.run(main())
