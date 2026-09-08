"""Tests for AI provider selection and fail-closed fallback policy."""

import json
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.integrations.ai.dependencies import (
    get_ai_provider,
    get_gemini_provider,
    get_ollama_provider,
)
from app.integrations.ai.exceptions import (
    AIProviderMalformedOutputError,
    AIProviderUnavailableError,
)
from app.integrations.ai.gemini import GeminiPreparednessAIProvider
from app.integrations.ai.ollama import OllamaPreparednessAIProvider
from app.main import app
from app.schemas.ai import (
    DisasterType,
    PreparednessGuideRequest,
    SupportedLanguage,
)
from app.services.preparedness_guide import PreparednessGuideService

client = TestClient(app)


def _sample_valid_guide_dict() -> dict[str, object]:
    """Helper returning valid dictionary conforming to PreparednessGuideContent."""
    return {
        "summary": "Deprem anında sakin kalıp güvenli bir noktaya sığının.",
        "priorities": [
            "Çök, Kapan, Tutun pozisyonunu alın.",
            "Pencerelerden ve devrilebilecek eşyalardan uzak durun.",
            "Sarsıntı süresince merdiven ve asansörlere koşmayın.",
        ],
        "emergency_kit": [
            "Kişi başı en az 3 günlük içme suyu",
            "İlk yardım kiti ve acil ilaçlar",
            "El feneri ve yedek piller",
            "Düdük ve çok amaçlı çakı",
        ],
        "communication_plan": [
            "Şehir dışı irtibat kişisi belirleyin.",
            "Hane buluşma noktasını kararlaştırın.",
            "İletişim için SMS tercih edin.",
        ],
        "special_needs": [
            "Çocuklar için teselli malzemesi ve kimlik bilgisi ekleyin.",
        ],
        "important_notes": [
            "Resmi AFAD ve valilik duyurularını takip edin.",
            "Hasarlı binalara yetkililer izin vermeden asla girmeyin.",
        ],
    }


def _make_ollama_envelope(content_str: str) -> dict[str, object]:
    """Helper creating standard Ollama chat API response envelope."""
    return {
        "model": "qwen3.5:2b-q4_K_M",
        "created_at": "2026-09-08T00:00:00Z",
        "message": {
            "role": "assistant",
            "content": content_str,
        },
        "done": True,
        "done_reason": "stop",
    }


# ==============================================================================
# 1. CONFIGURATION & VALIDATION TESTS
# ==============================================================================


def test_config_ai_provider_default_is_ollama() -> None:
    """Default AI_PROVIDER setting is 'ollama' without environment override."""
    default_settings = Settings()
    assert default_settings.AI_PROVIDER == "ollama"


@pytest.mark.parametrize(
    "valid_val,expected",
    [
        ("ollama", "ollama"),
        ("gemini", "gemini"),
        ("OLLAMA", "ollama"),
        ("GEMINI", "gemini"),
        ("  ollama  ", "ollama"),
        ("  gemini  ", "gemini"),
    ],
)
def test_config_ai_provider_supported_values(valid_val: str, expected: str) -> None:
    """Settings accepts and normalizes supported AI_PROVIDER values."""
    s = Settings(AI_PROVIDER=valid_val)  # type: ignore[arg-type]
    assert s.AI_PROVIDER == expected


@pytest.mark.parametrize(
    "invalid_val",
    [
        "claude",
        "openai",
        "deepseek",
        "",
        "   ",
        "invalid",
    ],
)
def test_config_ai_provider_rejects_unsupported_values(invalid_val: str) -> None:
    """Settings rejects any provider string other than 'ollama' or 'gemini'."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(AI_PROVIDER=invalid_val)  # type: ignore[arg-type]
    assert "Unsupported AI_PROVIDER" in str(exc_info.value)


# ==============================================================================
# 2. PROVIDER FACTORY SELECTION TESTS
# ==============================================================================


def test_factory_resolves_ollama_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """When AI_PROVIDER is ollama (default), get_ai_provider returns Ollama provider."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    provider = get_ai_provider()
    assert isinstance(provider, OllamaPreparednessAIProvider)
    assert provider.model == settings.OLLAMA_MODEL
    assert provider.base_url == settings.OLLAMA_BASE_URL
    provider.close()


def test_factory_resolves_ollama_even_when_gemini_key_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When AI_PROVIDER is ollama, GEMINI_API_KEY does NOT trigger Gemini."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "dummy-gemini-key")

    provider = get_ai_provider()
    assert isinstance(provider, OllamaPreparednessAIProvider)
    provider.close()


