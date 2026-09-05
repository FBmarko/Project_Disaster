"""Tests for request body size limiting middleware."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from starlette.responses import PlainTextResponse

from app.core.config import settings
from app.core.request_body_limit import RequestBodyLimitMiddleware
from app.integrations.ai.dependencies import get_ai_provider
from app.main import app
from app.schemas.ai import PreparednessGuideContent

client = TestClient(app)


# ==============================================================================
# 1. INTEGRATION TESTS VIA TESTCLIENT
# ==============================================================================


def test_request_body_below_limit_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "API_MAX_REQUEST_BODY_BYTES", 1000)

    # Valid small payload (~50 bytes)
    response = client.post(
        "/api/v1/ai/preparedness-guide",
        json={"disaster_type": "earthquake"},
    )
    # Reaches application; returns 503 (no provider) or 200, but NOT 413
    assert response.status_code != 413


def test_request_body_above_limit_returns_413_and_no_retry_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Set limit to 200 bytes
    monkeypatch.setattr(settings, "API_MAX_REQUEST_BODY_BYTES", 200)

    # Payload larger than 200 bytes
    oversized_city = "A" * 300
    response = client.post(
        "/api/v1/ai/preparedness-guide",
        json={"disaster_type": "earthquake", "city": oversized_city},
    )

    assert response.status_code == 413
    assert response.json() == {"detail": "Request body too large."}
    assert "retry-after" not in response.headers
    # Security headers must be present on 413 response
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"


def test_oversized_body_does_not_invoke_ai_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "API_MAX_REQUEST_BODY_BYTES", 200)

    mock_provider = MagicMock()
    mock_provider.generate_guide.return_value = PreparednessGuideContent(
        summary="Safe summary content text",
        before=["Step 1"],
        during=["Step 2"],
        after=["Step 3"],
        emergency_kit=["Item 1"],
        important_notes=["Note 1"],
    )
    app.dependency_overrides[get_ai_provider] = lambda: mock_provider

    try:
        oversized_payload = {"disaster_type": "earthquake", "city": "X" * 500}
        response = client.post(
            "/api/v1/ai/preparedness-guide",
            json=oversized_payload,
        )

        assert response.status_code == 413
        # CRUCIAL: Provider must NEVER be called for 413 oversized requests
        assert mock_provider.generate_guide.call_count == 0
    finally:
        app.dependency_overrides.pop(get_ai_provider, None)


def test_get_requests_are_unaffected_by_body_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Extremely small limit
    monkeypatch.setattr(settings, "API_MAX_REQUEST_BODY_BYTES", 10)

    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_options_requests_are_unaffected_by_body_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "API_MAX_REQUEST_BODY_BYTES", 10)

    response = client.options(
        "/api/v1/ai/preparedness-guide",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200


def test_cors_headers_present_on_413_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "API_MAX_REQUEST_BODY_BYTES", 100)

    response = client.post(
        "/api/v1/ai/preparedness-guide",
        headers={"Origin": "http://localhost:5173"},
        json={"disaster_type": "earthquake", "city": "A" * 200},
    )

    assert response.status_code == 413
    assert (
        response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    )


# ==============================================================================
# 2. DIRECT ASGI TESTS FOR STREAMING / CHUNKED ENFORCEMENT
# ==============================================================================


@pytest.mark.anyio
async def test_asgi_streamed_chunks_without_content_length_rejected_at_cap() -> None:
    """Proves that a client cannot bypass limits by streaming chunks
    without Content-Length.
    """
    captured_status = None
    captured_body = b""

    async def dummy_app(scope, receive, send):
        await receive()
        res = PlainTextResponse("ok")
        await res(scope, receive, send)

    mw = RequestBodyLimitMiddleware(dummy_app, max_bytes=50)

    # Multi-chunk stream with NO content-length header
    chunks = [
        {"type": "http.request", "body": b"A" * 30, "more_body": True},
        {"type": "http.request", "body": b"B" * 30, "more_body": False},
    ]
    idx = 0

    async def fake_receive():
        nonlocal idx
        m = chunks[idx]
        idx += 1
        return m

    async def fake_send(msg):
        nonlocal captured_status, captured_body
        if msg["type"] == "http.response.start":
            captured_status = msg["status"]
        elif msg["type"] == "http.response.body":
            captured_body += msg.get("body", b"")

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/test-endpoint",
        "headers": [],  # No content-length header!
    }

    await mw(scope, fake_receive, fake_send)

    assert captured_status == 413
    assert b"Request body too large." in captured_body


@pytest.mark.anyio
async def test_asgi_exact_limit_body_is_admitted() -> None:
    """Proves that body exactly matching limit is admitted through middleware."""
    app_called = False

    async def dummy_app(scope, receive, send):
        nonlocal app_called
        app_called = True
        msg = await receive()
        assert len(msg.get("body", b"")) == 50
        res = PlainTextResponse("ok")
        await res(scope, receive, send)

    mw = RequestBodyLimitMiddleware(dummy_app, max_bytes=50)

    chunks = [
        {"type": "http.request", "body": b"X" * 50, "more_body": False},
    ]
    idx = 0

    async def fake_receive():
        nonlocal idx
        m = chunks[idx]
        idx += 1
        return m

    async def fake_send(msg):
        pass

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/test-endpoint",
        "headers": [(b"content-length", b"50")],
    }

    await mw(scope, fake_receive, fake_send)
    assert app_called is True
