"""
alembic/env.py
──────────────
Alembic migration environment — runs before every `alembic upgrade` or `alembic downgrade`.

Why we customise this file:
- The default env.py uses synchronous SQLAlchemy.
- Our app uses ASYNC SQLAlchemy 2.0 (asyncpg driver).
- We must use run_sync() inside an async context to make migrations work.
- We read the DB URL from our Settings (which reads .env) — never hardcoded.

How migrations work:
1. You run `alembic revision --autogenerate -m "description"`
2. Alembic compares your ORM models (Base.metadata) to the actual DB schema
3. It generates a Python migration file with upgrade() and downgrade() functions
4. You run `alembic upgrade head` to apply all pending migrations
"""

import os
import sys

# Dynamically add the backend directory to sys.path so 'app' can be found during migration runs
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import our app's Base (has all table metadata) and settings (has DB URL)
from app.database import Base
from app.config import settings

# Import all models so Alembic can see all tables.
# If you forget to import a model here, Alembic won't detect it!
import app.models  # noqa: F401 — side effect import registers all models with Base

# Alembic Config object — gives access to values in alembic.ini
config = context.config

# Set up Python logging from the alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Tell Alembic about our schema — this is how autogenerate works.
# Base.metadata knows about every table because we imported all models above.
target_metadata = Base.metadata

# Override the sqlalchemy.url from alembic.ini with our actual DB URL from .env
# This is the correct pattern — credentials never live in alembic.ini
# Escape % characters in the URL (e.g. %40 for @) because configparser
# uses % for interpolation syntax. Doubling them (%% -> %) makes them literal.
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode — generates SQL without connecting to DB.
    Useful for generating SQL scripts to review before applying.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations synchronously within an async connection context."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode using our async engine.
    
    Why NullPool?
    Alembic runs as a one-off script, not a long-running server.
    NullPool creates a fresh connection for the migration and closes it
    immediately after — no connection pooling needed for a CLI tool.
    """
    import uuid
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4().hex}__",
        },
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations — called by Alembic CLI."""
    asyncio.run(run_async_migrations())


# Alembic calls one of these based on whether --sql flag is passed
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
