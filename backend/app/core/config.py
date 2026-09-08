from typing import Literal

from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    APP_NAME: str = "AFET360 API"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database configuration (safe development defaults)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "afet360"
    POSTGRES_USER: str = "afet360"
    POSTGRES_PASSWORD: str = "afet360_dev_password"
    DATABASE_URL: str | None = None

    # AI Provider selection (default: local Ollama)
    AI_PROVIDER: Literal["ollama", "gemini"] = "ollama"

    # AI Provider configuration (Google Gemini - optional unless AI_PROVIDER=gemini)
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GEMINI_TIMEOUT_SECONDS: float = 30.0

    # AI Provider configuration (Local Ollama - default provider)
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "qwen3.5:2b-q4_K_M"
    OLLAMA_TIMEOUT_SECONDS: float = 30.0

    # CORS configuration
    CORS_ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Rate Limiting configuration (per process in-memory)
    API_RATE_LIMIT_REQUESTS: int = 120
    API_RATE_LIMIT_WINDOW_SECONDS: int = 60
    AI_RATE_LIMIT_REQUESTS: int = 5
    AI_RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Request Body Size Limit (64 KiB default)
    API_MAX_REQUEST_BODY_BYTES: int = 65536

    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        """Parse and sanitize CORS origins from comma-separated string or list."""
        if isinstance(value, str):
            value = [orig.strip() for orig in value.split(",") if orig.strip()]
        if isinstance(value, list):
            return [str(orig).strip() for orig in value if str(orig).strip()]
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator(
        "API_RATE_LIMIT_REQUESTS",
        "API_RATE_LIMIT_WINDOW_SECONDS",
        "AI_RATE_LIMIT_REQUESTS",
        "AI_RATE_LIMIT_WINDOW_SECONDS",
        "API_MAX_REQUEST_BODY_BYTES",
    )
    @classmethod
    def validate_positive_integer(cls, value: int) -> int:
        """Ensure rate limit and size limit values are strictly positive integers."""
        if value <= 0:
            raise ValueError(
                "Rate limit and request body size settings must be greater than 0."
            )
        return value

    @field_validator("AI_PROVIDER", mode="before")
    @classmethod
    def validate_ai_provider(cls, value: object) -> str:
        """Ensure AI provider is strictly 'ollama' or 'gemini'."""
        if not isinstance(value, str):
            raise ValueError("AI_PROVIDER must be a string.")
        clean_val = value.strip().lower()
        if clean_val not in ("ollama", "gemini"):
            raise ValueError(
                f"Unsupported AI_PROVIDER '{value}'. "
                "Supported providers are: 'ollama', 'gemini'."
            )
        return clean_val

    @field_validator("OLLAMA_BASE_URL", mode="before")
    @classmethod
    def validate_ollama_base_url(cls, value: object) -> str:
        """Ensure Ollama base URL is non-empty and does not bind to 0.0.0.0."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("OLLAMA_BASE_URL must not be empty.")
        clean_url = value.strip().rstrip("/")
        if "0.0.0.0" in clean_url:
            raise ValueError(
                "OLLAMA_BASE_URL must not use 0.0.0.0 as host. "
                "Use 127.0.0.1 or localhost."
            )
        return clean_url

    @field_validator("OLLAMA_TIMEOUT_SECONDS")
    @classmethod
    def validate_ollama_timeout(cls, value: float) -> float:
        """Ensure Ollama timeout is strictly positive."""
        if value <= 0:
            raise ValueError("OLLAMA_TIMEOUT_SECONDS must be greater than 0.")
        return value

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Derive the canonical SQLAlchemy database connection URI."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
