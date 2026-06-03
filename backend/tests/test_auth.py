"""
tests/test_auth.py
──────────────────
Tests for user registration, login, and JWT access token usage.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

pytestmark = pytest.mark.anyio


async def test_register_user_success(client: AsyncClient, db_session: AsyncSession) -> None:
    """Test successful user registration with email and password."""
    payload = {
        "email": "testuser@example.com",
        "password": "supersecurepassword123",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    # Verify user exists in the database
    result = await db_session.execute(
        select(User).where(User.email == "testuser@example.com")
    )
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.email == "testuser@example.com"
    assert user.hashed_password is not None


async def test_register_user_duplicate_email(client: AsyncClient) -> None:
    """Test registering with an email that already exists raises 409."""
    payload = {
        "email": "duplicate@example.com",
        "password": "password123",
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    assert res2.json()["detail"] == "An account with this email already exists"


async def test_login_success(client: AsyncClient) -> None:
    """Test logging in with valid credentials returns token pair."""
    register_payload = {
        "email": "loginuser@example.com",
        "password": "password12345",
    }
    await client.post("/api/v1/auth/register", json=register_payload)

    login_payload = {
        "email": "loginuser@example.com",
        "password": "password12345",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_login_invalid_credentials(client: AsyncClient) -> None:
    """Test login with wrong password returns 401."""
    register_payload = {
        "email": "wrongpass@example.com",
        "password": "password12345",
    }
    await client.post("/api/v1/auth/register", json=register_payload)

    login_payload = {
        "email": "wrongpass@example.com",
        "password": "wrongpassword",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


async def test_get_current_user_profile(client: AsyncClient) -> None:
    """Test fetching profile using a valid Bearer token."""
    payload = {
        "email": "profile@example.com",
        "password": "password12345",
    }
    res = await client.post("/api/v1/auth/register", json=payload)
    token = res.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "profile@example.com"
    assert "id" in data
    assert "hashed_password" not in data
