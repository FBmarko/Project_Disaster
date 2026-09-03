from fastapi import APIRouter

from app.api.v1.router import v1_router
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(v1_router, prefix=settings.API_V1_PREFIX)
