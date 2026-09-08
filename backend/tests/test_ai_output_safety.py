"""Unit and integration tests for AI post-generation output safety hardening."""

import json
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.config import settings
from app.integrations.ai.dependencies import get_ai_provider
from app.integrations.ai.exceptions import AIOutputSafetyViolationError
from app.integrations.ai.gemini import GeminiPreparednessAIProvider
from app.integrations.ai.ollama import OllamaPreparednessAIProvider
from app.integrations.ai.policy import PreparednessSafetyPolicy
from app.main import app
from app.schemas.ai import (
    DisasterType,
    PreparednessGuideContent,
    PreparednessGuideRequest,
    SupportedLanguage,
)
from app.services.preparedness_guide import PreparednessGuideService

client = TestClient(app)


def _sample_valid_guide() -> PreparednessGuideContent:
    """Helper returning a standard compliant, safe PreparednessGuideContent."""
    return PreparednessGuideContent(
        summary="Deprem anında sakin kalıp güvenli bir noktaya sığının.",
        priorities=[
            "Çök, Kapan, Tutun pozisyonunu alın.",
            "Pencerelerden ve devrilebilecek eşyalardan uzak durun.",
            "Sarsıntı süresince merdiven ve asansörlere koşmayın.",
        ],
        emergency_kit=[
            "Kişi başı en az 3 günlük içme suyu",
            "İlk yardım kiti ve acil ilaçlar",
            "El feneri ve yedek piller",
            "Düdük ve çok amaçlı çakı",
        ],
        communication_plan=[
            "Şehir dışı irtibat kişisi belirleyin.",
            "Hane buluşma noktasını kararlaştırın.",
            "İletişim için SMS tercih edin.",
        ],
        special_needs=[
            "Çocuklar için teselli malzemesi ve kimlik bilgisi ekleyin.",
        ],
        important_notes=[
            "Resmi AFAD ve valilik duyurularını takip edin.",
            "Hasarlı binalara yetkililer izin vermeden asla girmeyin.",
        ],
    )


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
# 1. BASELINE SAFETY PASS & TEXT COLLECTION
# ==============================================================================


def test_valid_normal_guide_passes_safety_validation() -> None:
    """Valid, safety-compliant guide passes output safety validation without error."""
    valid_guide = _sample_valid_guide()
    # Must not raise
    PreparednessSafetyPolicy.validate_output_safety(valid_guide)


def test_collect_all_text_segments_includes_all_six_sections() -> None:
    """Helper extracts user-visible text segments from all six guide sections."""
    guide = _sample_valid_guide()
    segments = PreparednessSafetyPolicy.collect_all_text_segments(guide)

    assert len(segments) == 14
    assert guide.summary in segments
    for item in guide.priorities:
        assert item in segments
    for item in guide.emergency_kit:
        assert item in segments
    for item in guide.communication_plan:
        assert item in segments
    for item in guide.special_needs:
        assert item in segments
    for item in guide.important_notes:
        assert item in segments


@pytest.mark.parametrize(
    "section_name",
    [
        "summary",
        "priorities",
        "emergency_kit",
        "communication_plan",
        "special_needs",
        "important_notes",
    ],
)
def test_all_six_sections_are_inspected_for_safety(section_name: str) -> None:
    """A prohibited claim injected into ANY of the 6 sections triggers rejection."""
    valid = _sample_valid_guide()
    prohibited_text = "Yarın İstanbul'da deprem olacak."

    data = valid.model_dump()
    if section_name == "summary":
        data["summary"] = prohibited_text
    else:
        data[section_name].append(prohibited_text)

    unsafe_guide = PreparednessGuideContent.model_validate(data)

    with pytest.raises(AIOutputSafetyViolationError):
        PreparednessSafetyPolicy.validate_output_safety(unsafe_guide)


# ==============================================================================
# 2. TRUE POSITIVE REJECTIONS (TURKISH & ENGLISH)
# ==============================================================================


