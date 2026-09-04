"""Service layer orchestrating AI-powered disaster preparedness guide generation."""

import logging

from fastapi import HTTPException, status
from pydantic import ValidationError

from app.integrations.ai.base import PreparednessAIProvider
from app.integrations.ai.exceptions import (
    AIProviderError,
    AIProviderMalformedOutputError,
    AIProviderUnavailableError,
)
from app.integrations.ai.policy import PreparednessSafetyPolicy
from app.schemas.ai import (
    DEFAULT_AI_DISCLAIMER_EN,
    DEFAULT_AI_DISCLAIMER_TR,
    PreparednessGuideContent,
    PreparednessGuideRequest,
    PreparednessGuideResponse,
    SupportedLanguage,
)

logger = logging.getLogger(__name__)


class PreparednessGuideService:
    """Service providing bounded, structured, safety-checked preparedness guides."""

    def __init__(self, provider: PreparednessAIProvider | None = None) -> None:
        """Initialize service with an optional AI provider instance."""
        self.provider = provider

    def generate_guide(
        self, request: PreparednessGuideRequest
    ) -> PreparednessGuideResponse:
        """Generate, validate, and assemble a complete disaster preparedness guide.

        Args:
            request: Validated client request.

        Returns:
            PreparednessGuideResponse: Validated guide with backend disclaimer.

        Raises:
            HTTPException: 503 if provider unavailable, 502 if upstream fails.
        """
        if self.provider is None:
            logger.info("Preparedness AI guide requested with no provider configured.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI preparedness service is currently unavailable.",
            )

        # 1. Build immutable safety prompt and isolated user context
        system_prompt = PreparednessSafetyPolicy.build_system_prompt(request.language)
        user_context = PreparednessSafetyPolicy.build_user_context(request)

        # 2. Call provider abstraction and catch provider domain exceptions
        try:
            raw_content = self.provider.generate_guide(
                request=request,
                system_prompt=system_prompt,
                user_context=user_context,
            )
        except AIProviderUnavailableError as err:
            logger.warning("AI provider unavailable: %s", err)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI preparedness service is currently unavailable.",
            ) from err
        except AIProviderMalformedOutputError as err:
            logger.error("AI provider returned malformed output: %s", err)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI provider returned an invalid response.",
            ) from err
        except AIProviderError as err:
            logger.error("AI provider encountered an error: %s", err)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Upstream AI provider encountered an error.",
            ) from err
        except Exception as err:
            logger.exception("Unexpected exception calling AI provider: %s", err)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Upstream AI provider encountered an error.",
            ) from err

        # 3. Strictly validate provider output through schema
        try:
            content_dict = (
                raw_content.model_dump()
                if isinstance(raw_content, PreparednessGuideContent)
                else raw_content
            )
            validated_guide = PreparednessGuideContent.model_validate(content_dict)
        except (ValidationError, TypeError) as err:
            logger.error("AI output validation failed against schema: %s", err)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI provider returned an invalid response.",
            ) from err

        # 4. Attach backend-controlled disclaimer based on requested language
        disclaimer = (
            DEFAULT_AI_DISCLAIMER_TR
            if request.language == SupportedLanguage.TR
            else DEFAULT_AI_DISCLAIMER_EN
        )

        return PreparednessGuideResponse(
            disaster_type=request.disaster_type,
            city=request.city,
            language=request.language,
            generated_by_ai=True,
            guide=validated_guide,
            disclaimer=disclaimer,
        )
