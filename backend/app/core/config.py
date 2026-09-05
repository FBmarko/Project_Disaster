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

    # AI Provider configuration (Google Gemini)
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GEMINI_TIMEOUT_SECONDS: float = 30.0

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