@pytest.mark.parametrize(
    "unsafe_phrase,expected_category",
    [
        ("Yarın İstanbul'da deprem olacak.", "PREDICTION_TR"),
        ("Bu hafta deprem gerçekleşecek.", "PREDICTION_TR"),
        ("Gelecek ay büyük bir afet meydana gelecek.", "PREDICTION_TR"),
        ("Deprem mutlaka olacak ve can kaybı yaratacak.", "PREDICTION_TR"),
        ("Bu hafta deprem olasılığı %80.", "PROBABILITY_CLAIM"),
        ("Deprem ihtimali %90 seviyesindedir.", "PROBABILITY_CLAIM"),
        ("Yüzde 75 ihtimalle deprem gerçekleşecek.", "PROBABILITY_CLAIM"),
        ("Bu bina güvenlidir.", "BUILDING_GUARANTEE"),
        ("Bu bina tamamen güvenlidir.", "BUILDING_GUARANTEE"),
        ("Eviniz depremde tamamen güvenlidir.", "BUILDING_GUARANTEE"),
        ("Bu rota güvenlidir.", "ROUTE_GUARANTEE"),
        ("Bu güzergah kesinlikle güvenlidir.", "ROUTE_GUARANTEE"),
        ("Tahliye rotası güvenlidir.", "ROUTE_GUARANTEE"),
        ("AFAD şu anda Antalya için tahliye emri verdi.", "LIVE_WARNING"),
        ("AFAD tahliye emri verdi.", "LIVE_WARNING"),
        ("Ben AFAD yetkilisiyim.", "FALSE_AUTHORITY"),
        ("AFAD olarak sizlere bildiririz.", "FALSE_AUTHORITY"),
    ],
)
def test_turkish_prohibited_claims_rejected(
    unsafe_phrase: str, expected_category: str
) -> None:
    """Deterministic validation catches prohibited Turkish claims."""
    valid = _sample_valid_guide()
    data = valid.model_dump()
    data["summary"] = f"Güvenli olun. {unsafe_phrase}"
    guide = PreparednessGuideContent.model_validate(data)

    with pytest.raises(AIOutputSafetyViolationError) as exc_info:
        PreparednessSafetyPolicy.validate_output_safety(guide)

    assert expected_category in str(exc_info.value)


@pytest.mark.parametrize(
    "unsafe_phrase,expected_category",
    [
        ("An earthquake will happen tomorrow.", "PREDICTION_EN"),
        ("An earthquake will strike next week.", "PREDICTION_EN"),
        ("A disaster will occur soon.", "PREDICTION_EN"),
        ("There is an 80% chance of an earthquake tomorrow.", "PROBABILITY_CLAIM"),
        ("70% probability of an earthquake this week.", "PROBABILITY_CLAIM"),
        ("This building is safe during an earthquake.", "BUILDING_GUARANTEE"),
        ("Your house is safe.", "BUILDING_GUARANTEE"),
        ("This route is guaranteed safe.", "ROUTE_GUARANTEE"),
        ("This evacuation route is safe.", "ROUTE_GUARANTEE"),
        ("AFAD has just issued an evacuation order.", "LIVE_WARNING"),
        ("Evacuation order has just been issued by AFAD.", "LIVE_WARNING"),
        ("As AFAD, we order everyone to evacuate.", "FALSE_AUTHORITY"),
        ("I am an AFAD official.", "FALSE_AUTHORITY"),
    ],
)
def test_english_prohibited_claims_rejected(
    unsafe_phrase: str, expected_category: str
) -> None:
    """Deterministic validation catches prohibited English claims."""
    valid = _sample_valid_guide()
    data = valid.model_dump()
    data["summary"] = f"Stay calm. {unsafe_phrase}"
    guide = PreparednessGuideContent.model_validate(data)

    with pytest.raises(AIOutputSafetyViolationError) as exc_info:
        PreparednessSafetyPolicy.validate_output_safety(guide)

    assert expected_category in str(exc_info.value)


# ==============================================================================
# 3. FALSE POSITIVE RESISTANCE
# ==============================================================================


