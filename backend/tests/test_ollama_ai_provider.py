"""Unit tests for OllamaPreparednessAIProvider with mocked offline HTTP transport."""

import json
from typing import Any

import httpx
import pytest

from app.core.config import settings
from app.integrations.ai.dependencies import get_ollama_provider
from app.integrations.ai.exceptions import (
    AIProviderError,
    AIProviderMalformedOutputError,
    AIProviderUnavailableError,
)
from app.integrations.ai.ollama import OllamaPreparednessAIProvider
from app.integrations.ai.policy import PreparednessSafetyPolicy
from app.schemas.ai import (
    DisasterType,
    PreparednessGuideContent,
    PreparednessGuideRequest,
    SupportedLanguage,
)
from app.services.preparedness_guide import PreparednessGuideService


def _sample_valid_guide_dict() -> dict[str, Any]:
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
            "Bozulmayan konserve gıdalar",
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


def _make_ollama_envelope(content_str: str) -> dict[str, Any]:
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
# 1. INITIALIZATION & CONFIGURATION VALIDATION
# ==============================================================================


def test_ollama_provider_init_defaults() -> None:
    """Provider initializes with locked default values."""
    provider = OllamaPreparednessAIProvider()
    assert provider.base_url == "http://127.0.0.1:11434"
    assert provider.model == "qwen3.5:2b-q4_K_M"
    assert provider.timeout == 30.0
    assert provider.temperature == 0.0
    assert provider.num_ctx == 4096
    assert provider.num_predict == 800
    provider.close()


def test_ollama_provider_init_custom() -> None:
    """Provider properly stores custom configurations."""
    provider = OllamaPreparednessAIProvider(
        base_url="http://127.0.0.1:11435/",
        model="qwen3.5:4b-q4_K_M",
        timeout=25.0,
        temperature=0.0,
        num_ctx=2048,
        num_predict=600,
    )
    assert provider.base_url == "http://127.0.0.1:11435"
    assert provider.model == "qwen3.5:4b-q4_K_M"
    assert provider.timeout == 25.0
    assert provider.num_ctx == 2048
    assert provider.num_predict == 600
    provider.close()


@pytest.mark.parametrize("bad_url", ["", "   "])
def test_ollama_provider_init_empty_url(bad_url: str) -> None:
    """Provider rejects empty base URL."""
    with pytest.raises(ValueError, match="OLLAMA_BASE_URL must not be empty"):
        OllamaPreparednessAIProvider(base_url=bad_url)


def test_ollama_provider_init_rejects_0000() -> None:
    """Provider rejects binding to 0.0.0.0."""
    with pytest.raises(ValueError, match="must not use 0.0.0.0"):
        OllamaPreparednessAIProvider(base_url="http://0.0.0.0:11434")


@pytest.mark.parametrize("bad_model", ["", "   "])
def test_ollama_provider_init_empty_model(bad_model: str) -> None:
    """Provider rejects empty model identifier."""
    with pytest.raises(ValueError, match="OLLAMA_MODEL must not be empty"):
        OllamaPreparednessAIProvider(model=bad_model)


@pytest.mark.parametrize("bad_timeout", [0.0, -5.0])
def test_ollama_provider_init_invalid_timeout(bad_timeout: float) -> None:
    """Provider rejects non-positive timeout."""
    with pytest.raises(
        ValueError, match="OLLAMA_TIMEOUT_SECONDS must be greater than 0"
    ):
        OllamaPreparednessAIProvider(timeout=bad_timeout)


# ==============================================================================
# 2. SUCCESSFUL GENERATION & OUTBOUND CONTRACT VERIFICATION
# ==============================================================================


