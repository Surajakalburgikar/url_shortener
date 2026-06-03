"""
app/repositories/link_repo.py
──────────────────────────────
Data Access Layer for the Link entity.

Contains all DB queries for short links:
- Looking up by short_code (hot path — every redirect)
- Listing a user's links with pagination
- Creating and deleting links
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.link import Link


class LinkRepository:
    """All database operations for the Link table."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_short_code(self, short_code: str) -> Link | None:
        """
        THE hottest query in the entire application.
        Called on every redirect request.
        Uses the unique index on short_code — O(log n).
        """
        result = await self.db.execute(
            select(Link).where(Link.short_code == short_code)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, link_id: uuid.UUID) -> Link | None:
        result = await self.db.execute(
            select(Link).where(Link.id == link_id)
        )
        return result.scalar_one_or_none()

    async def short_code_exists(self, short_code: str) -> bool:
        """Check if a short code is already taken — used before creating with custom alias."""
        result = await self.db.execute(
            select(Link.id).where(Link.short_code == short_code)
        )
        return result.scalar_one_or_none() is not None

    async def get_user_links(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Link], int]:
        """
        List all links for a user, paginated, sorted newest first.
        Uses the composite index on (user_id, created_at).
        Returns (list_of_links, total_count).
        """
        base_query = select(Link).where(Link.user_id == user_id)

        # Get total count for pagination metadata
        count_result = await self.db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar_one()

        # Get paginated results
        offset = (page - 1) * page_size
        result = await self.db.execute(
            base_query.order_by(Link.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        links = list(result.scalars().all())

        return links, total

    async def create(
        self,
        short_code: str,
        original_url: str,
        user_id: uuid.UUID | None = None,
        expires_at: datetime | None = None,
    ) -> Link:
        """Create a new short link."""
        link = Link(
            short_code=short_code,
            original_url=original_url,
            user_id=user_id,
            expires_at=expires_at,
        )
        self.db.add(link)
        await self.db.flush()
        await self.db.refresh(link)
        return link

    async def delete(self, link: Link) -> None:
        """Delete a link (and cascade-deletes all its clicks via DB constraint)."""
        await self.db.delete(link)
        await self.db.flush()

    async def get_click_count(self, link_id: uuid.UUID) -> int:
        """Get total click count for a single link."""
        from app.models.click import Click
        result = await self.db.execute(
            select(func.count(Click.id)).where(Click.link_id == link_id)
        )
        return result.scalar_one() or 0
