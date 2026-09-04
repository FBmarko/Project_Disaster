"""FastAPI dependency provider for AI integration."""

from app.integrations.ai.base import PreparednessAIProvider


def get_ai_provider() -> PreparednessAIProvider | None:
    """Return the active AI provider instance or None if not configured.

    In TASK 11A, no external AI provider SDK is installed or configured for
    production, so this dependency safely returns None by default.
    The service layer detects None and returns HTTP 503 Service Unavailable.
    Automated tests override this dependency using app.dependency_overrides.
    """
    return None
