"""Alembic environment configuration."""

from __future__ import annotations

from logging.config import fileConfig
from os import environ

from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url
from alembic import context

from app.core.config import get_settings
from app.db.base import Base
from app.models import *  # noqa: F401,F403

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
sync_url = settings.sync_database_url or settings.database_url
raw_url = environ.get("DATABASE_URL", sync_url)
url = make_url(raw_url)
if url.drivername == "postgresql":
    url = url.set(drivername="postgresql+psycopg")
config.set_main_option("sqlalchemy.url", str(url))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
