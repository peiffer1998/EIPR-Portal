from __future__ import annotations

import asyncio
import uuid

import bcrypt
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_sessionmaker

EMAIL = "admin@eipr.local"
PASSWORD = "admin123"


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def main() -> None:
    settings = get_settings()
    sessionmaker = get_sessionmaker(settings.database_url)
    async with sessionmaker() as session:
        existing = await session.execute(
            text("SELECT 1 FROM users WHERE email = :email"), {"email": EMAIL}
        )
        if existing.first():
            print(f"User {EMAIL} already exists")
            return

        account_id = uuid.uuid4()
        location_id = uuid.uuid4()
        user_id = uuid.uuid4()

        await session.execute(
            text(
                "INSERT INTO accounts (id, name, slug, created_at, updated_at) "
                "VALUES (:id, :name, :slug, NOW(), NOW())"
            ),
            {"id": account_id, "name": "Dev Resort", "slug": "dev-resort"},
        )

        await session.execute(
            text(
                "INSERT INTO locations (id, account_id, name, timezone, created_at, updated_at) "
                "VALUES (:id, :account_id, :name, :tz, NOW(), NOW())"
            ),
            {"id": location_id, "account_id": account_id, "name": "Main", "tz": "UTC"},
        )

        await session.execute(
            text(
                "INSERT INTO users (id, account_id, email, hashed_password, first_name, last_name, role, status, is_primary_contact, created_at, updated_at) "
                "VALUES (:id, :account_id, :email, :pw, :first, :last, CAST(:role AS userrole), CAST(:status AS userstatus), :primary, NOW(), NOW())"
            ),
            {
                "id": user_id,
                "account_id": account_id,
                "email": EMAIL,
                "pw": _hash_password(PASSWORD),
                "first": "Dev",
                "last": "Admin",
                "role": "superadmin",
                "status": "active",
                "primary": False,
            },
        )

        await session.commit()
        print(f"Created account dev-resort and superadmin {EMAIL} / {PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())
