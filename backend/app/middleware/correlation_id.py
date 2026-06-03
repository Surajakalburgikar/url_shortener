"""
app/middleware/correlation_id.py
─────────────────────────────────
Generates a unique X-Request-ID for every request.

Why correlation IDs?
When you have logs from thousands of requests, you need a way to find ALL log lines
from ONE specific request. Without correlation IDs, debugging production issues is
like finding a needle in a haystack.

With correlation IDs:
- Every request gets a UUID (e.g. "550e8400-e29b-41d4-a716-446655440000")
- Every log line from that request includes that UUID
- You can grep logs for "550e8400..." and see the full story of that request
- The UUID is also returned in the response header so the client can report it in bug reports

This is standard observability practice at Google, AWS, Stripe, etc.
"""

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Attaches a unique request ID to every request and response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Use existing ID if provided by a upstream proxy (e.g. AWS ALB, Nginx)
        # Otherwise generate a new one
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())

        # Bind request_id to structlog context — all log lines in this request
        # will automatically include request_id=<uuid>
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Store on request state so routers can access it
        request.state.request_id = request_id

        response = await call_next(request)

        # Return the request ID in the response header
        # Client can include this in bug reports: "My request ID was 550e8400..."
        response.headers[REQUEST_ID_HEADER] = request_id

        # Clear the context so it doesn't bleed into the next request
        structlog.contextvars.clear_contextvars()

        return response
