"""Google Gemini AI provider adapter using official google-genai SDK."""

import json
import logging
from typing import Any

import httpx
from google import genai
from google.genai import errors
from pydantic import ValidationError

from app.integrations.ai.base import PreparednessAIProvider
from app.integrations.ai.exceptions import (
    AIProviderError,
    AIProviderMalformedOutputError,
    AIProviderUnavailableError,
)
from app.schemas.ai import PreparednessGuideContent, PreparednessGuideRequest

logger = logging.getLogger(__name__)


class GeminiPreparednessAIProvider(PreparednessAIProvider):
    """Production provider integrating Google Gemini API via official google-genai SDK.

    Uses the modern Interactions API (client.interactions.create) with:
    - store=False for stateless, privacy-preserving generation
    - system_instruction for server-controlled safety policy
    - input for isolated user context
    - structured outputs conforming to PreparednessGuideContent
    - thinking_level="low" and bounded output tokens
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.8-flash",
        timeout: float = 30.0,
        max_output_tokens: int = 2500,
        thinking_level: str = "low",
        client: genai.Client | None = None,
    ) -> None:
        """Initialize Gemini provider with configuration and client.

        Args:
            api_key: Google Gemini API key.
            model: Gemini model identifier (default: "gemini-3.8-flash").
            timeout: Maximum request timeout in seconds.
            max_output_tokens: Maximum output token ceiling for generation.
            thinking_level: Reasoning effort level (default: "low").
            client: Optional pre-configured genai.Client (useful for testing).
        """
        if not api_key or not api_key.strip():
            raise ValueError("GEMINI_API_KEY must not be empty.")

        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_output_tokens = max_output_tokens
        self.thinking_level = thinking_level
        self._client = client

    @property
    def client(self) -> genai.Client:
        """Lazily initialize or return the official genai.Client instance.

        Configures official public HttpOptions with HttpRetryOptions(attempts=0).
        Relies exclusively on the public google-genai SDK interface without
        mutating private or internal SDK configuration.
        """
        if self._client is None:
            http_options = genai.types.HttpOptions(
                retry_options=genai.types.HttpRetryOptions(attempts=0),
            )
            self._client = genai.Client(
                api_key=self.api_key,
                http_options=http_options,
            )
        return self._client

    def generate_guide(
        self,
        request: PreparednessGuideRequest,
        system_prompt: str,
        user_context: str,
    ) -> PreparednessGuideContent:
        """Generate structured disaster preparedness guide via Gemini Interactions API.

        Args:
            request: Validated client request.
            system_prompt: Non-negotiable server-controlled safety policy.
            user_context: Isolated disaster domain context and optional city.

        Returns:
            PreparednessGuideContent: Validated structured guide.

        Raises:
            AIProviderUnavailableError: If provider is unreachable, timed out,
                or quota exceeded.
            AIProviderMalformedOutputError: If provider returns empty or invalid JSON.
            AIProviderError: For upstream server failures or unexpected errors.
        """
        response_format: dict[str, Any] = {
            "type": "text",
            "mime_type": "application/json",
            "schema": PreparednessGuideContent.model_json_schema(),
        }
        generation_config: dict[str, Any] = {
            "thinking_level": self.thinking_level,
            "max_output_tokens": self.max_output_tokens,
        }

        try:
            interaction = self.client.interactions.create(
                model=self.model,
                input=user_context,
                system_instruction=system_prompt,
                store=False,
                response_format=response_format,
                generation_config=generation_config,
                timeout=self.timeout,
            )
        except errors.ClientError as err:
            logger.warning(
                "Gemini ClientError: status=%s, code=%s", err.status, err.code
            )
            if err.code in (401, 403, 429):
                raise AIProviderUnavailableError(
                    "AI provider authentication failed or quota exceeded."
                ) from err
            raise AIProviderError("AI provider client request failed.") from err
        except errors.ServerError as err:
            logger.error("Gemini ServerError: status=%s, code=%s", err.status, err.code)
            raise AIProviderError("Upstream AI provider error.") from err
        except errors.APIError as err:
            logger.error("Gemini APIError: code=%s", getattr(err, "code", None))
            if getattr(err, "code", None) in (401, 403, 429):
                raise AIProviderUnavailableError(
                    "AI provider authentication failed or quota exceeded."
                ) from err
            raise AIProviderError("AI provider encountered an error.") from err
        except (httpx.TimeoutException, TimeoutError) as err:
            logger.warning("Gemini interaction timed out after %ss", self.timeout)
            raise AIProviderUnavailableError("AI provider request timed out.") from err
        except httpx.RequestError as err:
            logger.warning("Gemini network connection error: %s", type(err).__name__)
            raise AIProviderUnavailableError(
                "Network error connecting to AI provider."
            ) from err
        except (
            AIProviderUnavailableError,
            AIProviderMalformedOutputError,
            AIProviderError,
        ):
            raise
        except Exception as err:
            logger.exception(
                "Unexpected error during Gemini interaction: %s", type(err).__name__
            )
            raise AIProviderError(
                "Unexpected error communicating with AI provider."
            ) from err

        output_text = getattr(interaction, "output_text", None)
        if not output_text or not output_text.strip():
            logger.error("Gemini interaction returned empty output_text.")
            raise AIProviderMalformedOutputError(
                "AI provider returned empty guide content."
            )

        try:
            parsed_json = json.loads(output_text)
        except json.JSONDecodeError as err:
            logger.error("Gemini output could not be decoded as JSON.")
            raise AIProviderMalformedOutputError(
                "AI provider returned invalid JSON structure."
            ) from err

        try:
            return PreparednessGuideContent.model_validate(parsed_json)
        except ValidationError as err:
            logger.error("Gemini output failed PreparednessGuideContent schema.")
            raise AIProviderMalformedOutputError(
                "AI provider returned data that does not conform to guide schema."
            ) from err