@pytest.mark.parametrize(
    "benign_statement",
    [
        "Depremlerin tam zamanını önceden bilmek mümkün değildir.",
        "Depremler kesin olarak tahmin edilemez.",
        "It is not possible to predict the exact time of an earthquake.",
        "Earthquakes cannot be predicted in advance.",
        "Binanızın güvenliği için yetkili uzman değerlendirmesi gerekir.",
        "Building safety requires professional structural evaluation.",
        "Hasarlı binalara yetkililer izin vermeden asla girmeyin.",
        "Do not enter damaged buildings after an event.",
        "Resmî yönlendirmeleri ve güncel yol durumunu kontrol edin.",
        "Follow official route guidance and emergency personnel.",
        "Rota koşulları değişebilir; resmî yönlendirmeleri izleyin.",
        "AFAD'ın resmî duyurularını takip edin.",
        "Follow official announcements from AFAD.",
        "AFAD rehberine göre hareket edin.",
        "According to official AFAD guidelines, stay indoors.",
        "112'yi yalnız acil durumlarda arayın.",
        "Kişi başı en az 3 günlük içme suyu hazırlayın.",
        "4 kişilik bir aile için temel ihtiyaç malzemeleri.",
        "72 saat yetecek kuru gıda stoğu yapın.",
        "Prepare 3 days of water per person for a 4-person family.",
    ],
)
def test_false_positive_resistance_for_legitimate_guidance(
    benign_statement: str,
) -> None:
    """Legitimate preparedness advice and disclaimers must never be rejected."""
    valid = _sample_valid_guide()
    data = valid.model_dump()
    data["summary"] = benign_statement
    guide = PreparednessGuideContent.model_validate(data)

    # Must pass without raising
    PreparednessSafetyPolicy.validate_output_safety(guide)


# ==============================================================================
# 4. PROVIDER-NEUTRAL SERVICE & PUBLIC ERROR CONTRACT
# ==============================================================================


def test_service_maps_safety_violation_to_502() -> None:
    """Service maps AIOutputSafetyViolationError to HTTP 502 with sanitized message."""
    unsafe_content = _sample_valid_guide()
    unsafe_dict = unsafe_content.model_dump()
    unsafe_dict["summary"] = "Yarın İstanbul'da deprem olacak."
    unsafe_guide = PreparednessGuideContent.model_validate(unsafe_dict)

    mock_provider = MagicMock()
    mock_provider.generate_guide.return_value = unsafe_guide

    service = PreparednessGuideService(provider=mock_provider)
    req = PreparednessGuideRequest(
        disaster_type=DisasterType.EARTHQUAKE,
        language=SupportedLanguage.TR,
    )

    with pytest.raises(HTTPException) as exc_info:
        service.generate_guide(req)

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "AI provider returned an invalid response."


def test_public_endpoint_does_not_leak_dangerous_generated_text() -> None:
    """Unsafe output text is never leaked in HTTP 502 detail or body."""
    secret_leak_phrase = "Yarın İstanbul'da kesinlikle deprem olacak."
    unsafe_dict = _sample_valid_guide().model_dump()
    unsafe_dict["summary"] = secret_leak_phrase
    envelope = _make_ollama_envelope(json.dumps(unsafe_dict))

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=envelope)

    transport = httpx.MockTransport(handler)
    mock_client = httpx.Client(transport=transport)
    mock_provider = OllamaPreparednessAIProvider(client=mock_client)

    app.dependency_overrides[get_ai_provider] = lambda: mock_provider
    try:
        response = client.post(
            "/api/v1/ai/preparedness-guide",
            json={"disaster_type": "earthquake", "language": "tr"},
        )
        assert response.status_code == 502
        resp_json = response.json()
        assert resp_json["detail"] == "AI provider returned an invalid response."
        assert secret_leak_phrase not in response.text
        assert "PREDICTION" not in response.text
    finally:
        app.dependency_overrides.pop(get_ai_provider, None)
        mock_provider.close()


