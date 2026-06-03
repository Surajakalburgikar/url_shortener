"""
tests/test_redirect.py
───────────────────────
Tests the URL redirect functionality and background click tracking.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.click import Click
from app.models.link import Link

pytestmark = pytest.mark.anyio


async def test_redirect_successful(client: AsyncClient, db_session: AsyncSession) -> None:
    """Test GET /{short_code} successfully redirects to original URL and tracks click."""
    payload = {
        "original_url": "https://www.wikipedia.org",
        "custom_alias": "wiki",
    }
    create_res = await client.post("/api/v1/links", json=payload)
    assert create_res.status_code == 201

    # Include a Referer header to test netloc parsing
    headers = {"Referer": "https://twitter.com/some/path"}
    response = await client.get("/wiki", headers=headers, follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "https://www.wikipedia.org/"

    # Verify a Click event was persisted in the database
    result = await db_session.execute(
        select(Click).join(Link).where(Link.short_code == "wiki")
    )
    clicks = list(result.scalars().all())
    assert len(clicks) == 1
    # The referrer should be parsed to just the domain
    assert clicks[0].referrer == "twitter.com"


async def test_redirect_not_found(client: AsyncClient) -> None:
    """Test redirecting on a non-existent short code returns 404."""
    response = await client.get("/thiscodedoesnotexist")
    assert response.status_code == 404