def test_ollama_provider_successful_generation_and_contract() -> None:
    """Provider sends locked parameters and parses valid structured output."""
    captured_requests: list[httpx.Request] = []
    valid_content = _sample_valid_guide_dict()
    envelope = _make_ollama_envelope(json.dumps(valid_content))

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json=envelope)

    transport = httpx.MockTransport(handler)
    mock_client = httpx.Client(transport=transport)

    provider = OllamaPreparednessAIProvider(client=mock_client)
    req = PreparednessGuideRequest(
        disaster_type=DisasterType.EARTHQUAKE,
        city="İstanbul",
        language=SupportedLanguage.TR,
        household_size=4,
        has_children=True,
    )
    sys_prompt = PreparednessSafetyPolicy.build_system_prompt(req.language)
    user_ctx = PreparednessSafetyPolicy.build_user_context(req)

    result = provider.generate_guide(req, sys_prompt, user_ctx)

    assert isinstance(result, PreparednessGuideContent)
    assert result.summary == valid_content["summary"]
    assert len(result.priorities) == len(valid_content["priorities"])
    assert len(result.emergency_kit) == len(valid_content["emergency_kit"])

    # Outbound contract assertions
    assert len(captured_requests) == 1
    outbound = captured_requests[0]
    assert outbound.method == "POST"
    assert outbound.url == "http://127.0.0.1:11434/api/chat"

    body = json.loads(outbound.content.decode("utf-8"))
    assert body["model"] == "qwen3.5:2b-q4_K_M"
    assert body["stream"] is False
    assert body["think"] is False
    assert body["format"] == PreparednessGuideContent.model_json_schema()
    assert body["options"] == {
        "temperature": 0.0,
        "num_ctx": 4096,
        "num_predict": 800,
    }

    # Verify messages
    messages = body["messages"]
    assert len(messages) == 2
    system_msg = messages[0]["content"]
    user_msg = messages[1]["content"]

    # System message assertions
    assert "MANDATORY SAFETY POLICY & STRICT PROHIBITIONS" in system_msg
    assert (
        "Gelecekteki afetler için kesinlikle zaman veya tarih tahmini yapmayın"
        in system_msg
    )
    assert "CONCISE CONTENT POLICY & SECTION RULES (MANDATORY)" in system_msg
    assert "2-3 kısa ve öz cümle" in system_msg
    assert "3-5 öz ve kritik öncelik maddesi" in system_msg
    assert "5-8 temel malzeme maddesi" in system_msg

    # User context assertions
    assert "DISASTER TYPE: EARTHQUAKE" in user_msg
    assert "Geographic Context: İstanbul" in user_msg
    assert "Household size: 4 person(s)" in user_msg
    assert "Children in household: Yes" in user_msg

    # No forbidden fields
    assert "api_key" not in body
    assert "tools" not in body
    assert "store" not in body


def test_ollama_provider_english_concise_policy() -> None:
    """Provider injects English concise policy instructions for EN requests."""
    captured_requests: list[httpx.Request] = []
    valid_content = _sample_valid_guide_dict()
    envelope = _make_ollama_envelope(json.dumps(valid_content))

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json=envelope)

    transport = httpx.MockTransport(handler)
    mock_client = httpx.Client(transport=transport)
    provider = OllamaPreparednessAIProvider(client=mock_client)

    req = PreparednessGuideRequest(
        disaster_type=DisasterType.FLOOD,
        city="Samsun",
        language=SupportedLanguage.EN,
        household_size=2,
        has_elderly_person=True,
    )
    sys_prompt = PreparednessSafetyPolicy.build_system_prompt(req.language)
    user_ctx = PreparednessSafetyPolicy.build_user_context(req)

    provider.generate_guide(req, sys_prompt, user_ctx)

    assert len(captured_requests) == 1
    body = json.loads(captured_requests[0].content.decode("utf-8"))
    system_msg = body["messages"][0]["content"]

    assert "CONCISE CONTENT POLICY & SECTION RULES (MANDATORY)" in system_msg
    assert "2-3 concise sentences" in system_msg
    assert "3-5 concise, critical priority items" in system_msg
    assert "5-8 essential kit items" in system_msg


def test_ollama_provider_handles_markdown_code_fences() -> None:
    """Provider cleanly strips markdown fences from returned content."""
    valid_content = _sample_valid_guide_dict()
    fenced_json = f"```json\n{json.dumps(valid_content)}\n```"
    envelope = _make_ollama_envelope(fenced_json)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=envelope)

    transport = httpx.MockTransport(handler)
    mock_client = httpx.Client(transport=transport)
    provider = OllamaPreparednessAIProvider(client=mock_client)

    req = PreparednessGuideRequest(
        disaster_type=DisasterType.FIRE,
        language=SupportedLanguage.TR,
    )
    result = provider.generate_guide(req, "system prompt", "user context")
    assert isinstance(result, PreparednessGuideContent)
    assert result.summary == valid_content["summary"]


