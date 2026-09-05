from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware
from app.core.request_body_limit import RequestBodyLimitMiddleware
from app.core.security import SecurityHeadersMiddleware

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for the AFET360 natural disaster preparedness platform.",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Middleware execution order (Starlette executes in reverse order of addition):
# Request:  CORSMiddleware -> SecurityHeaders -> BodyLimit -> RateLimiter -> Endpoints
# Response: Endpoints -> RateLimiter -> BodyLimit -> SecurityHeaders -> CORSMiddleware
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestBodyLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

app.include_router(api_router)