def test_factory_resolves_gemini_when_explicitly_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When AI_PROVIDER is gemini with key, get_ai_provider returns Gemini provider."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini-key")

    provider = get_ai_provider()
    assert isinstance(provider, GeminiPreparednessAIProvider)
    assert provider.api_key == "test-gemini-key"


def test_factory_gemini_missing_key_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When AI_PROVIDER is gemini but key is missing, get_ai_provider returns None."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    assert get_ai_provider() is None

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "   ")
    assert get_ai_provider() is None


def test_standalone_helpers_instantiate_independently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_ollama_provider and get_gemini_provider operate independently."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini-key")
    ollama_p = get_ollama_provider()
    gemini_p = get_gemini_provider()

    assert isinstance(ollama_p, OllamaPreparednessAIProvider)
    assert isinstance(gemini_p, GeminiPreparednessAIProvider)
    if ollama_p:
        ollama_p.close()


# ==============================================================================
# 3. FAIL-CLOSED FALLBACK POLICY TESTS
# ==============================================================================


def test_fail_closed_ollama_never_calls_gemini(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When Ollama fails, system fails closed with 503 and never invokes Gemini."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key-should-not-be-called")

    # Mock Ollama HTTP transport to simulate network connection failure
    def failing_handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Ollama daemon unreachable")

    transport = httpx.MockTransport(failing_handler)
    mock_ollama_client = httpx.Client(transport=transport)
    failing_ollama_provider = OllamaPreparednessAIProvider(client=mock_ollama_client)

    # Mock Gemini provider to ensure it is never called
    mock_gemini_provider = MagicMock(spec=GeminiPreparednessAIProvider)
    monkeypatch.setattr(
        "app.integrations.ai.dependencies.get_gemini_provider",
        lambda: mock_gemini_provider,
    )

    service = PreparednessGuideService(provider=failing_ollama_provider)
    req = PreparednessGuideRequest(
        disaster_type=DisasterType.EARTHQUAKE,
        language=SupportedLanguage.TR,
    )

    with pytest.raises(HTTPException) as exc_info:
        service.generate_guide(req)

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "AI preparedness service is currently unavailable."
    mock_gemini_provider.generate_guide.assert_not_called()


def test_fail_closed_ollama_malformed_output_never_calls_gemini(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When Ollama returns malformed output, returns 502 and never calls Gemini."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key-should-not-be-called")

    envelope = _make_ollama_envelope("invalid-non-json-output")

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=envelope)

    transport = httpx.MockTransport(handler)
    mock_ollama_client = httpx.Client(transport=transport)
    failing_ollama_provider = OllamaPreparednessAIProvider(client=mock_ollama_client)

    mock_gemini_provider = MagicMock(spec=GeminiPreparednessAIProvider)
    monkeypatch.setattr(
        "app.integrations.ai.dependencies.get_gemini_provider",
        lambda: mock_gemini_provider,
    )

    service = PreparednessGuideService(provider=failing_ollama_provider)
    req = PreparednessGuideRequest(
        disaster_type=DisasterType.EARTHQUAKE,
        language=SupportedLanguage.TR,
    )

    with pytest.raises(HTTPException) as exc_info:
        service.generate_guide(req)

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "AI provider returned an invalid response."
    mock_gemini_provider.generate_guide.assert_not_called()


def test_fail_closed_ollama_timeout_never_calls_gemini(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When Ollama times out, system returns 503 and never calls Gemini."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key-should-not-be-called")

    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Ollama read timeout")

    transport = httpx.MockTransport(handler)
    mock_ollama_client = httpx.Client(transport=transport)
    failing_ollama_provider = OllamaPreparednessAIProvider(client=mock_ollama_client)

    mock_gemini_provider = MagicMock(spec=GeminiPreparednessAIProvider)
    monkeypatch.setattr(
        "app.integrations.ai.dependencies.get_gemini_provider",
        lambda: mock_gemini_provider,
    )

    service = PreparednessGuideService(provider=failing_ollama_provider)
    req = PreparednessGuideRequest(
        disaster_type=DisasterType.EARTHQUAKE,
        language=SupportedLanguage.TR,
    )

    with pytest.raises(HTTPException) as exc_info:
        service.generate_guide(req)

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "AI preparedness service is currently unavailable."
    mock_gemini_provider.generate_guide.assert_not_called()


