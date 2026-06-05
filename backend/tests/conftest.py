"""
tests/conftest.py
──────────────────
Configuration file for pytest using AnyIO.
"""

from typing import AsyncGenerator

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.database import Base, get_db
from app.main import app

# Ensure we are using the test environment and test database
settings.app_env = "testing"
assert "test" in settings.test_database_url, "TEST_DATABASE_URL must point to a test database!"

# Create engine for test database with NullPool
test_engine = create_async_engine(
    settings.test_database_url,
    echo=False,
    poolclass=NullPool,
)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Specify the backend for AnyIO to use. Must be session scoped to support session async fixtures."""
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db() -> AsyncGenerator[None, None]:
    """Automatically creates all tables before tests run and drops them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides a transactional database session for a single test."""
    async with test_engine.connect() as connection:
        transaction = await connection.begin()
        async with TestingSessionLocal(bind=connection) as session:
            yield session
            await session.close()
        await transaction.rollback()


@pytest.fixture(autouse=True)
async def override_get_db(db_session: AsyncSession) -> None:
    """Overrides the get_db dependency in the FastAPI app with the test DB session."""
    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provides an HTTPX AsyncClient for requesting API endpoints."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
