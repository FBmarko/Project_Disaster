"""Local Ollama AI provider adapter using Ollama HTTP REST API."""

import json
import logging
from typing import Any

import httpx
from pydantic import ValidationError

from app.integrations.ai.base import PreparednessAIProvider
from app.integrations.ai.exceptions import (
    AIProviderError,
    AIProviderMalformedOutputError,
    AIProviderUnavailableError,
)
from app.schemas.ai import (
    PreparednessGuideContent,
    PreparednessGuideRequest,
    SupportedLanguage,
)

logger = logging.getLogger(__name__)


class OllamaPreparednessAIProvider(PreparednessAIProvider):
    """Production provider integrating local Ollama HTTP API with structured output.

    Communicates with local Ollama daemon via POST /api/chat using:
    - pinned model tag (default: "qwen3.5:2b-q4_K_M")
    - stream: False
    - think: False
    - format: PreparednessGuideContent.model_json_schema()
    - options: temperature=0.0, num_ctx=4096, num_predict=800
    - concise production prompt policy adhering to AFET360 safety rules
    - strictly stateless (zero DB writes, zero prompt/guide persistence)
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen3.5:2b-q4_K_M",
        timeout: float = 30.0,
        temperature: float = 0.0,
        num_ctx: int = 4096,
        num_predict: int = 800,
        client: httpx.Client | None = None,
    ) -> None:
        """Initialize Ollama provider with configuration and HTTP client.

        Args:
            base_url: Local Ollama daemon base URL (default: http://127.0.0.1:11434).
            model: Pinned Ollama model identifier (default: "qwen3.5:2b-q4_K_M").
            timeout: Maximum request timeout in seconds (default: 30.0).
            temperature: Sampling temperature for deterministic generation (0.0).
            num_ctx: Context window size in tokens (default: 4096).
            num_predict: Maximum generated tokens ceiling (default: 800).
            client: Optional pre-configured httpx.Client (useful for testing).
        """
        if not base_url or not base_url.strip():
            raise ValueError("OLLAMA_BASE_URL must not be empty.")

        clean_base_url = base_url.strip().rstrip("/")
        if "0.0.0.0" in clean_base_url:
            raise ValueError(
                "OLLAMA_BASE_URL must not use 0.0.0.0 as host. "
                "Use 127.0.0.1 or localhost."
            )

        if not model or not model.strip():
            raise ValueError("OLLAMA_MODEL must not be empty.")

        if timeout <= 0:
            raise ValueError("OLLAMA_TIMEOUT_SECONDS must be greater than 0.")

        self.base_url = clean_base_url
        self.model = model.strip()
        self.timeout = timeout
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.num_predict = num_predict
        self._client = client
        self._owns_client = client is None

    def _get_client(self) -> httpx.Client:
        """Lazily initialize or return the httpx.Client instance."""
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def close(self) -> None:
        """Close underlying HTTP client if owned by this provider instance."""
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    @staticmethod
    def _build_concise_policy(language: SupportedLanguage) -> str:
        """Build concise output formatting guidelines respecting requested language."""
        if language == SupportedLanguage.TR:
            return (
                "\n\nCONCISE CONTENT POLICY & SECTION RULES (MANDATORY):\n"
                "- 'summary': 2-3 kısa ve öz cümle ile genel özet.\n"
                "- 'priorities': 3-5 öz ve kritik öncelik maddesi "
                "(her madde tek bir kısa net cümle olmalıdır).\n"
                "- 'emergency_kit': 5-8 temel malzeme maddesi "
                "(kısa ve net madde adları).\n"
                "- 'communication_plan': 3-5 net aile iletişim adımı.\n"
                "- 'special_needs': Hane durumuna göre 0-4 özel ihtiyaç maddesi.\n"
                "- 'important_notes': Resmi makamlara (AFAD) yönlendirme ve "
                "kritik uyarılardan oluşan 2-4 kısa madde.\n"
                "Açıklamaları gereksiz uzatmaktan, maddeleri tekrarlamaktan ve genel "
                "dolgu ifadelerinden kesinlikle kaçının. Doğrudan ve net olun.\n\n"
                "OUTPUT FORMAT REQUIREMENTS:\n"
                "You must return ONLY valid JSON matching the provided schema. "
                "Do NOT include Markdown code fences (e.g. ```json) or any text "
                "outside the JSON object."
            )
        return (
            "\n\nCONCISE CONTENT POLICY & SECTION RULES (MANDATORY):\n"
            "- 'summary': 2-3 concise sentences providing overview.\n"
            "- 'priorities': 3-5 concise, critical priority items "
            "(each item a single short sentence).\n"
            "- 'emergency_kit': 5-8 essential kit items (short concise item names).\n"
            "- 'communication_plan': 3-5 concise family communication steps.\n"
            "- 'special_needs': 0-4 household-specific items.\n"
            "- 'important_notes': 2-4 concise notes and caveats referencing "
            "official sources.\n"
            "Avoid long essays, repetitive guidance, and generic filler. "
            "Keep each item concise and direct.\n\n"
            "OUTPUT FORMAT REQUIREMENTS:\n"
            "You must return ONLY valid JSON matching the provided schema. "
            "Do NOT include Markdown code fences (e.g. ```json) or any text "
            "outside the JSON object."
        )

    def generate_guide(
        self,
        request: PreparednessGuideRequest,
        system_prompt: str,
        user_context: str,
    ) -> PreparednessGuideContent:
        """Generate structured disaster preparedness guide via local Ollama HTTP API.

        Args:
            request: Validated client request.
            system_prompt: Non-negotiable server-controlled safety policy.
            user_context: Isolated disaster domain context and optional city.

        Returns:
            PreparednessGuideContent: Validated structured guide.

        Raises:
            AIProviderUnavailableError: If Ollama is unreachable, timed out,
                or the requested model is not found/pulled.
            AIProviderMalformedOutputError: If Ollama returns empty, invalid JSON,
                or non-conforming schema content.
            AIProviderError: For non-2xx HTTP responses or unexpected transport errors.
        """
        concise_policy = self._build_concise_policy(request.language)
        effective_system_prompt = f"{system_prompt}{concise_policy}"

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": effective_system_prompt},
                {"role": "user", "content": user_context},
            ],
            "stream": False,
            "think": False,
            "format": PreparednessGuideContent.model_json_schema(),
            "options": {
                "temperature": self.temperature,
                "num_ctx": self.num_ctx,
                "num_predict": self.num_predict,
            },
        }

        client = self._get_client()
        url = f"{self.base_url}/api/chat"

        try:
            response = client.post(url, json=payload, timeout=self.timeout)
        except (httpx.ConnectError, httpx.NetworkError) as err:
            logger.warning("Ollama connection error at %s: %s", self.base_url, err)
            raise AIProviderUnavailableError(
                "AI preparedness service is currently unavailable."
            ) from err
        except httpx.TimeoutException as err:
            logger.warning("Ollama request timed out after %ss: %s", self.timeout, err)
            raise AIProviderUnavailableError("AI provider request timed out.") from err
        except httpx.RequestError as err:
            logger.warning("Ollama HTTP request error: %s", err)
            raise AIProviderUnavailableError(
                "AI preparedness service is currently unavailable."
            ) from err
        except (
            AIProviderUnavailableError,
            AIProviderMalformedOutputError,
            AIProviderError,
        ):
            raise
        except Exception as err:
            logger.exception("Unexpected error connecting to Ollama: %s", err)
            raise AIProviderError(
                "Unexpected error communicating with AI provider."
            ) from err

        if response.status_code == 404:
            logger.warning(
                "Ollama returned 404 for model '%s': %s", self.model, response.text
            )
            raise AIProviderUnavailableError(
                f"AI model '{self.model}' is not available on the local provider."
            )
        elif not (200 <= response.status_code < 300):
            logger.error(
                "Ollama HTTP error status=%s body=%s",
                response.status_code,
                response.text,
            )
            raise AIProviderError(f"AI provider returned HTTP {response.status_code}.")

        try:
            envelope = response.json()
        except Exception as err:
            logger.error(
                "Ollama response could not be parsed as JSON envelope: %s", err
            )
            raise AIProviderMalformedOutputError(
                "AI provider returned invalid response structure."
            ) from err

        if not isinstance(envelope, dict):
            logger.error(
                "Ollama response envelope is not a dictionary: %s", type(envelope)
            )
            raise AIProviderMalformedOutputError(
                "AI provider returned invalid response structure."
            )

        message = envelope.get("message")
        if not isinstance(message, dict):
            logger.error("Ollama response missing message object in envelope.")
            raise AIProviderMalformedOutputError(
                "AI provider returned empty guide content."
            )

        content_text = message.get("content")
        if (
            not content_text
            or not isinstance(content_text, str)
            or not content_text.strip()
        ):
            logger.error("Ollama response message content is empty or not a string.")
            raise AIProviderMalformedOutputError(
                "AI provider returned empty guide content."
            )

        content_str = content_text.strip()
        # Strip markdown fences if present
        if content_str.startswith("```json"):
            content_str = content_str.removeprefix("```json")
        elif content_str.startswith("```"):
            content_str = content_str.removeprefix("```")
        if content_str.endswith("```"):
            content_str = content_str.removesuffix("```")
        content_str = content_str.strip()

        try:
            parsed_data = json.loads(content_str)
        except json.JSONDecodeError as err:
            logger.error("Ollama message content could not be decoded as JSON: %s", err)
            raise AIProviderMalformedOutputError(
                "AI provider returned invalid JSON structure."
            ) from err

        if not isinstance(parsed_data, dict):
            logger.error("Ollama message content parsed to non-dict JSON.")
            raise AIProviderMalformedOutputError(
                "AI provider returned invalid JSON structure."
            )

        try:
            return PreparednessGuideContent.model_validate(parsed_data)
        except ValidationError as err:
            logger.error(
                "Ollama output failed PreparednessGuideContent schema validation: %s",
                err,
            )
            raise AIProviderMalformedOutputError(
                "AI provider returned data that does not conform to guide schema."
            ) from err