# ==============================================================================
# 3. SCHEMA & MALFORMED OUTPUT HANDLING
# ==============================================================================


def test_ollama_provider_rejects_pydantic_constraint_violation() -> None:
    """Provider raises error if content violates schema constraints."""
    invalid_content = _sample_valid_guide_dict()
    # priorities requires min_length=1; empty list violates Pydantic constraints
    invalid_content["priorities"] = []
    envelope = _make_ollama_envelope(json.dumps(invalid_content))

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=envelope)

    transport = httpx.MockTransport(handler)
    mock_client = httpx.Client(transport=transport)
    provider = OllamaPreparednessAIProvider(client=mock_client)

    req = PreparednessGuideRequest(
        disaster_type=DisasterType.EARTHQUAKE,
        language=SupportedLanguage.TR,
    )
    with pytest.raises(
        AIProviderMalformedOutputError, match="does not conform to guide schema"
    ):
        provider.generate_guide(req, "system prompt", "user context")


def test_ollama_provider_rejects_summary_too_short() -> None:
    """Provider rejects summary shorter than 10 characters."""
    invalid_content = _sample_valid_guide_dict()
    invalid_content["summary"] = "Short"
    envelope = _make_ollama_envelope(json.dumps(invalid_content))

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=envelope)

    transport = httpx.MockTransport(handler)
    mock_client = httpx.Client(transport=transport)
    provider = OllamaPreparednessAIProvider(client=mock_client)

    req = PreparednessGuideRequest(
        disaster_type=DisasterType.EARTHQUAKE,
        language=SupportedLanguage.TR,
    )
    with pytest.raises(
        AIProviderMalformedOutputError, match="does not conform to guide schema"
    ):
        provider.generate_guide(req, "system prompt", "user context")


def test_ollama_provider_rejects_unparseable_json_content() -> None:
    """Provider raises AIProviderMalformedOutputError for invalid JSON syntax."""
    envelope = _make_ollama_envelope('{"summary": "incomplete json...')

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=envelope)

    transport = httpx.MockTransport(handler)
    mock_client = httpx.Client(transport=transport)
    provider = OllamaPreparednessAIProvider(client=mock_client)

    req = PreparednessGuideRequest(
        disaster_type=DisasterType.EARTHQUAKE,
        language=SupportedLanguage.TR,
    )
    with pytest.raises(AIProviderMalformedOutputError, match="invalid JSON structure"):
        provider.generate_guide(req, "system prompt", "user context")


@pytest.mark.parametrize("bad_content", ["", "   ", "\n\t"])
def test_ollama_provider_rejects_empty_content(bad_content: str) -> None:
    """Provider raises AIProviderMalformedOutputError for empty/whitespace content."""
    envelope = _make_ollama_envelope(bad_content)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=envelope)

    transport = httpx.MockTransport(handler)
    mock_client = httpx.Client(transport=transport)
    provider = OllamaPreparednessAIProvider(client=mock_client)

    req = PreparednessGuideRequest(
        disaster_type=DisasterType.EARTHQUAKE,
        language=SupportedLanguage.TR,
    )
    with pytest.raises(AIProviderMalformedOutputError, match="empty guide content"):
        provider.generate_guide(req, "system prompt", "user context")


def test_ollama_provider_rejects_malformed_envelope() -> None:
    """Provider raises error if envelope lacks message object."""
    envelope = {"error": "unexpected structure"}

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=envelope)

    transport = httpx.MockTransport(handler)
    mock_client = httpx.Client(transport=transport)
    provider = OllamaPreparednessAIProvider(client=mock_client)

    req = PreparednessGuideRequest(
        disaster_type=DisasterType.EARTHQUAKE,
        language=SupportedLanguage.TR,
    )
    with pytest.raises(AIProviderMalformedOutputError, match="empty guide content"):
        provider.generate_guide(req, "system prompt", "user context")


