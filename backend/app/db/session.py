"""Database session and engine helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_engine_cache: dict[str, AsyncEngine] = {}
_sessionmaker_cache: dict[str, async_sessionmaker[AsyncSession]] = {}


def _resolve_database_url(override: str | None = None) -> str:
    settings = get_settings()
    return override or settings.database_url


def get_sessionmaker(
    database_url: str | None = None,
) -> async_sessionmaker[AsyncSession]:
    """Return (and cache) an async sessionmaker for the given database URL."""
    url = _resolve_database_url(database_url)
    sessionmaker = _sessionmaker_cache.get(url)
    if sessionmaker is None:
        engine = create_async_engine(url, echo=False, future=True)
        sessionmaker = async_sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )
        _engine_cache[url] = engine
        _sessionmaker_cache[url] = sessionmaker
    return sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an async database session using the configured engine."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        yield session


async def dispose_engine(database_url: str | None = None) -> None:
    """Dispose the cached engine/sessionmaker for the given database URL."""
    url = _resolve_database_url(database_url)
    engine = _engine_cache.pop(url, None)
    if engine is not None:
        await engine.dispose()
    _sessionmaker_cache.pop(url, None)
