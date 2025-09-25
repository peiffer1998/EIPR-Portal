"""Test fixtures for the EIPR backend."""
from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import dispose_engine, get_sessionmaker
from app.main import app
from app.models import (
    Account,
    Location,
    LocationCapacityRule,
    ReservationType,
    User,
    UserRole,
    UserStatus,
)


@pytest.fixture(scope="session")
def db_url(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Provide a temporary SQLite database URL for the test session."""
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    return f"sqlite+aiosqlite:///{db_path}"


@pytest_asyncio.fixture()
async def reset_database(db_url: str) -> AsyncIterator[None]:
    """Drop and recreate the database schema for an isolated test."""
    os.environ["DATABASE_URL"] = db_url
    get_settings.cache_clear()
    get_settings()

    await dispose_engine(db_url)
    engine = create_async_engine(db_url, future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()
    yield
    await dispose_engine(db_url)


@pytest_asyncio.fixture()
async def app_context(reset_database: AsyncIterator[None], db_url: str) -> AsyncIterator[dict[str, object]]:
    """Yield an async client and seeded account data."""
    sessionmaker = get_sessionmaker(db_url)
    manager_password = "Passw0rd!"

    async with sessionmaker() as session:
        account = Account(name="Test Resort", slug=f"test-{uuid.uuid4().hex[:8]}")
        session.add(account)
        await session.flush()

        location = Location(
            account_id=account.id,
            name="Cedar Rapids",
            timezone="UTC",
        )
        session.add(location)
        await session.flush()

        for reservation_type in ReservationType:
            session.add(
                LocationCapacityRule(
                    location_id=location.id,
                    reservation_type=reservation_type,
                    max_active=1,
                )
            )

        manager = User(
            account_id=account.id,
            email="manager@example.com",
            hashed_password=get_password_hash(manager_password),
            first_name="Casey",
            last_name="Manager",
            role=UserRole.MANAGER,
            status=UserStatus.ACTIVE,
        )
        session.add(manager)

        superadmin_password = "Sup3rPass!"
        superadmin = User(
            account_id=account.id,
            email="seed.superadmin@example.com",
            hashed_password=get_password_hash(superadmin_password),
            first_name="Sam",
            last_name="Super",
            role=UserRole.SUPERADMIN,
            status=UserStatus.ACTIVE,
        )
        session.add(superadmin)
        await session.commit()

        context = {
            "account_id": account.id,
            "account_slug": account.slug,
            "location_id": location.id,
            "manager_email": manager.email,
            "manager_password": manager_password,
            "superadmin_email": superadmin.email,
            "superadmin_password": superadmin_password,
        }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        context["client"] = client
        yield context
