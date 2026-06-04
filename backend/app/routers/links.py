"""
app/routers/links.py
─────────────────────
Link management endpoints — create, list, delete short URLs.

Rate limiting:
- Anonymous users: 5 POST /api/v1/links per hour
- Authenticated users: 50 POST /api/v1/links per hour

Rate limiting is done via fastapi-limiter using Redis as the store.
The limit key includes the user's ID for authenticated users,
or the IP address for anonymous users.
"""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, get_optional_user
from app.models.user import User
from app.schemas.link import LinkCreate, LinkListResponse, LinkResponse
from app.services.link_service import LinkService

router = APIRouter(prefix="/links", tags=["links"])


def get_redis():
    """Get the Redis client from the app state."""
    from app.main import redis_client
    return redis_client


@router.post(
    "",
    response_model=LinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a short URL",
    description=(
        "Shorten any HTTP/HTTPS URL. "
        "Optionally provide a custom alias and/or expiry datetime. "
        "Works for anonymous users (no auth required) and authenticated users. "
        "Rate limited: 5/hr for anonymous, 50/hr for authenticated."
    ),
)
async def create_link(
    data: LinkCreate,
    request: Request,
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> LinkResponse:
    """
    Create a shortened URL.
    - Anonymous: link is created but not tied to any user account
    - Authenticated: link is owned by the user (appears in their dashboard)
    """
    # Rate limiting — check before processing
    await _check_rate_limit(request, current_user)

    redis = get_redis()
    service = LinkService(db=db, redis=redis)
    user_id = current_user.id if current_user else None
    return await service.create_link(data=data, user_id=user_id)


@router.get(
    "",
    response_model=LinkListResponse,
    summary="List my links",
    description="Returns a paginated list of all short links created by the current user.",
)
async def list_links(
    page: int = Query(default=1, ge=1, description="Page number (starts at 1)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LinkListResponse:
    redis = get_redis()
    service = LinkService(db=db, redis=redis)
    return await service.list_user_links(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )


@router.delete(
    "/{short_code}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a short link",
    description="Permanently deletes a short link and all its click analytics. Only the owner can delete.",
)
async def delete_link(
    short_code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    redis = get_redis()
    service = LinkService(db=db, redis=redis)
    await service.delete_link(short_code=short_code, user_id=current_user.id)


# ── Rate limiting helper ──────────────────────────────────────────────────────

async def _check_rate_limit(request: Request, user: User | None) -> None:
    """
    Enforce rate limits using Redis.
    
    Why manual implementation instead of fastapi-limiter decorator?
    The decorator approach can't differentiate limits by auth status.
    This gives us full control: 5/hr for anon, 50/hr for authenticated.
    """
    from fastapi import HTTPException
    from app.main import redis_client
    if not redis_client:
        return  # Skip rate limiting if Redis is not available (dev without Redis)

    try:
        # Build the rate limit key
        if user:
            key = f"ratelimit:links:user:{user.id}"
            limit = 50
        else:
            # Use client IP for anonymous rate limiting
            client_ip = request.client.host if request.client else "unknown"
            key = f"ratelimit:links:anon:{client_ip}"
            limit = 5

        # Increment counter and set 1-hour TTL if this is the first request
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, 3600)  # 1 hour window

        if count > limit:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. {'Authenticated' if user else 'Anonymous'} users can create {limit} links per hour.",
                headers={"Retry-After": "3600"},
            )
    except HTTPException:
        raise
    except Exception as e:
        import structlog
        log = structlog.get_logger()
        log.warning("ratelimit.redis_error", error=str(e))
        return  # Fail open

