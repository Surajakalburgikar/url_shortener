"""
app/routers/analytics.py
─────────────────────────
Analytics endpoints — returns click data for links and users.

Both endpoints are protected — you must be logged in to view analytics.
A user can only see analytics for their own links (enforced in the service layer).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.analytics import LinkAnalyticsResponse, UserAnalyticsResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/me",
    response_model=UserAnalyticsResponse,
    summary="My aggregate analytics",
    description=(
        "Returns total clicks, clicks per day (last 30 days), top referrers, "
        "and top countries across ALL of your short links."
    ),
)
async def get_my_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserAnalyticsResponse:
    service = AnalyticsService(db)
    return await service.get_user_analytics(user_id=current_user.id)


@router.get(
    "/{short_code}",
    response_model=LinkAnalyticsResponse,
    summary="Analytics for a specific link",
    description=(
        "Returns clicks per day, top referrers, and top countries for one specific short link. "
        "Only the link owner can view this."
    ),
)
async def get_link_analytics(
    short_code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LinkAnalyticsResponse:
    service = AnalyticsService(db)
    return await service.get_link_analytics(
        short_code=short_code,
        user_id=current_user.id,
    )
