from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def check_database_readiness(session: Session) -> dict[str, Any]:
    """Verify database connectivity, query execution, and PostGIS extension presence.

    Returns a status dictionary without exposing sensitive infrastructure details.
    """
    session.execute(text("SELECT 1")).scalar()
    postgis_version = session.execute(text("SELECT PostGIS_Version();")).scalar()

    return {
        "database": "connected",
        "postgis": "available",
        "postgis_version": str(postgis_version) if postgis_version else "unknown",
    }
