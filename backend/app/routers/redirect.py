"""
app/routers/redirect.py
────────────────────────
The redirect endpoint — the hottest path in the entire application.

GET /{short_code} → 307 Temporary Redirect to original URL

Performance design:
1. Check Redis cache first (microseconds) — cache HIT returns immediately
2. Fall back to PostgreSQL only on cache MISS (milliseconds)
3. Click is recorded via BackgroundTask — AFTER the response is sent
   This means the redirect is instant regardless of DB write speed.

Why 307 (Temporary Redirect) instead of 301 (Permanent)?
- 301: Browser caches the redirect forever — if we delete the link, browsers
  will still redirect to the old URL because they cached it.
- 307: Browser always asks us — we can return 410 Gone for expired/deleted links.
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, get_db
from app.repositories.click_repo import ClickRepository
from app.services.link_service import LinkService

router = APIRouter(tags=["redirect"])


async def record_click(
    link_id: uuid.UUID,
    request: Request,
    db: AsyncSession | None = None,
) -> None:
    """
    Record a click event asynchronously.
    
    This runs AFTER the 307 redirect response is already sent to the user.
    The user's browser has already started loading the destination URL —
    they experience zero delay from this DB write.
    
    Why BackgroundTask instead of asyncio.create_task?
    BackgroundTask is managed by FastAPI/Starlette — it runs after the response
    is complete but before the connection closes, and it has proper error handling.
    """
    # Extract metadata from the request
    referrer = request.headers.get("referer") or request.headers.get("referrer")
    user_agent = request.headers.get("user-agent")
    client_ip = request.client.host if request.client else None

    # Trim referrer to just the domain (twitter.com, not full URL)
    if referrer:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(referrer)
            referrer = parsed.netloc or referrer
        except Exception:
            pass

    # Country detection from IP (simple approach — no external API needed)
    # In a real system, you'd use a MaxMind GeoIP database here
    country = None  # We'll leave this as None for now — can be enhanced later

    # If the request session is closed (production), create a fresh one.
    # If it is open/active (tests), reuse it to participate in the test transaction.
    session_to_use = db
    is_external_session = False
    
    if db:
        try:
            if db.is_active:
                is_external_session = True
        except Exception:
            pass

    if not is_external_session:
        session_to_use = AsyncSessionLocal()

    try:
        click_repo = ClickRepository(session_to_use)
        await click_repo.create_click(
            link_id=link_id,
            country=country,
            referrer=referrer,
            user_agent=user_agent,
            ip_address=client_ip,
        )
        await session_to_use.commit()
    except Exception as e:
        import logging
        logging.getLogger("uvicorn.error").error(f"Failed to record click: {e}")
        await session_to_use.rollback()
    finally:
        if not is_external_session:
            await session_to_use.close()


@router.get(
    "/{short_code}",
    summary="Redirect to original URL",
    description=(
        "Looks up the short code and redirects to the original URL. "
        "Returns 404 if the code doesn't exist, 410 if the link has expired. "
        "Click is recorded asynchronously after redirect."
    ),
    response_class=RedirectResponse,
    status_code=307,
)
async def redirect_to_url(
    short_code: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """
    The hot path — must be as fast as possible.
    
    Flow:
    1. LinkService.get_original_url() checks Redis, then DB
    2. We immediately return 307 redirect
    3. BackgroundTasks records the click AFTER response is sent
    """
    redis = None
    try:
        from app.main import redis_client
        redis = redis_client
    except Exception:
        pass

    service = LinkService(db=db, redis=redis)
    original_url, link_id = await service.get_original_url(short_code)

    # Schedule click recording — runs after this function returns the redirect
    background_tasks.add_task(record_click, link_id, request, db)

    return RedirectResponse(url=original_url, status_code=307)
