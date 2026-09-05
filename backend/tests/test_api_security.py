"""Integration tests for AFET360 API security layer.

Covers: CORS, security headers, and rate limiting.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.rate_limit import RATE_LIMIT_DETAIL, rate_limiter
from app.integrations.ai.dependencies import get_ai_provider
from app.main import app
from app.schemas.ai import PreparednessGuideContent

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Ensure a clean rate limiter state before and after each test."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()


# ==============================================================================
# 1. CORS SECURITY TESTS
# ==============================================================================


def test_cors_allowed_origin_receives_cors_headers() -> None:
    response = client.get(
        "/api/v1/health",
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.status_code == 200
    assert (
        response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    )


def test_cors_disallowed_origin_does_not_receive_cors_header() -> None:
    response = client.get(
        "/api/v1/health",
        headers={"Origin": "http://malicious-site.example.com"},
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_cors_preflight_options_for_allowed_origin() -> None:
    response = client.options(
        "/api/v1/ai/preparedness-guide",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response.status_code == 200
    assert (
        response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    )
    assert "POST" in response.headers.get("access-control-allow-methods", "")


def test_cors_preflight_disallowed_method_rejected() -> None:
    response = client.options(
        "/api/v1/fault-lines",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "DELETE",
        },
    )
    # Method DELETE is not permitted by CORS policy
    allowed_methods = response.headers.get("access-control-allow-methods", "")
    assert "DELETE" not in allowed_methods


def test_cors_credentials_disabled() -> None:
    response = client.get(
        "/api/v1/health",
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.status_code == 200
    # Credentials must NOT be allowed
    assert response.headers.get("access-control-allow-credentials") != "true"


# ==============================================================================
# 2. SECURITY HEADERS TESTS
# ==============================================================================


def test_security_headers_present_on_successful_response() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("referrer-policy") == "no-referrer"
    assert "accelerometer=()" in response.headers.get("permissions-policy", "")
    assert "camera=()" in response.headers.get("permissions-policy", "")


def test_security_headers_present_on_error_response() -> None:
    response = client.get("/api/v1/non-existent-path")
    assert response.status_code == 404
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("referrer-policy") == "no-referrer"


def test_docs_accessible_with_security_headers() -> None:
    response = client.get("/docs")
    assert response.status_code == 200
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"


# ==============================================================================
# 3. RATE LIMITING TESTS
# ==============================================================================


def test_health_check_exempt_from_rate_limiting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Set limit low to verify exact /api/v1/health is exempt
    monkeypatch.setattr(settings, "API_RATE_LIMIT_REQUESTS", 2)

    for _ in range(10):
        response = client.get("/api/v1/health")
        assert response.status_code == 200


def test_arbitrary_health_suffix_is_not_exempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Set limit low to verify non-exact /health suffix is rate limited
    monkeypatch.setattr(settings, "API_RATE_LIMIT_REQUESTS", 2)

    # 2 requests to an arbitrary path ending with /health
    client.get("/api/v1/other/health")
    client.get("/api/v1/other/health")

    # 3rd request is blocked with 429 by rate limiter
    res = client.get("/api/v1/other/health")
    assert res.status_code == 429
    assert res.json() == {"detail": "Too many requests. Please try again later."}


def test_general_api_rate_limit_enforcement(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "API_RATE_LIMIT_REQUESTS", 3)
    monkeypatch.setattr(settings, "API_RATE_LIMIT_WINDOW_SECONDS", 60)

    # 3 allowed requests
    for _ in range(3):
        res = client.get("/api/v1/fault-lines")
        assert res.status_code == 200

    # 4th request rejected
    res = client.get("/api/v1/fault-lines")
    assert res.status_code == 429
    assert res.json() == {"detail": "Too many requests. Please try again later."}
    assert "retry-after" in res.headers
    retry_after = int(res.headers["retry-after"])
    assert 1 <= retry_after <= 60

    # Verify security headers are also present on 429 response
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-frame-options") == "DENY"


def test_ai_rate_limit_enforcement_and_quota_defense(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "AI_RATE_LIMIT_REQUESTS", 2)
    monkeypatch.setattr(settings, "AI_RATE_LIMIT_WINDOW_SECONDS", 60)

    mock_provider = MagicMock()
    mock_provider.generate_guide.return_value = PreparednessGuideContent(
        summary="Test summary",
        before=["Step 1"],
        during=["Step 2"],
        after=["Step 3"],
        emergency_kit=["Item 1"],
        important_notes=["Note 1"],
    )

    app.dependency_overrides[get_ai_provider] = lambda: mock_provider

    try:
        # 1st request -> 200
        res1 = client.post(
            "/api/v1/ai/preparedness-guide", json={"disaster_type": "earthquake"}
        )
        assert res1.status_code == 200

        # 2nd request -> 200
        res2 = client.post(
            "/api/v1/ai/preparedness-guide", json={"disaster_type": "flood"}
        )
        assert res2.status_code == 200

        assert mock_provider.generate_guide.call_count == 2

        # 3rd request -> 429 Too Many Requests
        res3 = client.post(
            "/api/v1/ai/preparedness-guide", json={"disaster_type": "fire"}
        )
        assert res3.status_code == 429
        assert res3.json() == {"detail": "Too many requests. Please try again later."}
        assert "retry-after" in res3.headers

        # CRUCIAL: Gemini provider was NOT called for rejected 429 request
        # (external provider quota is preserved)
        assert mock_provider.generate_guide.call_count == 2
    finally:
        app.dependency_overrides.pop(get_ai_provider, None)


def test_ai_rate_limit_is_stricter_than_general_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "API_RATE_LIMIT_REQUESTS", 50)
    monkeypatch.setattr(settings, "AI_RATE_LIMIT_REQUESTS", 1)

    mock_provider = MagicMock()
    mock_provider.generate_guide.return_value = PreparednessGuideContent(
        summary="Valid preparedness summary text",
        before=["Step 1"],
        during=["Step 2"],
        after=["Step 3"],
        emergency_kit=["Item 1"],
        important_notes=["Note 1"],
    )
    app.dependency_overrides[get_ai_provider] = lambda: mock_provider

    try:
        # First AI call succeeds
        res_ai = client.post(
            "/api/v1/ai/preparedness-guide", json={"disaster_type": "earthquake"}
        )
        assert res_ai.status_code == 200

        # Second AI call is rejected
        res_ai_blocked = client.post(
            "/api/v1/ai/preparedness-guide", json={"disaster_type": "earthquake"}
        )
        assert res_ai_blocked.status_code == 429

        # But general API endpoint continues to succeed under its own quota
        res_general = client.get("/api/v1/fault-lines")
        assert res_general.status_code == 200
    finally:
        app.dependency_overrides.pop(get_ai_provider, None)


def test_independent_rate_limits_across_distinct_clients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "API_RATE_LIMIT_REQUESTS", 1)

    client1 = TestClient(app, client=("192.168.1.10", 12345))
    client2 = TestClient(app, client=("192.168.1.20", 12345))

    # Client 1 uses quota
    r1 = client1.get("/api/v1/fault-lines")
    assert r1.status_code == 200

    r1_blocked = client1.get("/api/v1/fault-lines")
    assert r1_blocked.status_code == 429

    # Client 2 still has quota available
    r2 = client2.get("/api/v1/fault-lines")
    assert r2.status_code == 200


def test_forwarded_headers_do_not_bypass_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "API_RATE_LIMIT_REQUESTS", 1)

    # Client sends request with spoofed X-Forwarded-For
    r1 = client.get(
        "/api/v1/fault-lines",
        headers={"X-Forwarded-For": "1.1.1.1"},
    )
    assert r1.status_code == 200

    # Second request from same socket with different spoofed IP must still be blocked
    r2 = client.get(
        "/api/v1/fault-lines",
        headers={"X-Forwarded-For": "2.2.2.2"},
    )
    assert r2.status_code == 429


def test_rate_limit_429_exact_contract_stability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that both general and AI 429 rejections return the exact
    stable public contract:
      HTTP 429
      {"detail": "Too many requests. Please try again later."}
      Retry-After: positive integer
    and never leak IP, bucket key, counter, or quota internals.
    Also verifies external AI provider is never invoked on rate limit rejection.
    """
    monkeypatch.setattr(settings, "API_RATE_LIMIT_REQUESTS", 1)
    monkeypatch.setattr(settings, "AI_RATE_LIMIT_REQUESTS", 1)

    mock_provider = MagicMock()
    mock_provider.generate_guide.return_value = PreparednessGuideContent(
        summary="Sample summary",
        before=["Before step"],
        during=["During step"],
        after=["After step"],
        emergency_kit=["Kit item"],
        important_notes=[],
    )
    app.dependency_overrides[get_ai_provider] = lambda: mock_provider

    try:
        # 1. General endpoint rejection contract
        res_gen_ok = client.get("/api/v1/fault-lines")
        assert res_gen_ok.status_code == 200

        res_gen_blocked = client.get("/api/v1/fault-lines")
        assert res_gen_blocked.status_code == 429
        assert res_gen_blocked.json() == {
            "detail": "Too many requests. Please try again later."
        }
        assert res_gen_blocked.json()["detail"] == RATE_LIMIT_DETAIL
        assert "retry-after" in res_gen_blocked.headers
        assert int(res_gen_blocked.headers["retry-after"]) >= 1

        # Confirm no leakage of internals
        raw_text_gen = res_gen_blocked.text
        assert "general:" not in raw_text_gen
        assert "client" not in raw_text_gen
        assert "bucket" not in raw_text_gen
        assert "counter" not in raw_text_gen

        # 2. AI endpoint rejection contract
        res_ai_ok = client.post(
            "/api/v1/ai/preparedness-guide", json={"disaster_type": "earthquake"}
        )
        assert res_ai_ok.status_code == 200
        assert mock_provider.generate_guide.call_count == 1

        res_ai_blocked = client.post(
            "/api/v1/ai/preparedness-guide", json={"disaster_type": "flood"}
        )
        assert res_ai_blocked.status_code == 429
        assert res_ai_blocked.json() == {
            "detail": "Too many requests. Please try again later."
        }
        assert res_ai_blocked.json()["detail"] == RATE_LIMIT_DETAIL
        assert "retry-after" in res_ai_blocked.headers
        assert int(res_ai_blocked.headers["retry-after"]) >= 1

        # Provider must NOT be called for rejected request
        assert mock_provider.generate_guide.call_count == 1

        # Confirm no leakage of internals in AI rejection
        raw_text_ai = res_ai_blocked.text
        assert "ai:" not in raw_text_ai
        assert "client" not in raw_text_ai
        assert "bucket" not in raw_text_ai
        assert "counter" not in raw_text_ai
    finally:
        app.dependency_overrides.pop(get_ai_provider, None)
