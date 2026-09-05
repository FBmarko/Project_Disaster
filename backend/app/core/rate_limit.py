"""In-memory sliding-window rate limiter for AFET360 API.

NOTE: This rate limiter operates strictly PER PROCESS in-memory.
It provides resource bounding without external datastores or distributed caches.
"""

import math
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings


@dataclass
class _Bucket:
    """Bucket state maintaining timestamps and window duration."""

    timestamps: deque[float] = field(default_factory=deque)
    window_seconds: int = 60


def get_client_ip(scope: Scope) -> str:
    """Extract directly connected client IP address from ASGI scope.

    SECURITY ARCHITECTURE DECISION:
    Forwarded headers (X-Forwarded-For, X-Real-IP, Forwarded) are intentionally
    NOT trusted by default. Blindly trusting forwarded headers from untrusted clients
    allows trivial rate-limit bypass via header spoofing.
    If deployment introduces a trusted reverse proxy, proxy-aware client resolution
    will be configured explicitly in TASK 16.
    """
    client = scope.get("client")
    if client and client[0]:
        return str(client[0])
    return "unknown"


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding-window rate limiter.

    Maintains a FIFO deque of monotonic request timestamps per client key.
    Provides bounded memory usage via window-aware lazy pruning and
    a strict hard capacity cap (max_keys).
    """

    def __init__(
        self,
        time_func: Callable[[], float] | None = None,
        cleanup_interval_seconds: float = 60.0,
        max_keys: int = 10_000,
    ) -> None:
        """Initialize the rate limiter.

        Args:
            time_func: Monotonic time source (default: time.monotonic).
            cleanup_interval_seconds: Minimum interval between stale cleanups.
            max_keys: Strict maximum capacity of concurrent active keys.
        """
        self.time_func = time_func or time.monotonic
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self.max_keys = max_keys
        self._lock = threading.Lock()
        self._buckets: dict[str, _Bucket] = {}
        self._last_cleanup: float = self.time_func()

    def check_and_record(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        now: float | None = None,
    ) -> tuple[bool, int]:
        """Check if request is permitted under rate limit and record if allowed.

        Args:
            key: Rate limit bucket key (e.g. "ai:127.0.0.1" or "general:127.0.0.1").
            max_requests: Maximum allowed requests within the time window.
            window_seconds: Duration of the sliding window in seconds.
            now: Optional monotonic timestamp (useful for deterministic tests).

        Returns:
            tuple[bool, int]: (is_allowed, retry_after_seconds).
            If allowed: (True, 0).
            If rejected: (False, retry_after_seconds).
        """
        current_time = now if now is not None else self.time_func()

        with self._lock:
            # Periodic opportunistic cleanup if interval exceeded
            if current_time - self._last_cleanup > self.cleanup_interval_seconds:
                self._cleanup_stale_locked(current_time)

            if key in self._buckets:
                bucket = self._buckets[key]
                bucket.window_seconds = window_seconds
            else:
                # New key arriving: check hard memory cap
                if len(self._buckets) >= self.max_keys:
                    self._cleanup_stale_locked(current_time)

                if len(self._buckets) >= self.max_keys:
                    # Capacity full and active buckets cannot be evicted.
                    # Fail closed to preserve memory without allowing bypass.
                    return False, window_seconds

                bucket = _Bucket(window_seconds=window_seconds)
                self._buckets[key] = bucket

            timestamps = bucket.timestamps
            cutoff = current_time - bucket.window_seconds

            # Prune timestamps outside this bucket's sliding window
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) < max_requests:
                timestamps.append(current_time)
                return True, 0

            # Exceeded limit: compute remaining seconds until oldest slides out
            oldest = timestamps[0]
            retry_after = max(
                1, math.ceil(oldest + bucket.window_seconds - current_time)
            )
            return False, retry_after

    def cleanup_stale(self, now: float | None = None) -> int:
        """Purge idle or empty buckets according to each bucket's own window.

        Args:
            now: Optional current monotonic timestamp.

        Returns:
            int: Number of deleted buckets.
        """
        current_time = now if now is not None else self.time_func()
        with self._lock:
            return self._cleanup_stale_locked(current_time)

    def _cleanup_stale_locked(self, current_time: float) -> int:
        """Internal helper for cleaning stale buckets while holding the lock."""
        keys_to_remove = []

        for key, bucket in self._buckets.items():
            cutoff = current_time - bucket.window_seconds
            while bucket.timestamps and bucket.timestamps[0] <= cutoff:
                bucket.timestamps.popleft()
            if not bucket.timestamps:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._buckets[key]

        self._last_cleanup = current_time
        return len(keys_to_remove)

    def reset(self) -> None:
        """Clear all rate limit state (primarily for test isolation)."""
        with self._lock:
            self._buckets.clear()
            self._last_cleanup = self.time_func()


# Global default rate limiter instance
rate_limiter = SlidingWindowRateLimiter()

EXEMPT_PATHS = {
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/health",
}

AI_PATH = "/api/v1/ai/preparedness-guide"


class RateLimitMiddleware:
    """ASGI middleware applying general and AI-specific rate limits.

    Precedence & Policy:
    1. CORS preflight (OPTIONS) requests are exempt.
    2. Exact documentation and health routes (/docs, /redoc, /openapi.json,
       /api/v1/health) are exempt. Generic suffixes are not exempt.
    3. AI endpoint (POST /api/v1/ai/preparedness-guide) uses a dedicated,
       stricter AI bucket (settings.AI_RATE_LIMIT_REQUESTS).
    4. General API endpoints (/api/v1/*) use the general bucket
       (settings.API_RATE_LIMIT_REQUESTS).
    5. Exceeded limits return HTTP 429 Too Many Requests with Retry-After.
    """

    def __init__(
        self,
        app: ASGIApp,
        limiter: SlidingWindowRateLimiter | None = None,
    ) -> None:
        self.app = app
        self.limiter = limiter or rate_limiter

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "").upper()
        path = scope.get("path", "")

        # 1. Exempt CORS preflight requests
        if method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        # 2. Exempt exact documentation and health check endpoints
        if path in EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return

        # 3. Only apply limits to API routes
        if not path.startswith(settings.API_V1_PREFIX):
            await self.app(scope, receive, send)
            return

        client_ip = get_client_ip(scope)

        # 4. Route-based bucket resolution
        if path == AI_PATH and method == "POST":
            bucket_key = f"ai:{client_ip}"
            max_requests = settings.AI_RATE_LIMIT_REQUESTS
            window_seconds = settings.AI_RATE_LIMIT_WINDOW_SECONDS
        else:
            bucket_key = f"general:{client_ip}"
            max_requests = settings.API_RATE_LIMIT_REQUESTS
            window_seconds = settings.API_RATE_LIMIT_WINDOW_SECONDS

        allowed, retry_after = self.limiter.check_and_record(
            key=bucket_key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": str(retry_after)},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
