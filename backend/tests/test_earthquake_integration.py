import json
import socket
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import engine
from app.models.earthquake_event import EarthquakeEvent
from app.services.earthquake_sync import EarthquakeSyncService

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "afad_events_sample.json"


def is_postgres_available() -> bool:
    """Fast socket-level connectivity check for PostgreSQL."""
    try:
        with socket.create_connection(
            (settings.POSTGRES_HOST, settings.POSTGRES_PORT), timeout=0.5
        ):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def skip_if_database_unavailable() -> None:
    if not is_postgres_available():
        pytest.skip("PostgreSQL/PostGIS container is not reachable.")


@pytest.fixture
def isolated_session() -> Generator[Session, None, None]:
    """Provide a database session within an outer transaction that rolls back."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def test_earthquake_events_table_and_indexes_exist() -> None:
    """Verify earthquake_events table, columns, and indexes exist in PostgreSQL."""
    inspector = inspect(engine)
    tables = inspector.get_table_names(schema="public")
    assert "earthquake_events" in tables

    columns = {c["name"] for c in inspector.get_columns("earthquake_events")}
    expected = {
        "id",
        "source",
        "source_event_id",
        "occurred_at",
        "depth_km",
        "magnitude",
        "magnitude_type",
        "location_name",
        "country",
        "province",
        "district",
        "neighborhood",
        "geometry",
        "is_updated",
        "last_update_at",
        "source_properties",
        "fetched_at",
        "created_at",
        "updated_at",
    }
    assert expected.issubset(columns)

    indexes = {idx["name"] for idx in inspector.get_indexes("earthquake_events")}
    assert "idx_earthquake_events_geometry" in indexes
    assert "idx_earthquake_events_occurred_at" in indexes
    assert "idx_earthquake_events_magnitude" in indexes
    assert "idx_earthquake_events_mag_occurred" in indexes
    assert "idx_earthquake_events_source_event_id" in indexes

    unique_constraints = {
        uc["name"]
        for uc in inspector.get_unique_constraints("earthquake_events")
        if uc["name"]
    }
    assert "uq_earthquake_events_source_event_id" in unique_constraints


def test_geometry_columns_point_metadata() -> None:
    """Verify PostGIS geometry_columns metadata declares POINT EPSG:4326."""
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT f_geometry_column, coord_dimension, srid, type "
                "FROM geometry_columns WHERE f_table_name = 'earthquake_events';"
            )
        ).first()

    assert result is not None
    assert result[0] == "geometry"
    assert result[1] == 2
    assert result[2] == 4326
    assert result[3].upper() == "POINT"


def test_earthquake_sync_service_idempotency(isolated_session: Session) -> None:
    """Verify that importing the same AFAD events twice is completely idempotent."""
    with open(FIXTURES_PATH, encoding="utf-8") as f:
        sample_data = json.load(f)

    service = EarthquakeSyncService(isolated_session)

    # First synchronization
    stats1 = service.sync_events(sample_data)
    assert stats1.total_received == 5
    assert stats1.inserted + stats1.updated + stats1.unchanged == 5
    assert stats1.failed == 0
    count_after_first = isolated_session.query(EarthquakeEvent).count()

    # Second synchronization with identical data: 100% must be unchanged
    stats2 = service.sync_events(sample_data)
    assert stats2.total_received == 5
    assert stats2.inserted == 0
    assert stats2.updated == 0
    assert stats2.unchanged == 5
    assert stats2.failed == 0

    count_after_second = isolated_session.query(EarthquakeEvent).count()
    assert count_after_second == count_after_first


def test_earthquake_update_on_revision(isolated_session: Session) -> None:
    """Verify that when AFAD updates magnitude or location, the row is updated."""
    with open(FIXTURES_PATH, encoding="utf-8") as f:
        sample_data = json.load(f)

    service = EarthquakeSyncService(isolated_session)
    service.sync_events(sample_data)
    count_before = isolated_session.query(EarthquakeEvent).count()

    # Modify the first event (Pazarcık)
    revised = dict(sample_data[0])
    revised["magnitude"] = "7.8"  # Upgraded magnitude
    revised["depth"] = "10.0"
    revised["isEventUpdate"] = True
    revised["lastUpdateDate"] = "2023-02-07T00:00:00"

    stats = service.sync_events([revised])
    assert stats.inserted == 0
    assert stats.updated == 1
    assert stats.unchanged == 0

    # Total rows must remain unchanged
    assert isolated_session.query(EarthquakeEvent).count() == count_before

    # Check updated record
    event = (
        isolated_session.query(EarthquakeEvent)
        .filter_by(source_event_id="543428")
        .first()
    )
    assert event is not None
    assert event.magnitude == 7.8
    assert event.depth_km == 10.0


def test_postgis_point_spatial_query(isolated_session: Session) -> None:
    """Verify spatial queries, validity, and geometry type for imported points."""
    with open(FIXTURES_PATH, encoding="utf-8") as f:
        sample_data = json.load(f)

    service = EarthquakeSyncService(isolated_session)
    service.sync_events(sample_data)

    fixture_ids = [e["eventID"] for e in sample_data]

    # Check PostGIS spatial integrity functions on fixture records
    stmt = select(
        func.ST_IsValid(EarthquakeEvent.geometry),
        func.ST_IsEmpty(EarthquakeEvent.geometry),
        func.ST_GeometryType(EarthquakeEvent.geometry),
        func.ST_SRID(EarthquakeEvent.geometry),
    ).where(EarthquakeEvent.source_event_id.in_(fixture_ids))

    validity_rows = isolated_session.execute(stmt).all()

    assert len(validity_rows) == 5
    for is_valid, is_empty, geom_type, srid in validity_rows:
        assert is_valid is True
        assert is_empty is False
        assert geom_type == "ST_Point"
        assert srid == 4326

    # Geodesic radius query around Pazarcık (37.03996, 37.27728) within 50 km
    nearby_pazarcik = isolated_session.execute(
        text(
            "SELECT source_event_id, magnitude "
            "FROM earthquake_events "
            "WHERE ST_DWithin("
            "  geometry::geography, "
            "  ST_SetSRID(ST_MakePoint(37.03996, 37.27728), 4326)::geography, "
            "  50000.0"
            ");"
        )
    ).all()

    # Must contain Pazarcık event
    event_ids = [r[0] for r in nearby_pazarcik]
    assert "543428" in event_ids


def test_integration_suite_leaves_database_clean(isolated_session: Session) -> None:
    """Verify isolated session operates without side effects."""
    initial_count = isolated_session.query(EarthquakeEvent).count()
    service = EarthquakeSyncService(isolated_session)
    service.sync_events(
        [
            {
                "eventID": "TEMP_TEST_1",
                "date": "2024-01-01T00:00:00",
                "latitude": "38.0",
                "longitude": "27.0",
                "depth": "10.0",
                "magnitude": "5.0",
                "type": "MW",
            }
        ]
    )
    assert isolated_session.query(EarthquakeEvent).count() == initial_count + 1


def test_earthquake_update_without_last_update_date(
    isolated_session: Session,
) -> None:
    """Verify updates are detected via magnitude/depth without lastUpdateDate."""
    service = EarthquakeSyncService(isolated_session)
    event_payload = {
        "eventID": "TEMP_UPDATE_TEST",
        "date": "2024-01-01T00:00:00",
        "latitude": "38.0",
        "longitude": "27.0",
        "depth": "10.0",
        "magnitude": "5.0",
        "type": "MW",
        "location": "Initial Location",
        "isEventUpdate": False,
        "lastUpdateDate": None,
    }

    # Initial sync
    stats1 = service.sync_events([event_payload])
    assert stats1.inserted == 1

    # Upstream revision without lastUpdateDate: revised magnitude and depth
    revised_payload = dict(event_payload)
    revised_payload["magnitude"] = "5.3"
    revised_payload["depth"] = "12.5"
    revised_payload["location"] = "Revised Location"
    revised_payload["isEventUpdate"] = True

    stats2 = service.sync_events([revised_payload])
    assert stats2.inserted == 0
    assert stats2.updated == 1
    assert stats2.unchanged == 0

    record = (
        isolated_session.query(EarthquakeEvent)
        .filter_by(source_event_id="TEMP_UPDATE_TEST")
        .first()
    )
    assert record is not None
    assert record.magnitude == 5.3
    assert record.depth_km == 12.5
    assert record.location_name == "Revised Location"
    assert record.is_updated is True


def test_fetched_at_leaves_identical_event_unchanged(
    isolated_session: Session,
) -> None:
    """Verify that re-syncing identical events leaves them unchanged."""
    service = EarthquakeSyncService(isolated_session)
    event_payload = {
        "eventID": "TEMP_IDEMPOTENCY_TEST",
        "date": "2024-01-01T00:00:00",
        "latitude": "38.0",
        "longitude": "27.0",
        "depth": "10.0",
        "magnitude": "5.0",
        "type": "MW",
    }

    # Initial insert
    stats1 = service.sync_events([event_payload])
    assert stats1.inserted == 1

    # Re-sync exact identical event payload
    stats2 = service.sync_events([event_payload])
    assert stats2.inserted == 0
    assert stats2.updated == 0
    assert stats2.unchanged == 1
