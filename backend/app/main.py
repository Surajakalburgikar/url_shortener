"""
app/main.py
────────────
FastAPI application factory — the entry point of the entire backend.

App factory pattern:
Instead of `app = FastAPI()` at module level (which makes testing hard),
we configure everything here and export the app object.

Startup/shutdown lifecycle:
- On startup: connect to Redis, configure structlog
- On shutdown: close Redis connection

The order middleware is added MATTERS — they execute in reverse order:
1. SecurityHeaders (outermost — runs last on response, first to receive request)
2. CorrelationId (generates UUID, binds to log context)
3. CORS (must be close to the inside to see actual request origin)
"""

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi

from app.config import settings
from app.middleware.correlation_id import CorrelationIdMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.routers import analytics, auth, health, links, redirect

# ── Structured logging setup ──────────────────────────────────────────────────
# structlog outputs JSON in production (easy to parse by log aggregators like Datadog)
# and pretty colored output in development (easy to read)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,          # Merge request_id from middleware
        structlog.processors.add_log_level,               # Add "level": "info"
        structlog.processors.TimeStamper(fmt="iso"),      # Add "timestamp": "2024-..."
        structlog.dev.ConsoleRenderer()                   # Pretty output for dev
        if settings.is_development
        else structlog.processors.JSONRenderer(),         # JSON output for production
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

log = structlog.get_logger()

# ── Redis client (module-level — shared across requests) ──────────────────────
# Declared here so routers can import it: `from app.main import redis_client`
redis_client = None


# ── FastAPI app factory ───────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to Redis on startup and close on shutdown."""
    global redis_client
    if settings.redis_url:
        try:
            import redis.asyncio as aioredis
            redis_client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=False,
            )
            await redis_client.ping()
            log.info("startup.redis_connected", url=settings.redis_url[:30] + "...")
        except Exception as e:
            log.warning("startup.redis_unavailable", error=str(e))
            redis_client = None
    else:
        log.info("startup.redis_skipped", reason="REDIS_URL not configured")
        
    yield
    
    if redis_client:
        await redis_client.close()
        log.info("shutdown.redis_closed")

    # Always close the GeoIP http client, regardless of Redis status
    from app.routers.redirect import http_client as geo_http_client
    await geo_http_client.aclose()
    log.info("shutdown.geo_http_client_closed")


app = FastAPI(
    title="URL Shortener & Analytics API",
    description=(
        "A production-quality URL shortener with:\n"
        "- JWT authentication (email/password + GitHub OAuth)\n"
        "- Redis-cached redirects for sub-millisecond performance\n"
        "- Click analytics with geographic and referrer breakdown\n"
        "- Rate limiting (5/hr anonymous, 50/hr authenticated)\n\n"
        "**Authenticate:** Click the 🔒 Authorize button and enter your Bearer token."
    ),
    version=settings.app_version,
    contact={
        "name": "URL Shortener API",
        "url": "https://github.com/yourusername/url-shortener",
    },
    license_info={"name": "MIT"},
    openapi_tags=[
        {"name": "auth", "description": "Registration, login, token refresh, GitHub OAuth"},
        {"name": "links", "description": "Create, list, and delete short URLs"},
        {"name": "analytics", "description": "Click analytics and statistics"},
        {"name": "redirect", "description": "Short URL redirect endpoint"},
        {"name": "health", "description": "Health and readiness checks"},
    ],
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)


# ── Middleware (added in reverse execution order) ─────────────────────────────

# 4. Session Middleware — required by Authlib to maintain state between OAuth redirects
from starlette.middleware.sessions import SessionMiddleware
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# 3. Correlation ID — generates UUID for every request
app.add_middleware(CorrelationIdMiddleware)

# 2. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 1. CORS (outermost, so preflight OPTIONS are answered immediately)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


# ── Global exception handler ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catches ALL unhandled exceptions and returns a consistent JSON error shape.
    
    Why this matters:
    - Without this, FastAPI returns a 500 with a raw Python traceback — leaks internals
    - With this, we always return {"error": "...", "message": "...", "request_id": "..."}
    - The request_id lets engineers find the full error in the logs
    - Stack traces are logged server-side (never sent to clients in production)
    """
    request_id = getattr(request.state, "request_id", "unknown")

    log.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=str(request.url),
        request_id=request_id,
        exc_info=exc,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again.",
            "request_id": request_id,
        },
    )


# ── Swagger / ReDoc Basic Auth ────────────────────────────────────────────────
security = HTTPBasic()

def authenticate_docs(credentials: HTTPBasicCredentials = Depends(security)):
    import secrets
    correct_username = secrets.compare_digest(credentials.username, settings.docs_username)
    correct_password = secrets.compare_digest(credentials.password, settings.docs_password)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

if not settings.is_production:
    @app.get("/openapi.json", include_in_schema=False)
    async def get_open_api_endpoint(username: str = Depends(authenticate_docs)):
        return get_openapi(title=app.title, version=app.version, routes=app.routes)

    @app.get("/docs", include_in_schema=False)
    async def get_swagger_html(username: str = Depends(authenticate_docs)):
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title=f"{app.title} - Swagger UI",
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        )

    @app.get("/redoc", include_in_schema=False)
    async def get_redoc_html_endpoint(username: str = Depends(authenticate_docs)):
        return get_redoc_html(
            openapi_url="/openapi.json",
            title=f"{app.title} - ReDoc",
        )


# ── Routers ───────────────────────────────────────────────────────────────────

# Health checks — no prefix (lives at /health and /health/ready)
app.include_router(health.router)

# API v1 routes
API_PREFIX = f"/api/{settings.api_version}"

app.include_router(auth.router, prefix=API_PREFIX)      # /api/v1/auth/*
app.include_router(links.router, prefix=API_PREFIX)     # /api/v1/links/*
app.include_router(analytics.router, prefix=API_PREFIX) # /api/v1/analytics/*

# Redirect must be LAST — it matches /{short_code} which would otherwise
# catch /api, /docs, /health etc. if registered first
app.include_router(redirect.router)                     # /{short_code}


# ── Root endpoint ─────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": "URL Shortener API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
