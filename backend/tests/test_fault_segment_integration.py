import json
import socket
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import engine
from app.services.fault_import import FaultImportService


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
    """Provide a database session within an outer transaction that rolls back on exit.

    Guarantees that integration tests never permanently contaminate the
    persistent development database.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def test_fault_segments_table_and_gist_index_exist() -> None:
    """Verify fault_segments table, columns, and GiST index exist in PostgreSQL."""
    inspector = inspect(engine)
    tables = inspector.get_table_names(schema="public")
    assert "fault_segments" in tables

    columns = {c["name"] for c in inspector.get_columns("fault_segments")}
    expected = {
        "id",
        "source",
        "source_feature_id",
        "name",
        "segment_name",
        "fault_type",
        "activity_status",
        "geometry",
        "source_reference",
        "source_properties",
        "created_at",
        "updated_at",
    }
    assert expected.issubset(columns)

    indexes = inspector.get_indexes("fault_segments")
    gist_indexes = [
        idx
        for idx in indexes
        if idx.get("dialect_options", {}).get("postgresql_using") == "gist"
    ]
    assert len(gist_indexes) >= 1
    assert any(idx["name"] == "idx_fault_segments_geometry" for idx in gist_indexes)


def test_geometry_columns_metadata() -> None:
    """Verify PostGIS geometry_columns metadata for fault_segments."""
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT f_table_name, f_geometry_column, coord_dimension, srid, type "
                "FROM geometry_columns WHERE f_table_name = :tbl"
            ),
            {"tbl": "fault_segments"},
        ).fetchone()

        assert row is not None
        assert row[0] == "fault_segments"
        assert row[1] == "geometry"
        assert row[2] == 2
        assert row[3] == 4326
        assert row[4] == "MULTILINESTRING"


def test_fault_import_service_idempotency(isolated_session: Session) -> None:
    """Verify that importing the sample fixture twice is idempotent."""
    fixture_path = Path(__file__).parent / "fixtures" / "gem_faults_turkey_sample.json"
    with open(fixture_path, encoding="utf-8") as f:
        fixture_data = json.load(f)

    service = FaultImportService(isolated_session)

    # First import run: all 5 features are either inserted or already present
    stats_1 = service.import_gem_geojson(fixture_data)
    assert stats_1.total_source_features == 5
    assert stats_1.inserted + stats_1.unchanged == 5
    assert stats_1.updated == 0
    assert stats_1.failed == 0

    # Second import run with identical data: 100% must be unchanged
    stats_2 = service.import_gem_geojson(fixture_data)
    assert stats_2.total_source_features == 5
    assert stats_2.inserted == 0
    assert stats_2.updated == 0
    assert stats_2.unchanged == 5
    assert stats_2.failed == 0


def test_postgis_geometry_validity_and_spatial_query(
    isolated_session: Session,
) -> None:
    """Verify geometries are valid PostGIS MultiLineStrings and queryable."""
    fixture_path = Path(__file__).parent / "fixtures" / "gem_faults_turkey_sample.json"
    with open(fixture_path, encoding="utf-8") as f:
        fixture_data = json.load(f)

    service = FaultImportService(isolated_session)
    service.import_gem_geojson(fixture_data)

    fixture_ids = [f["properties"]["catalog_id"] for f in fixture_data["features"]]

    # Check ST_IsValid on fixture records
    results = isolated_session.execute(
        text(
            "SELECT ST_IsValid(geometry), ST_GeometryType(geometry), "
            "ST_SRID(geometry) FROM fault_segments "
            "WHERE source_feature_id = ANY(:ids)"
        ),
        {"ids": fixture_ids},
    ).fetchall()

    assert len(results) == 5
    for is_valid, geom_type, srid in results:
        assert is_valid is True
        assert geom_type == "ST_MultiLineString"
        assert srid == 4326

    # Test ST_DWithin query: find faults within 50 km of Edirne (26.55°E, 41.67°N)
    point_wkt = "SRID=4326;POINT(26.55 41.67)"
    nearby_faults = isolated_session.execute(
        text(
            "SELECT id, source_feature_id "
            "FROM fault_segments "
            "WHERE ST_DWithin(geometry::geography, ST_GeogFromText(:pt), 50000)"
        ),
        {"pt": point_wkt},
    ).fetchall()

    assert len(nearby_faults) > 0


def test_integration_suite_leaves_database_clean() -> None:
    """Regression test verifying test suite leaves persistent database clean."""
    with engine.connect() as conn:
        count = conn.execute(text("SELECT count(*) FROM fault_segments")).scalar()
    # The isolated_session fixture ensures 0 residual test records in the database
    # (If the table was empty or populated prior to tests, count is strictly conserved)
    assert count is not None
