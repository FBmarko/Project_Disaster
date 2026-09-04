"""Domain exceptions for AI provider integration."""


class AIProviderError(Exception):
    """Base exception for all AI provider integration failures."""

    def __init__(self, message: str = "AI provider encountered an error.") -> None:
        super().__init__(message)


class AIProviderUnavailableError(AIProviderError):
    """Raised when the AI provider service is not configured or unavailable."""

    def __init__(
        self, message: str = "AI preparedness service is currently unavailable."
    ) -> None:
        super().__init__(message)


class AIProviderMalformedOutputError(AIProviderError):
    """Raised when the AI provider returns an unparseable or invalid payload."""

    def __init__(
        self, message: str = "AI provider returned malformed or invalid output."
    ) -> None:
        super().__init__(message)
