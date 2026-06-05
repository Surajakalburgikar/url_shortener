"""
tests/test_analytics.py
────────────────────────
Tests for analytics retrieval endpoints, cookie-based authentication, and oauth exchange.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.link import Link
from app.models.click import Click

pytestmark = pytest.mark.anyio


async def test_cookie_based_auth(client: AsyncClient) -> None:
    """Test login sets cookies and auth works using access_token cookie instead of headers."""
    register_payload = {
        "email": "cookieuser@example.com",
        "password": "password12345",
    }
    await client.post("/api/v1/auth/register", json=register_payload)

    login_payload = {
        "email": "cookieuser@example.com",
        "password": "password12345",
    }
    login_response = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_response.status_code == 200
    
    # Assert that access_token cookie is present in client's cookies
    assert "access_token" in client.cookies

    # Fetch profile without Authorization header — should read from cookie
    profile_response = await client.get("/api/v1/auth/me")
    assert profile_response.status_code == 200
    assert profile_response.json()["email"] == "cookieuser@example.com"


async def test_analytics_endpoints(client: AsyncClient, db_session: AsyncSession) -> None:
    """Test retrieving user-wide analytics and per-link analytics."""
    # Register & Login
    reg_payload = {"email": "analyticsuser@example.com", "password": "password12345"}
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create link
    payload = {"original_url": "https://www.youtube.com", "custom_alias": "ytb"}
    create_res = await client.post("/api/v1/links", json=payload, headers=headers)
    assert create_res.status_code == 201

    # Record some mock clicks directly in the database
    from app.models.click import Click
    import uuid
    from datetime import datetime, timezone
    
    link_id = uuid.UUID(create_res.json()["id"])
    
    click1 = Click(link_id=link_id, country="US", referrer="google.com", user_agent="Mozilla")
    click2 = Click(link_id=link_id, country="IN", referrer="twitter.com", user_agent="Chrome")
    
    db_session.add(click1)
    db_session.add(click2)
    await db_session.commit()

    # Query User-wide Analytics
    analytics_me_res = await client.get("/api/v1/analytics/me", headers=headers)
    assert analytics_me_res.status_code == 200
    data_me = analytics_me_res.json()
    assert data_me["total_clicks"] == 2
    assert len(data_me["clicks_per_day"]) >= 1

    # Query Specific Link Analytics
    analytics_link_res = await client.get("/api/v1/analytics/ytb", headers=headers)
    assert analytics_link_res.status_code == 200
    data_link = analytics_link_res.json()
    assert data_link["total_clicks"] == 2
    assert any(tc["country"] == "US" for tc in data_link["top_countries"])
    assert any(tc["country"] == "IN" for tc in data_link["top_countries"])
    assert any(tr["referrer"] == "google.com" for tr in data_link["top_referrers"])
    assert any(tr["referrer"] == "twitter.com" for tr in data_link["top_referrers"])


async def test_oauth_exchange_invalid_token(client: AsyncClient) -> None:
    """Test that posting an invalid exchange token to OAuth exchange endpoint returns 401."""
    payload = {"code": "invalid-exchange-token"}
    response = await client.post("/api/v1/auth/oauth/exchange", json=payload)
    assert response.status_code == 401
    assert "Invalid or expired" in response.json()["detail"]
