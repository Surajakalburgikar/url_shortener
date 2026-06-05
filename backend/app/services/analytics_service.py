"""
app/services/analytics_service.py
────────────────────────────────────
Business logic for analytics — aggregates click data.

This service is thin because the heavy lifting is done in ClickRepository.
Its job is to orchestrate the repository calls and assemble the response schema.
"""

import uuid
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.click_repo import ClickRepository
from app.repositories.link_repo import LinkRepository
from app.schemas.analytics import LinkAnalyticsResponse, UserAnalyticsResponse
from fastapi import HTTPException, status


class AnalyticsService:
    """Orchestrates analytics data aggregation."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.click_repo = ClickRepository(db)
        self.link_repo = LinkRepository(db)

    async def get_link_analytics(
        self,
        short_code: str,
        user_id: uuid.UUID,
    ) -> LinkAnalyticsResponse:
        """
        Get full analytics for one specific short link.
        Only the link owner can view analytics for their link.
        """
        link = await self.link_repo.get_by_short_code(short_code)

        if not link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Link not found",
            )

        if link.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view analytics for this link",
            )

        # Execute queries sequentially because SQLAlchemy AsyncSession is not concurrency-safe
        total_clicks = await self.click_repo.get_total_clicks_for_link(link.id)
        clicks_per_day = await self.click_repo.get_clicks_per_day(link.id)
        top_referrers = await self.click_repo.get_top_referrers(link.id)
        top_countries = await self.click_repo.get_top_countries(link.id)

        return LinkAnalyticsResponse(
            short_code=link.short_code,
            original_url=link.original_url,
            total_clicks=total_clicks,
            clicks_per_day=clicks_per_day,
            top_referrers=top_referrers,
            top_countries=top_countries,
        )

    async def get_user_analytics(self, user_id: uuid.UUID) -> UserAnalyticsResponse:
        """
        Get aggregate analytics across ALL of a user's links.
        Returned by GET /api/v1/analytics/me
        """
        total_links = await self.link_repo.count_user_links(user_id)

        # Execute queries sequentially because SQLAlchemy AsyncSession is not concurrency-safe
        total_clicks = await self.click_repo.get_total_clicks_for_user(user_id)
        clicks_per_day = await self.click_repo.get_clicks_per_day_for_user(user_id)
        top_referrers = await self.click_repo.get_top_referrers_for_user(user_id)
        top_countries = await self.click_repo.get_top_countries_for_user(user_id)

        return UserAnalyticsResponse(
            total_links=total_links,
            total_clicks=total_clicks,
            clicks_per_day=clicks_per_day,
            top_referrers=top_referrers,
            top_countries=top_countries,
        )