# ==============================================================================
# 4. TRANSPORT, TIMEOUT & HTTP ERROR HANDLING
# ==============================================================================


def test_ollama_provider_connection_error_maps_to_unavailable() -> None:
    """Network connection failure maps to AIProviderUnavailableError."""

    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    transport = httpx.MockTransport(handler)
    mock_client = httpx.Client(transport=transport)
    provider = OllamaPreparednessAIProvider(client=mock_client)

    req = PreparednessGuideRequest(
        disaster_type=DisasterType.EARTHQUAKE,
        language=SupportedLanguage.TR,
    )
    with pytest.raises(AIProviderUnavailableError, match="currently unavailable"):
        provider.generate_guide(req, "system prompt", "user context")


def test_ollama_provider_timeout_maps_to_unavailable() -> None:
    """Request timeout maps to AIProviderUnavailableError."""

    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Request timed out")

    transport = httpx.MockTransport(handler)
    mock_client = httpx.Client(transport=transport)
    provider = OllamaPreparednessAIProvider(client=mock_client)

    req = PreparednessGuideRequest(
        disaster_type=DisasterType.EARTHQUAKE,
        language=SupportedLanguage.TR,
    )
    with pytest.raises(AIProviderUnavailableError, match="request timed out"):
        provider.generate_guide(req, "system prompt", "user context")


def test_ollama_provider_404_model_missing_maps_to_unavailable() -> None:
    """HTTP 404 (model not found) maps to AIProviderUnavailableError without pulling."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={"error": "model 'qwen3.5:2b-q4_K_M' not found, try pulling it first"},
        )

    transport = httpx.MockTransport(handler)
    mock_client = httpx.Client(transport=transport)
    provider = OllamaPreparednessAIProvider(client=mock_client)

    req = PreparednessGuideRequest(
        disaster_type=DisasterType.EARTHQUAKE,
        language=SupportedLanguage.TR,
    )
    with pytest.raises(
        AIProviderUnavailableError, match="not available on the local provider"
    ):
        provider.generate_guide(req, "system prompt", "user context")


def test_ollama_provider_500_maps_to_provider_error() -> None:
    """HTTP 500 server error maps to AIProviderError."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(handler)
    mock_client = httpx.Client(transport=transport)
    provider = OllamaPreparednessAIProvider(client=mock_client)

    req = PreparednessGuideRequest(
        disaster_type=DisasterType.EARTHQUAKE,
        language=SupportedLanguage.TR,
    )
    with pytest.raises(AIProviderError, match="HTTP 500"):
        provider.generate_guide(req, "system prompt", "user context")


# ==============================================================================
# 5. SERVICE INTEGRATION & DEPENDENCY FACTORY
# ==============================================================================


def test_ollama_provider_with_preparedness_guide_service() -> None:
    """PreparednessGuideService integrates with OllamaPreparednessAIProvider."""
    valid_content = _sample_valid_guide_dict()
    envelope = _make_ollama_envelope(json.dumps(valid_content))

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=envelope)

    transport = httpx.MockTransport(handler)
    mock_client = httpx.Client(transport=transport)
    provider = OllamaPreparednessAIProvider(client=mock_client)

    service = PreparednessGuideService(provider=provider)
    req = PreparednessGuideRequest(
        disaster_type=DisasterType.EARTHQUAKE,
        city="İzmir",
        language=SupportedLanguage.TR,
    )
    response = service.generate_guide(req)

    assert response.disaster_type == DisasterType.EARTHQUAKE
    assert response.city == "İzmir"
    assert response.generated_by_ai is True
    assert response.guide.summary == valid_content["summary"]
    assert "AFAD" in response.disclaimer


def test_get_ollama_provider_dependency_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_ollama_provider correctly instantiates provider from settings."""
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "qwen3.5:2b-q4_K_M")
    monkeypatch.setattr(settings, "OLLAMA_TIMEOUT_SECONDS", 20.0)

    provider = get_ollama_provider()
    assert isinstance(provider, OllamaPreparednessAIProvider)
    assert provider.base_url == "http://127.0.0.1:11434"
    assert provider.model == "qwen3.5:2b-q4_K_M"
    assert provider.timeout == 20.0
    provider.close()
