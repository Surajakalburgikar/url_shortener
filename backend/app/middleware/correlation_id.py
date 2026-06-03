"""
app/middleware/correlation_id.py
─────────────────────────────────
Generates a unique X-Request-ID for every request.

Uses pure ASGI middleware pattern to avoid Starlette's BaseHTTPMiddleware event loop bugs.
"""

import uuid
import structlog
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"


class CorrelationIdMiddleware:
    """Attaches a unique request ID to every request and response using pure ASGI."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # Try to read incoming request ID or generate a new one
        request_id = str(uuid.uuid4())
        for key, value in scope.get("headers", []):
            if key.lower() == REQUEST_ID_HEADER.lower().encode("latin-1"):
                request_id = value.decode("latin-1")
                break

        # Bind to structlog logging context
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Store in scope state so endpoints/dependency-injection can access it via request.state
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["request_id"] = request_id

        async def send_wrapper(message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Clear context at request end
            structlog.contextvars.clear_contextvars()
