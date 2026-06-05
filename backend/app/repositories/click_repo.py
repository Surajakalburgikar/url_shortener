"""
app/repositories/click_repo.py
───────────────────────────────
Data Access Layer for the Click entity — powers all analytics.

All analytics queries live here. These are aggregate queries
(GROUP BY, COUNT, DATE_TRUNC) that use the composite index
on (link_id, clicked_at) for performance.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.click import Click
from app.models.link import Link
from app.schemas.analytics import DailyClick, TopCountry, TopReferrer


class ClickRepository:
    """All database operations for the Click table and analytics aggregations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_click(
        self,
        link_id: uuid.UUID,
        country: str | None = None,
        referrer: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> Click:
        """
        Record a single click event.
        Called from a BackgroundTask — never blocks the redirect response.
        """
        click = Click(
            link_id=link_id,
            country=country,
            referrer=referrer,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.db.add(click)
        await self.db.flush()
        return click

    async def get_total_clicks_for_link(self, link_id: uuid.UUID) -> int:
        """Total click count for one link."""
        result = await self.db.execute(
            select(func.count(Click.id)).where(Click.link_id == link_id)
        )
        return result.scalar_one() or 0

    async def get_clicks_per_day(
        self,
        link_id: uuid.UUID,
        days: int = 30,
    ) -> list[DailyClick]:
        """
        Clicks grouped by day for the last N days.
        Uses DATE_TRUNC to group timestamps to day-level.
        Uses the composite index on (link_id, clicked_at).
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(
                func.date_trunc(text("'day'"), Click.clicked_at).label("day"),
                func.count(Click.id).label("count"),
            )
            .where(Click.link_id == link_id)
            .where(Click.clicked_at >= since)
            .group_by(func.date_trunc(text("'day'"), Click.clicked_at))
            .order_by(func.date_trunc(text("'day'"), Click.clicked_at))
        )

        return [
            DailyClick(date=row.day.date().isoformat(), click_count=row.count)
            for row in result.all()
        ]

    async def get_top_referrers(
        self,
        link_id: uuid.UUID,
        limit: int = 5,
    ) -> list[TopReferrer]:
        """Top N referrer domains for a link."""
        result = await self.db.execute(
            select(
                func.coalesce(Click.referrer, "direct").label("referrer"),
                func.count(Click.id).label("count"),
            )
            .where(Click.link_id == link_id)
            .group_by(text("referrer"))
            .order_by(text("count DESC"))
            .limit(limit)
        )
        return [
            TopReferrer(referrer=row.referrer, click_count=row.count)
            for row in result.all()
        ]

    async def get_top_countries(
        self,
        link_id: uuid.UUID,
        limit: int = 5,
    ) -> list[TopCountry]:
        """Top N countries for a link."""
        result = await self.db.execute(
            select(
                func.coalesce(Click.country, "Unknown").label("country"),
                func.count(Click.id).label("count"),
            )
            .where(Click.link_id == link_id)
            .group_by(text("country"))
            .order_by(text("count DESC"))
            .limit(limit)
        )
        return [
            TopCountry(country=row.country, click_count=row.count)
            for row in result.all()
        ]

    # ── User-level aggregates (across ALL their links) ────────────────────────

    async def get_total_clicks_for_user(self, user_id: uuid.UUID) -> int:
        """Total clicks across ALL of a user's links."""
        result = await self.db.execute(
            select(func.count(Click.id))
            .join(Link, Click.link_id == Link.id)
            .where(Link.user_id == user_id)
        )
        return result.scalar_one() or 0

    async def get_clicks_per_day_for_user(
        self,
        user_id: uuid.UUID,
        days: int = 30,
    ) -> list[DailyClick]:
        """Clicks grouped by day across ALL of a user's links."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(
                func.date_trunc(text("'day'"), Click.clicked_at).label("day"),
                func.count(Click.id).label("count"),
            )
            .join(Link, Click.link_id == Link.id)
            .where(Link.user_id == user_id)
            .where(Click.clicked_at >= since)
            .group_by(func.date_trunc(text("'day'"), Click.clicked_at))
            .order_by(func.date_trunc(text("'day'"), Click.clicked_at))
        )
        return [
            DailyClick(date=row.day.date().isoformat(), click_count=row.count)
            for row in result.all()
        ]

    async def get_top_referrers_for_user(
        self, user_id: uuid.UUID, limit: int = 5
    ) -> list[TopReferrer]:
        result = await self.db.execute(
            select(
                func.coalesce(Click.referrer, "direct").label("referrer"),
                func.count(Click.id).label("count"),
            )
            .join(Link, Click.link_id == Link.id)
            .where(Link.user_id == user_id)
            .group_by(text("referrer"))
            .order_by(text("count DESC"))
            .limit(limit)
        )
        return [
            TopReferrer(referrer=row.referrer, click_count=row.count)
            for row in result.all()
        ]

    async def get_top_countries_for_user(
        self, user_id: uuid.UUID, limit: int = 5
    ) -> list[TopCountry]:
        result = await self.db.execute(
            select(
                func.coalesce(Click.country, "Unknown").label("country"),
                func.count(Click.id).label("count"),
            )
            .join(Link, Click.link_id == Link.id)
            .where(Link.user_id == user_id)
            .group_by(text("country"))
            .order_by(text("count DESC"))
            .limit(limit)
        )
        return [
            TopCountry(country=row.country, click_count=row.count)
            for row in result.all()
        ]
