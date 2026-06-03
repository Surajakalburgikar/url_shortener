"""
app/routers/health.py
──────────────────────
Health check endpoints — used by:
- Load balancers (to know if the server is up)
- Render.com (to detect a healthy deployment)
- UptimeRobot (to keep the free tier from sleeping)
- Kubernetes liveness/readiness probes (future-proofing)

Two endpoints:
- GET /health       → "am I running?" (liveness) — just checks the process is alive
- GET /health/ready → "can I serve traffic?" (readiness) — checks DB + Redis connections
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness check")
async def health_check():
    """
    Returns app status and version.
    Always returns 200 if the process is running.
    Used by: load balancers, UptimeRobot monitors.
    """
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.app_env,
    }


@router.get("/health/ready", summary="Readiness check")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Returns DB and Redis connection status.
    Returns 200 only if the app can actually serve requests.
    Used by: Kubernetes readiness probes, deployment verification.
    """
    # Check database connectivity
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)[:50]}"

    # Check Redis connectivity
    redis_status = "ok"
    try:
        from app.main import redis_client  # imported at runtime to avoid circular import
        if redis_client:
            await redis_client.ping()
        else:
            redis_status = "not configured"
    except Exception as e:
        redis_status = f"error: {str(e)[:50]}"

    overall = "ok" if db_status == "ok" and redis_status in ("ok", "not configured") else "degraded"

    return {
        "status": overall,
        "database": db_status,
        "redis": redis_status,
    }
