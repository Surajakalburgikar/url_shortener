"""
app/middleware/security_headers.py
────────────────────────────────────
Adds security-related HTTP headers to every response.

Uses the pure ASGI middleware pattern instead of BaseHTTPMiddleware.
Why?
- BaseHTTPMiddleware has known performance overhead and event loop bugs in async tests.
- Pure ASGI middleware is faster, lightweight, and works perfectly in async test suites.
"""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send


class SecurityHeadersMiddleware:
    """Adds security headers to every HTTP response using pure ASGI wrapper."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Only modify HTTP or WebSocket responses
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                headers["X-XSS-Protection"] = "1; mode=block"
                headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
                headers["Server"] = "url-shortener"
                headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; img-src 'self' data: https://fastapi.tiangolo.com; font-src 'self' data: https://fonts.gstatic.com; frame-ancestors 'none';"
            await send(message)

        await self.app(scope, receive, send_wrapper)
