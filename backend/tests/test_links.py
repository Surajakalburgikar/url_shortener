"""
tests/test_links.py
───────────────────
Tests for URL shortening creation, retrieval, listing, safety checks, and deletion.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.link import Link

pytestmark = pytest.mark.anyio


async def test_create_link_anonymous(client: AsyncClient, db_session: AsyncSession) -> None:
    """Test creating a short link anonymously (no login token required)."""
    payload = {
        "original_url": "https://www.google.com",
    }
    response = await client.post("/api/v1/links", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert "short_code" in data
    assert data["original_url"] == "https://www.google.com/"
    assert data["user_id"] is None

    result = await db_session.execute(
        select(Link).where(Link.short_code == data["short_code"])
    )
    link = result.scalar_one_or_none()
    assert link is not None
    assert link.original_url == "https://www.google.com/"


async def test_create_link_authenticated(client: AsyncClient) -> None:
    """Test creating a short link with a user account."""
    reg_payload = {"email": "linkowner@example.com", "password": "password123"}
    res = await client.post("/api/v1/auth/register", json=reg_payload)
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "original_url": "https://github.com",
        "custom_alias": "my-github-link",
    }
    response = await client.post("/api/v1/links", json=payload, headers=headers)
    assert response.status_code == 201

    data = response.json()
    assert data["short_code"] == "my-github-link"
    assert data["user_id"] is not None


async def test_create_link_invalid_url(client: AsyncClient) -> None:
    """Test shortening an invalid format URL triggers validation error."""
    payload = {
        "original_url": "not-a-valid-url",
    }
    response = await client.post("/api/v1/links", json=payload)
    assert response.status_code == 422


async def test_create_link_blocked_host(client: AsyncClient) -> None:
    """Test shortening a private/local IP URL (SSRF safety blocker) returns 422."""
    payload = {
        "original_url": "http://localhost:5432/db",
    }
    response = await client.post("/api/v1/links", json=payload)
    assert response.status_code == 422
    assert "private or local address" in response.json()["detail"]


async def test_delete_link_unauthorized(client: AsyncClient) -> None:
    """Test that a user cannot delete a link owned by another user."""
    res_a = await client.post("/api/v1/auth/register", json={"email": "usera@example.com", "password": "password123"})
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
    link_res = await client.post("/api/v1/links", json={"original_url": "https://netflix.com"}, headers=headers_a)
    short_code = link_res.json()["short_code"]

    res_b = await client.post("/api/v1/auth/register", json={"email": "userb@example.com", "password": "password123"})
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    response = await client.delete(f"/api/v1/links/{short_code}", headers=headers_b)
    assert response.status_code == 403


async def test_delete_link_success(client: AsyncClient, db_session: AsyncSession) -> None:
    """Test that a user can successfully delete their own link."""
    reg_payload = {"email": "owner@example.com", "password": "password123"}
    res = await client.post("/api/v1/auth/register", json=reg_payload)
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create link
    payload = {"original_url": "https://www.wikipedia.org", "custom_alias": "wiki-link"}
    create_res = await client.post("/api/v1/links", json=payload, headers=headers)
    assert create_res.status_code == 201
    short_code = create_res.json()["short_code"]

    # Delete link
    delete_res = await client.delete(f"/api/v1/links/{short_code}", headers=headers)
    assert delete_res.status_code == 204

    # Verify link is gone from DB
    result = await db_session.execute(
        select(Link).where(Link.short_code == short_code)
    )
    link = result.scalar_one_or_none()
    assert link is None
