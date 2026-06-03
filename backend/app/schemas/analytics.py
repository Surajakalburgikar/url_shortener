"""
app/schemas/analytics.py
────────────────────────
Pydantic v2 schemas for analytics responses.

These schemas shape the data returned by the analytics endpoints.
The service layer aggregates raw Click records into these structured summaries.
"""

from pydantic import BaseModel


class DailyClick(BaseModel):
    """Clicks for a single day — used to plot the line chart in the frontend."""
    date: str          # ISO format: "2024-01-15"
    click_count: int


class TopReferrer(BaseModel):
    """A single referrer domain and its click count."""
    referrer: str      # e.g. "twitter.com" or "direct" (no referrer header)
    click_count: int


class TopCountry(BaseModel):
    """A single country and its click count."""
    country: str       # 2-letter ISO code, e.g. "IN", "US", or "Unknown"
    click_count: int


class LinkAnalyticsResponse(BaseModel):
    """
    Full analytics for one specific short link.
    Returned by GET /api/v1/analytics/{short_code}
    """
    short_code: str
    original_url: str
    total_clicks: int
    clicks_per_day: list[DailyClick]      # Last 30 days — for the line chart
    top_referrers: list[TopReferrer]      # Top 5 referrer domains
    top_countries: list[TopCountry]       # Top 5 countries


class UserAnalyticsResponse(BaseModel):
    """
    Aggregate analytics across ALL of a user's links.
    Returned by GET /api/v1/analytics/me
    """
    total_links: int
    total_clicks: int
    clicks_per_day: list[DailyClick]      # Last 30 days across all links
    top_referrers: list[TopReferrer]      # Top 5 referrers across all links
    top_countries: list[TopCountry]       # Top 5 countries across all links
