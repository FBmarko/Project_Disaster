"""Provider abstraction interface for AI disaster preparedness guides."""

from abc import ABC, abstractmethod

from app.schemas.ai import PreparednessGuideContent, PreparednessGuideRequest


class PreparednessAIProvider(ABC):
    """Abstract interface for disaster preparedness AI generation providers.

    Decouples service logic and endpoint definitions from any specific vendor SDK.
    """

    @abstractmethod
    def generate_guide(
        self,
        request: PreparednessGuideRequest,
        system_prompt: str,
        user_context: str,
    ) -> PreparednessGuideContent:
        """Generate structured preparedness guide content matching the schema.

        Args:
            request: Validated client request.
            system_prompt: Non-negotiable safety rules and schema constraints.
            user_context: Isolated domain-specific parameters and city context.

        Returns:
            PreparednessGuideContent: Strongly typed, validated guide content.

        Raises:
            AIProviderUnavailableError: If provider cannot be reached.
            AIProviderMalformedOutputError: If provider returns invalid data.
            AIProviderError: For other upstream provider failures.
        """
        raise NotImplementedError
