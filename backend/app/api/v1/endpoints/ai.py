"""Public REST API endpoints for AI-powered disaster preparedness guides."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.integrations.ai.base import PreparednessAIProvider
from app.integrations.ai.dependencies import get_ai_provider
from app.schemas.ai import PreparednessGuideRequest, PreparednessGuideResponse
from app.services.preparedness_guide import PreparednessGuideService

router = APIRouter()


@router.post(
    "/preparedness-guide",
    response_model=PreparednessGuideResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate AI disaster preparedness guide",
    description=(
        "Generate a structured preparedness guide for a specified disaster type "
        "(earthquake, flood, fire) and language ('tr' or 'en'). "
        "Returns UI-ready sections with a backend legal safety disclaimer. "
        "Optional city context provides geographic framing only, never real-time "
        "status or building safety claims. If no AI provider is configured, "
        "returns HTTP 503 Service Unavailable."
    ),
    responses={
        status.HTTP_200_OK: {
            "description": "Structured AI preparedness guide successfully generated.",
            "model": PreparednessGuideResponse,
        },
        status.HTTP_413_CONTENT_TOO_LARGE: {
            "description": (
                "Request body exceeds the configured maximum permitted size."
            ),
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Validation error on inputs or unpermitted extra fields.",
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "description": "Rate limit exceeded for AI generation requests.",
        },
        status.HTTP_502_BAD_GATEWAY: {
            "description": "Upstream AI provider error or invalid structured output.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "AI preparedness service is unconfigured or unavailable.",
        },
    },
)
def generate_preparedness_guide(
    request: PreparednessGuideRequest,
    provider: Annotated[PreparednessAIProvider | None, Depends(get_ai_provider)] = None,
) -> PreparednessGuideResponse:
    """Generate structured preparedness guide using the configured AI provider."""
    service = PreparednessGuideService(provider=provider)
    return service.generate_guide(request)
