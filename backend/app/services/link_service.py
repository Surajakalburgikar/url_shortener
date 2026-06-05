"""
app/services/link_service.py
─────────────────────────────
Business logic for URL shortening and link management.

Responsibilities:
- Generate random short codes
- Validate URLs (block localhost, private IPs, javascript: scheme)
- Check custom alias availability
- Handle Redis caching for the redirect hot path
- Coordinate between LinkRepository and Redis
"""

import random
import re
import string
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.link_repo import LinkRepository
from app.schemas.link import LinkCreate, LinkListResponse, LinkResponse

# Characters used for random short codes, excluding visually confusing ones:
# 0 (zero), O (capital o), 1 (one), I (capital i), l (lowercase L)
ALPHABET = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
SHORT_CODE_LENGTH = 6


def generate_short_code() -> str:
    """Generate a cryptographically secure random 6-character short code."""
    import secrets
    return "".join(secrets.choice(ALPHABET) for _ in range(SHORT_CODE_LENGTH))


# ── URL safety validation ─────────────────────────────────────────────────────

# Block patterns that could be used for SSRF (Server-Side Request Forgery) attacks.
# SSRF is when an attacker tricks your server into making requests to internal services.
BLOCKED_HOSTS = re.compile(
    r"(localhost|127\.|0\.0\.0\.0|192\.168\.|10\.|172\.(1[6-9]|2\d|3[01])\.)",
    re.IGNORECASE,
)


def validate_url_safety(url: str) -> None:
    """
    Additional URL safety checks beyond what AnyHttpUrl provides.
    
    AnyHttpUrl already blocks:
    - javascript: scheme
    - ftp: scheme  
    - Missing scheme
    
    We additionally block:
    - localhost (SSRF prevention)
    - Private IP ranges (SSRF prevention)
    """
    if BLOCKED_HOSTS.search(url):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="URL points to a private or local address, which is not allowed",
        )


# ── Link service ──────────────────────────────────────────────────────────────

class LinkService:
    """Orchestrates link creation, listing, deletion, and Redis caching."""

    def __init__(self, db: AsyncSession, redis=None) -> None:
        self.db = db
        self.redis = redis
        self.link_repo = LinkRepository(db)

    async def create_link(
        self,
        data: LinkCreate,
        user_id: uuid.UUID | None = None,
    ) -> LinkResponse:
        """
        Create a shortened URL.
        
        Steps:
        1. Validate URL safety (block localhost/private IPs)
        2. Determine short code (custom alias or auto-generated)
        3. Check short code uniqueness
        4. Create in DB
        5. Cache in Redis
        """
        url_str = str(data.original_url)
        validate_url_safety(url_str)

        # Determine short code
        if data.custom_alias:
            short_code = data.custom_alias
            if await self.link_repo.short_code_exists(short_code):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"The alias '{short_code}' is already taken",
                )
        else:
            # Auto-generate: try until we find a unique one (collision is rare)
            for _ in range(5):
                short_code = generate_short_code()
                if not await self.link_repo.short_code_exists(short_code):
                    break
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not generate a unique short code. Please try again.",
                )

        link = await self.link_repo.create(
            short_code=short_code,
            original_url=url_str,
            user_id=user_id,
            expires_at=data.expires_at,
        )

        # Cache in Redis so the first redirect is also fast
        await self._cache_link(short_code, url_str, data.expires_at, link.id)

        return LinkResponse(
            id=link.id,
            short_code=link.short_code,
            original_url=link.original_url,
            user_id=link.user_id,
            expires_at=link.expires_at,
            created_at=link.created_at,
            click_count=0,
        )

    async def get_original_url(self, short_code: str) -> tuple[str, uuid.UUID]:
        """
        Look up the original URL for a short code.
        
        Cache-first strategy:
        1. Check Redis (microseconds)
        2. Fall back to PostgreSQL (milliseconds)
        3. Cache the result in Redis for future requests
        
        Returns (original_url, link_id) tuple.
        Raises 404 if not found, 410 if expired.
        """
        import structlog
        log = structlog.get_logger()

        # 1. Check Redis cache
        if self.redis:
            try:
                cached = await self.redis.get(f"link:{short_code}")
                if cached:
                    log.info("redirect.cache_hit", short_code=short_code)
                    # Format: "url|link_id"
                    parts = cached.decode().split("|", 1)
                    if len(parts) == 2:
                        return parts[0], uuid.UUID(parts[1])
            except Exception as e:
                log.warning("redirect.redis_error", error=str(e))

        # 2. Cache miss — go to DB
        log.info("redirect.cache_miss", short_code=short_code)
        link = await self.link_repo.get_by_short_code(short_code)

        if not link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Short link not found",
            )

        # Check expiry
        if link.expires_at:
            expires = link.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires <= datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="This link has expired",
                )

        # 3. Cache it for next time
        await self._cache_link(short_code, link.original_url, link.expires_at, link.id)

        return link.original_url, link.id

    async def list_user_links(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> LinkListResponse:
        """List all links for a user with pagination and click counts (optimized single query)."""
        links_with_counts, total = await self.link_repo.get_user_links(user_id, page, page_size)

        items = []
        for link, count in links_with_counts:
            items.append(LinkResponse(
                id=link.id,
                short_code=link.short_code,
                original_url=link.original_url,
                user_id=link.user_id,
                expires_at=link.expires_at,
                created_at=link.created_at,
                click_count=count,
            ))

        return LinkListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def delete_link(
        self,
        short_code: str,
        user_id: uuid.UUID,
    ) -> None:
        """
        Delete a link — only the owner can delete their own links.
        Also removes from Redis cache.
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
                detail="You don't have permission to delete this link",
            )

        await self.link_repo.delete(link)

        # Evict from cache
        if self.redis:
            try:
                await self.redis.delete(f"link:{short_code}")
            except Exception as e:
                import structlog
                log = structlog.get_logger()
                log.warning("delete.redis_error", error=str(e))

    async def _cache_link(
        self,
        short_code: str,
        url: str,
        expires_at: datetime | None,
        link_id: uuid.UUID,
    ) -> None:
        """Store link in Redis. TTL matches the link's expiry if set."""
        if not self.redis:
            return

        value = f"{url}|{str(link_id)}"
        try:
            # TTL: if link expires, cache should too; otherwise cache for 1 hour
            if expires_at:
                expires = expires_at
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                ttl = int((expires - datetime.now(timezone.utc)).total_seconds())
                if ttl > 0:
                    await self.redis.setex(f"link:{short_code}", ttl, value)
            else:
                await self.redis.setex(f"link:{short_code}", 3600, value)  # 1 hour default TTL
        except Exception as e:
            import structlog
            log = structlog.get_logger()
            log.warning("cache.redis_error", error=str(e))
