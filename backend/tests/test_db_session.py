from unittest.mock import MagicMock, patch

from app.db.base import Base
from app.db.dependencies import get_db
from app.db.readiness import check_database_readiness


def test_base_metadata_initialized() -> None:
    """Verify that SQLAlchemy Declarative Base is initialized without domain models."""
    assert hasattr(Base, "metadata")
    # In Phase 2, no application/domain tables should exist yet
    assert len(Base.metadata.tables) == 0


def test_get_db_session_lifecycle() -> None:
    """Verify that get_db dependency yields a session and closes it cleanly."""
    mock_session = MagicMock()
    with patch("app.db.dependencies.SessionLocal", return_value=mock_session):
        session_generator = get_db()
        session = next(session_generator)
        assert session is mock_session
        mock_session.close.assert_not_called()

        # Exhaust generator to trigger finally block
        try:
            next(session_generator)
        except StopIteration:
            pass

        mock_session.close.assert_called_once()


def test_check_database_readiness_unit() -> None:
    """Verify database readiness helper logic using a mocked session."""
    mock_session = MagicMock()
    mock_session.execute.return_value.scalar.side_effect = [
        1,
        "3.4 USE_GEOS=1 USE_PROJ=1",
    ]

    result = check_database_readiness(mock_session)
    assert result["database"] == "connected"
    assert result["postgis"] == "available"
    assert result["postgis_version"] == "3.4 USE_GEOS=1 USE_PROJ=1"
