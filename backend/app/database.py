"""
app/database.py
───────────────
Async SQLAlchemy 2.0 database engine setup.

Key concepts:
- Engine: the connection to your database (like a phone line to PostgreSQL)
- SessionLocal: a factory that creates database sessions (like a conversation over that line)
- get_db(): a FastAPI dependency that opens a session, yields it to the endpoint,
  then closes it — even if an exception occurs (the `finally` block guarantees this)

Connection pooling explained:
- pool_size=20:      Keep 20 connections open and ready to reuse
- max_overflow=10:   Allow up to 10 extra connections when all 20 are busy
- pool_timeout=30:   Wait up to 30 seconds for a free connection before erroring
- pool_recycle=1800: Replace connections older than 30 minutes (prevents stale connections)
"""

import uuid
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# ── Engine ────────────────────────────────────────────────────────────────────
# create_async_engine uses asyncpg under the hood to make async DB calls.
# echo=True in development prints every SQL query to the console (helpful for debugging).
engine = create_async_engine(
    settings.database_url,
    echo=settings.is_development,  # Log SQL queries in dev, silent in production
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4().hex}__",
    },
)


# ── Session factory ───────────────────────────────────────────────────────────
# async_sessionmaker creates AsyncSession objects.
# expire_on_commit=False: after a commit, objects stay usable without a new DB query.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Base class for all ORM models ─────────────────────────────────────────────
# Every model (User, Link, Click) will inherit from this Base.
# SQLAlchemy uses it to know about all your tables.
class Base(DeclarativeBase):
    pass


# ── FastAPI dependency ─────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields a database session for the duration of one HTTP request.

    Usage in a FastAPI endpoint:
        from app.database import get_db
        from sqlalchemy.ext.asyncio import AsyncSession

        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            result = await db.execute(...)
            return result

    The `finally` block ensures the session is always closed,
    even if an unhandled exception occurs inside the endpoint.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

