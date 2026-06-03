"""
app/middleware/security_headers.py
────────────────────────────────────
Adds security-related HTTP headers to every response.

Why security headers matter:
These headers tell the browser how to behave when displaying your content.
Without them, your app is vulnerable to:
- Clickjacking (X-Frame-Options)
- MIME type sniffing attacks (X-Content-Type-Options)
- Cross-site scripting via old IE (X-XSS-Protection)
- Protocol downgrade attacks (Strict-Transport-Security)

A security scanner (like Mozilla Observatory) will give you an F without these.
With them, you get an A+. Big tech companies always set these.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to every HTTP response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Prevents browsers from guessing the content type
        # (protects against MIME confusion attacks)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevents your app from being embedded in an iframe (clickjacking protection)
        response.headers["X-Frame-Options"] = "DENY"

        # Legacy XSS protection for old browsers (modern browsers use CSP instead)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Forces HTTPS for 1 year — only set in production (doesn't make sense on localhost)
        # includeSubDomains: applies to all subdomains too
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        # Hides the server technology stack from attackers
        # (they don't need to know we're running FastAPI/uvicorn)
        response.headers["Server"] = "url-shortener"

        return response
