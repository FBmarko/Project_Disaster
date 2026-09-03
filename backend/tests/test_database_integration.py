import socket

import pytest
from sqlalchemy import text

from app.core.config import settings
from app.db.readiness import check_database_readiness
from app.db.session import SessionLocal, engine


def is_postgres_available(
    host: str = settings.POSTGRES_HOST,
    port: int = settings.POSTGRES_PORT,
    timeout: float = 0.5,
) -> bool:
    """Fast check to verify if the PostgreSQL port is reachable."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, TimeoutError):
        return False


@pytest.mark.integration
@pytest.mark.skipif(
    not is_postgres_available(),
    reason="PostgreSQL/PostGIS database is not reachable",
)
def test_real_postgres_connection() -> None:
    """Verify live connection to PostgreSQL."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1


@pytest.mark.integration
@pytest.mark.skipif(
    not is_postgres_available(),
    reason="PostgreSQL/PostGIS database is not reachable",
)
def test_postgis_extension_available() -> None:
    """Verify live PostGIS extension is installed and reports version."""
    with SessionLocal() as session:
        readiness = check_database_readiness(session)
        assert readiness["database"] == "connected"
        assert readiness["postgis"] == "available"
        assert readiness["postgis_version"] != "unknown"