def test_fail_closed_gemini_never_calls_ollama(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When Gemini fails, system fails closed with 503/502 and never invokes Ollama."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")

    mock_gemini_provider = MagicMock(spec=GeminiPreparednessAIProvider)
    mock_gemini_provider.generate_guide.side_effect = AIProviderUnavailableError(
        "Gemini API quota exhausted"
    )

    mock_ollama_provider = MagicMock(spec=OllamaPreparednessAIProvider)
    monkeypatch.setattr(
        "app.integrations.ai.dependencies.get_ollama_provider",
        lambda: mock_ollama_provider,
    )

    service = PreparednessGuideService(provider=mock_gemini_provider)
    req = PreparednessGuideRequest(
        disaster_type=DisasterType.FLOOD,
        language=SupportedLanguage.TR,
    )

    with pytest.raises(HTTPException) as exc_info:
        service.generate_guide(req)

    assert exc_info.value.status_code == 503
    mock_ollama_provider.generate_guide.assert_not_called()


def test_fail_closed_gemini_malformed_output_never_calls_ollama(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When Gemini returns malformed output, returns 502 and never calls Ollama."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")

    mock_gemini_provider = MagicMock(spec=GeminiPreparednessAIProvider)
    mock_gemini_provider.generate_guide.side_effect = AIProviderMalformedOutputError(
        "Gemini returned invalid payload"
    )

    mock_ollama_provider = MagicMock(spec=OllamaPreparednessAIProvider)
    monkeypatch.setattr(
        "app.integrations.ai.dependencies.get_ollama_provider",
        lambda: mock_ollama_provider,
    )

    service = PreparednessGuideService(provider=mock_gemini_provider)
    req = PreparednessGuideRequest(
        disaster_type=DisasterType.FLOOD,
        language=SupportedLanguage.TR,
    )

    with pytest.raises(HTTPException) as exc_info:
        service.generate_guide(req)

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "AI provider returned an invalid response."
    mock_ollama_provider.generate_guide.assert_not_called()


def test_gemini_selected_without_key_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When Gemini is selected without key, service returns 503 without Ollama."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    mock_ollama_provider = MagicMock(spec=OllamaPreparednessAIProvider)
    monkeypatch.setattr(
        "app.integrations.ai.dependencies.get_ollama_provider",
        lambda: mock_ollama_provider,
    )

    # Ensure no dependency override is active
    app.dependency_overrides.pop(get_ai_provider, None)

    response = client.post(
        "/api/v1/ai/preparedness-guide",
        json={"disaster_type": "earthquake", "language": "tr"},
    )
    assert response.status_code == 503
    assert (
        response.json()["detail"] == "AI preparedness service is currently unavailable."
    )
    mock_ollama_provider.generate_guide.assert_not_called()


# ==============================================================================
# 4. TEAMMATE / ENDPOINT INTEGRATION (NO GEMINI KEY REQUIRED)
# ==============================================================================


def test_endpoint_succeeds_with_default_ollama_and_no_gemini_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Teammate can run AI generation with default Ollama without GEMINI_API_KEY."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    valid_content = _sample_valid_guide_dict()
    envelope = _make_ollama_envelope(json.dumps(valid_content))

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=envelope)

    transport = httpx.MockTransport(handler)
    mock_client = httpx.Client(transport=transport)
    mock_provider = OllamaPreparednessAIProvider(client=mock_client)

    app.dependency_overrides[get_ai_provider] = lambda: mock_provider
    try:
        response = client.post(
            "/api/v1/ai/preparedness-guide",
            json={
                "disaster_type": "earthquake",
                "city": "İstanbul",
                "language": "tr",
                "household_size": 4,
                "has_children": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["generated_by_ai"] is True
        assert data["guide"]["summary"] == valid_content["summary"]
        assert len(data["guide"]["priorities"]) == 3
        assert "AFAD" in data["disclaimer"]
    finally:
        app.dependency_overrides.pop(get_ai_provider, None)
        mock_provider.close()


def test_non_ai_endpoints_and_openapi_load_without_gemini_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-AI endpoints and OpenAPI schema load cleanly with no GEMINI_API_KEY."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    # OpenAPI schema check
    schema = app.openapi()
    assert len(schema["paths"]) == 17

    # Non-AI health / representative endpoint check
    health_resp = client.get("/api/v1/health")
    assert health_resp.status_code == 200