# ==============================================================================
# 5. PROVIDER BYPASS PROOF & FAIL-CLOSED INTEGRATION
# ==============================================================================


def test_safety_cannot_be_bypassed_by_switching_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post-generation safety is strictly provider-neutral for Ollama and Gemini."""
    unsafe_dict = _sample_valid_guide().model_dump()
    unsafe_dict["summary"] = "Bu bina tamamen güvenlidir."
    unsafe_guide = PreparednessGuideContent.model_validate(unsafe_dict)

    req = PreparednessGuideRequest(
        disaster_type=DisasterType.EARTHQUAKE,
        language=SupportedLanguage.TR,
    )

    # 1. Ollama provider returning unsafe guide
    mock_ollama = MagicMock(spec=OllamaPreparednessAIProvider)
    mock_ollama.generate_guide.return_value = unsafe_guide
    service_ollama = PreparednessGuideService(provider=mock_ollama)

    with pytest.raises(HTTPException) as exc_ollama:
        service_ollama.generate_guide(req)
    assert exc_ollama.value.status_code == 502

    # 2. Gemini provider returning unsafe guide
    mock_gemini = MagicMock(spec=GeminiPreparednessAIProvider)
    mock_gemini.generate_guide.return_value = unsafe_guide
    service_gemini = PreparednessGuideService(provider=mock_gemini)

    with pytest.raises(HTTPException) as exc_gemini:
        service_gemini.generate_guide(req)
    assert exc_gemini.value.status_code == 502


def test_unsafe_output_does_not_trigger_other_provider_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When selected Ollama produces unsafe output, Gemini is NOT invoked."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "dummy-gemini-key")

    unsafe_dict = _sample_valid_guide().model_dump()
    unsafe_dict["summary"] = "Bu rota güvenlidir."
    unsafe_guide = PreparednessGuideContent.model_validate(unsafe_dict)

    mock_ollama = MagicMock(spec=OllamaPreparednessAIProvider)
    mock_ollama.generate_guide.return_value = unsafe_guide

    mock_gemini = MagicMock(spec=GeminiPreparednessAIProvider)
    monkeypatch.setattr(
        "app.integrations.ai.dependencies.get_gemini_provider",
        lambda: mock_gemini,
    )

    service = PreparednessGuideService(provider=mock_ollama)
    req = PreparednessGuideRequest(
        disaster_type=DisasterType.EARTHQUAKE,
        language=SupportedLanguage.TR,
    )

    with pytest.raises(HTTPException) as exc_info:
        service.generate_guide(req)

    assert exc_info.value.status_code == 502
    mock_gemini.generate_guide.assert_not_called()


# ==============================================================================
# 6. CONCISE PROMPT POLICY & OPENAPI INVARIANTS
# ==============================================================================


def test_concise_policy_is_present_in_shared_system_prompt() -> None:
    """System prompts contain explicit preferred concise section targets."""
    prompt_tr = PreparednessSafetyPolicy.build_system_prompt(SupportedLanguage.TR)
    prompt_en = PreparednessSafetyPolicy.build_system_prompt(SupportedLanguage.EN)

    # Turkish concise constraints
    assert "2-3 kısa ve öz cümle" in prompt_tr
    assert "3-5" in prompt_tr
    assert "5-8" in prompt_tr
    assert "0-4" in prompt_tr
    assert "2-4" in prompt_tr
    assert "aşmayın" in prompt_tr
    assert "AFAD" in prompt_tr

    # English concise constraints
    assert "2-3 concise sentences" in prompt_en
    assert "3-5" in prompt_en
    assert "5-8" in prompt_en
    assert "0-4" in prompt_en
    assert "2-4" in prompt_en
    assert "do not exceed" in prompt_en.lower()
    assert "AFAD" in prompt_en


def test_openapi_schema_remains_exactly_17_paths() -> None:
    """Public OpenAPI schema contains exactly 17 paths with no new endpoints."""
    schema = app.openapi()
    assert len(schema["paths"]) == 17
