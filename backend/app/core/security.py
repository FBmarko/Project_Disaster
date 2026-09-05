"""Security middleware and response header management for AFET360 API."""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send


class SecurityHeadersMiddleware:
    """Attach standard security response headers to all HTTP responses.

    Security Headers Applied:
    - X-Content-Type-Options: nosniff
      Prevents MIME-sniffing away from declared Content-Type.
    - X-Frame-Options: DENY
      Protects against clickjacking by preventing rendering in an iframe.
    - Referrer-Policy: no-referrer
      Prevents leaking path or query parameters in the Referer header.
    - Permissions-Policy:
      accelerometer=(), camera=(), geolocation=(), gyroscope=(),
      magnetometer=(), microphone=(), payment=(), usb=()
      Disables browser hardware/feature access on API responses.

    ARCHITECTURAL NOTES:
    - HSTS (Strict-Transport-Security) is intentionally NOT applied here.
      It belongs to the production HTTPS termination / reverse proxy layer (TASK 16)
      to avoid breaking local HTTP development environments.
    - Frontend Content-Security-Policy (CSP) is intentionally NOT set here.
      This service is a JSON API and does not serve frontend HTML application documents.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                headers["Referrer-Policy"] = "no-referrer"
                headers["Permissions-Policy"] = (
                    "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
                    "magnetometer=(), microphone=(), payment=(), usb=()"
                )
            await send(message)

        await self.app(scope, receive, send_with_security_headers)
