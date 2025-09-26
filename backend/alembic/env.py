"""Alembic environment configuration."""

from __future__ import annotations

from logging.config import fileConfig
from os import environ

import sqlalchemy as sa
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url
from alembic import context

from app.core.config import get_settings
from app.db.base import Base
from app.models import *  # noqa: F401,F403

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

env_sync_url = environ.get("SYNC_DATABASE_URL")
env_database_url = environ.get("DATABASE_URL")

if env_sync_url:
    raw_url = env_sync_url
elif env_database_url:
    raw_url = env_database_url
else:
    settings = get_settings()
    raw_url = settings.sync_database_url or settings.database_url

url = make_url(raw_url)
if url.drivername in {"postgresql", "postgresql+asyncpg"}:
    url = url.set(drivername="postgresql+psycopg")
config.set_main_option("sqlalchemy.url", url.render_as_string(hide_password=False))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_pk_length=128,
        version_table_pk_type=sa.String(191),
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
        if connection.dialect.name == "postgresql":
            connection.exec_driver_sql(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'alembic_version'
                          AND column_name = 'version_num'
                          AND character_maximum_length < 191
                    ) THEN
                        ALTER TABLE alembic_version
                        ALTER COLUMN version_num TYPE VARCHAR(191);
                    ELSIF NOT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_name = 'alembic_version'
                    ) THEN
                        CREATE TABLE alembic_version (
                            version_num VARCHAR(191) NOT NULL,
                            PRIMARY KEY (version_num)
                        );
                    END IF;
                END
                $$;
                """
            )
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_pk_length=128,
            version_table_pk_type=sa.String(191),
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
