"""FastAPI dependency provider for AI integration."""

from app.core.config import settings
from app.integrations.ai.base import PreparednessAIProvider
from app.integrations.ai.gemini import GeminiPreparednessAIProvider
from app.integrations.ai.ollama import OllamaPreparednessAIProvider


def get_ollama_provider() -> OllamaPreparednessAIProvider | None:
    """Return an OllamaPreparednessAIProvider instance configured from settings.

    Returns None if OLLAMA_BASE_URL is unset or whitespace.
    """
    if not settings.OLLAMA_BASE_URL or not settings.OLLAMA_BASE_URL.strip():
        return None

    return OllamaPreparednessAIProvider(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_MODEL,
        timeout=settings.OLLAMA_TIMEOUT_SECONDS,
    )


def get_gemini_provider() -> GeminiPreparednessAIProvider | None:
    """Return a GeminiPreparednessAIProvider instance configured from settings.

    Returns None if GEMINI_API_KEY is unset or whitespace.
    """
    if not settings.GEMINI_API_KEY or not settings.GEMINI_API_KEY.strip():
        return None

    return GeminiPreparednessAIProvider(
        api_key=settings.GEMINI_API_KEY,
        model=settings.GEMINI_MODEL,
        timeout=settings.GEMINI_TIMEOUT_SECONDS,
    )


def get_ai_provider() -> PreparednessAIProvider | None:
    """Return the active AI provider instance or None if not configured.

    Resolves provider strictly based on settings.AI_PROVIDER:
    - 'ollama' (default): returns OllamaPreparednessAIProvider.
    - 'gemini': returns GeminiPreparednessAIProvider if GEMINI_API_KEY is set,
      or None if credentials are missing (service layer maps None to HTTP 503).

    FAIL-CLOSED POLICY:
    Never falls back across providers automatically. If the selected provider is
    unavailable, fails closed without silently contacting the other provider.
    Automated tests may override this dependency using app.dependency_overrides.
    """
    if settings.AI_PROVIDER == "ollama":
        return get_ollama_provider()
    elif settings.AI_PROVIDER == "gemini":
        return get_gemini_provider()

    return None
