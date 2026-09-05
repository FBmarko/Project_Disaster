"""Request body size limit middleware for AFET360 API."""

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings

BODY_LIMIT_METHODS = {"POST", "PUT", "PATCH"}


class RequestBodyLimitMiddleware:
    """ASGI middleware enforcing an upper bound on incoming request body size.

    Protection Layers:
    1. Early rejection: Checks Content-Length header if present. If Content-Length
       exceeds the configured maximum, the request is immediately rejected with
       HTTP 413 without reading the body.
    2. Streamed/chunked enforcement: For requests with missing or chunked
       Content-Length, body chunks received via ASGI receive() are counted.
       If accumulated bytes exceed the limit, reading terminates immediately
       and returns HTTP 413. Buffers at most (limit + 1) bytes to prevent
       memory exhaustion attacks.
    """

    def __init__(
        self,
        app: ASGIApp,
        max_bytes: int | None = None,
    ) -> None:
        self.app = app
        self.max_bytes = max_bytes

    @property
    def limit(self) -> int:
        if self.max_bytes is not None:
            return self.max_bytes
        return settings.API_MAX_REQUEST_BODY_BYTES

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "").upper()
        path = scope.get("path", "")

        # Apply only to mutating API methods under /api/v1/
        if method not in BODY_LIMIT_METHODS or not path.startswith(
            settings.API_V1_PREFIX
        ):
            await self.app(scope, receive, send)
            return

        limit = self.limit

        # Layer A: Early Content-Length check
        content_length_header = None
        for name, value in scope.get("headers", []):
            if name.lower() == b"content-length":
                try:
                    content_length_header = int(value.decode("latin-1"))
                except (ValueError, UnicodeDecodeError):
                    content_length_header = None
                break

        if content_length_header is not None and content_length_header > limit:
            response = JSONResponse(
                status_code=413,
                content={"detail": "Request body too large."},
            )
            await response(scope, receive, send)
            return

        # Layer B: Streamed byte accounting and bounded replay
        received_bytes = 0
        buffered_messages: list[dict] = []
        is_oversized = False

        while True:
            message = await receive()
            buffered_messages.append(message)
            if message.get("type") == "http.request":
                body = message.get("body", b"")
                received_bytes += len(body)
                if received_bytes > limit:
                    is_oversized = True
                    break
            if not message.get("more_body", False):
                break

        if is_oversized:
            response = JSONResponse(
                status_code=413,
                content={"detail": "Request body too large."},
            )
            await response(scope, receive, send)
            return

        # Replay buffered chunks to downstream app
        replay_index = 0

        async def replay_receive() -> dict:
            nonlocal replay_index
            if replay_index < len(buffered_messages):
                msg = buffered_messages[replay_index]
                replay_index += 1
                return msg
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay_receive, send)
