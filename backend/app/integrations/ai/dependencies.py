"""FastAPI dependency provider for AI integration."""

from app.core.config import settings
from app.integrations.ai.base import PreparednessAIProvider
from app.integrations.ai.gemini import GeminiPreparednessAIProvider
from app.integrations.ai.ollama import OllamaPreparednessAIProvider


def get_ai_provider() -> PreparednessAIProvider | None:
    """Return the active AI provider instance or None if not configured.

    If GEMINI_API_KEY is unset or empty, returns None.
    The service layer detects None and returns HTTP 503 Service Unavailable.
    When configured, instantiates GeminiPreparednessAIProvider using
    application settings.
    Automated tests may override this dependency using app.dependency_overrides.
    """
    if not settings.GEMINI_API_KEY or not settings.GEMINI_API_KEY.strip():
        return None

    return GeminiPreparednessAIProvider(
        api_key=settings.GEMINI_API_KEY,
        model=settings.GEMINI_MODEL,
        timeout=settings.GEMINI_TIMEOUT_SECONDS,
    )


def get_ollama_provider() -> OllamaPreparednessAIProvider | None:
    """Return an OllamaPreparednessAIProvider instance configured from settings.

    Provided for standalone instantiation, testing, and future provider selection.
    Does NOT change default get_ai_provider behavior in TASK 14C-B.
    """
    if not settings.OLLAMA_BASE_URL or not settings.OLLAMA_BASE_URL.strip():
        return None

    return OllamaPreparednessAIProvider(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_MODEL,
        timeout=settings.OLLAMA_TIMEOUT_SECONDS,
    )
