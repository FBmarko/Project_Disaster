import pytest

from app.core.config import Settings


def test_default_database_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in [
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "DATABASE_URL",
    ]:
        monkeypatch.delenv(var, raising=False)
    settings = Settings(_env_file=None)
    assert settings.POSTGRES_HOST == "localhost"
    assert settings.POSTGRES_PORT == 5432
    assert settings.POSTGRES_DB == "afet360"
    assert settings.POSTGRES_USER == "afet360"
    assert settings.POSTGRES_PASSWORD == "afet360_dev_password"
    assert (
        settings.SQLALCHEMY_DATABASE_URI
        == "postgresql+psycopg://afet360:afet360_dev_password@localhost:5432/afet360"
    )


def test_custom_database_url_override() -> None:
    custom_url = "postgresql+psycopg://custom_user:custom_pass@dbhost:5433/custom_db"
    settings = Settings(DATABASE_URL=custom_url)
    assert settings.SQLALCHEMY_DATABASE_URI == custom_url
