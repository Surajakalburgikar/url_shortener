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
import structlog
import httpx

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Path
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal, get_db
from app.repositories.click_repo import ClickRepository
from app.services.link_service import LinkService

router = APIRouter(tags=["redirect"])
log = structlog.get_logger()

import geoip2.database
import geoip2.errors
import os

_geoip_reader = None

def get_geoip_reader():
    global _geoip_reader
    if _geoip_reader is None:
        paths = [
            "GeoLite2-Country.mmdb",
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "GeoLite2-Country.mmdb"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "GeoLite2-Country.mmdb"),
        ]
        for path in paths:
            if os.path.exists(path):
                try:
                    _geoip_reader = geoip2.database.Reader(path)
                    break
                except Exception:
                    pass
    return _geoip_reader


def resolve_country_from_ip(ip: str | None) -> str | None:
    """Resolve IP address to 2-letter country code using local GeoLite2 DB."""
    if not ip or ip in ("127.0.0.1", "::1", "localhost") or ip.startswith("192.168.") or ip.startswith("10."):
        return "LO"
    reader = get_geoip_reader()
    if not reader:
        return "ZZ"
    try:
        response = reader.country(ip)
        return response.country.iso_code or "ZZ"
    except geoip2.errors.AddressNotFoundError:
        return "ZZ"
    except Exception as e:
        log.warning("ip_lookup_failed", ip=ip, error=str(e))
        return "ZZ"


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

    # Country detection from IP via local GeoLite2 DB
    country = resolve_country_from_ip(client_ip)

    # If we are running tests, reuse the transaction session to keep database isolation intact.
    # Otherwise, allocate a fresh database session for the background thread.
    if settings.is_testing and db:
        session_to_use = db
        is_external_session = True
    else:
        session_to_use = AsyncSessionLocal()
        is_external_session = False

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
        log.error("click_recording_failed", error=str(e), link_id=str(link_id))
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
    request: Request,
    background_tasks: BackgroundTasks,
    short_code: str = Path(..., min_length=1, max_length=50, pattern="^[a-zA-Z0-9_-]+$"),
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
    if settings.is_testing:
        background_tasks.add_task(record_click, link_id, request, db)
    else:
        background_tasks.add_task(record_click, link_id, request)

    return RedirectResponse(url=original_url, status_code=307)
