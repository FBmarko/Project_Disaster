"""Integration tests for OSM emergency assembly area persistence and idempotency."""

import json
import socket
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import engine
from app.models.assembly_area_dataset import AssemblyAreaDataset
from app.services.assembly_import import AssemblyImportService


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


def create_synthetic_valid_snapshot(tmp_path: Path) -> Path:
    """Create a minimal valid snapshot with 2 points and 1 polygon way."""
    payload = {
        "version": 0.6,
        "generator": "Overpass API 0.7.62.11 87bfad18",
        "osm3s": {
            "timestamp_osm_base": "2026-09-04T08:48:11Z",
            "timestamp_areas_base": "2026-09-03T10:22:36Z",
        },
        "elements": [
            {
                "type": "node",
                "id": 9001,
                "lat": 41.01,
                "lon": 28.97,
                "tags": {
                    "emergency": "assembly_point",
                    "name": "Nokta 1 Parkı",
                    "ref": "34-001",
                    "operator": "AFAD",
                    "leisure": "park",
                },
            },
            {
                "type": "node",
                "id": 9002,
                "lat": 41.02,
                "lon": 28.98,
                "tags": {
                    "emergency": "assembly_point",
                    "name": "Nokta 2 Alanı",
                },
            },
            {
                "type": "way",
                "id": 9003,
                "geometry": [
                    {"lat": 41.03, "lon": 28.95},
                    {"lat": 41.03, "lon": 28.96},
                    {"lat": 41.04, "lon": 28.96},
                    {"lat": 41.04, "lon": 28.95},
                    {"lat": 41.03, "lon": 28.95},
                ],
                "tags": {
                    "emergency": "assembly_point",
                    "name": "Nokta 3 Büyük Park",
                    "operator": "İBB",
                },
            },
        ],
    }
    file_path = tmp_path / "synthetic_snapshot.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    return file_path


def test_assembly_import_first_run_inserts_and_second_is_idempotent(
    tmp_path: Path, isolated_session: Session
) -> None:
    """First run inserts records; second run on same snapshot is 100% unchanged."""
    snapshot_path = create_synthetic_valid_snapshot(tmp_path)
    service = AssemblyImportService(isolated_session)

    # First run
    stats1 = service.import_osm_snapshot(
        snapshot_path, strict_checksum=False, strict_contract=False
    )
    assert stats1.inserted == 3
    assert stats1.unchanged == 0
    assert stats1.was_dataset_created is True
    assert stats1.polygon_count == 1
    assert stats1.node_count == 2

    # Verify database state
    dataset = isolated_session.get(AssemblyAreaDataset, stats1.dataset_id)
    assert dataset is not None
    assert dataset.source == "OpenStreetMap"
    assert dataset.license == "ODbL 1.0"
    assert dataset.attribution == "© OpenStreetMap contributors"

    areas_count = service.repository.count_areas_for_dataset(stats1.dataset_id)
    assert areas_count == 3

    # Verify polygon PostGIS validity
    total, valid, simple = service.repository.validate_polygons_valid_and_simple(
        stats1.dataset_id
    )
    assert total == 1
    assert valid == 1
    assert simple == 1

    # Capture created_at and updated_at timestamps after first import
    rows_before = isolated_session.execute(
        text(
            "SELECT source_feature_id, created_at, updated_at "
            "FROM assembly_areas WHERE dataset_id = :d"
        ),
        {"d": stats1.dataset_id},
    ).fetchall()
    timestamps_before = {r[0]: (r[1], r[2]) for r in rows_before}
    assert len(timestamps_before) == 3
    for _feature_id, (created, updated) in timestamps_before.items():
        assert created is not None
        assert updated is not None
        assert updated >= created

    # Second run: identical snapshot
    stats2 = service.import_osm_snapshot(
        snapshot_path, strict_checksum=False, strict_contract=False
    )
    assert stats2.dataset_id == stats1.dataset_id
    assert stats2.was_dataset_created is False
    assert stats2.inserted == 0
    assert stats2.unchanged == 3
    assert service.repository.count_areas_for_dataset(stats1.dataset_id) == 3

    # Verify updated_at timestamps are strictly unchanged (read-only verification)
    rows_after = isolated_session.execute(
        text(
            "SELECT source_feature_id, created_at, updated_at "
            "FROM assembly_areas WHERE dataset_id = :d"
        ),
        {"d": stats1.dataset_id},
    ).fetchall()
    timestamps_after = {r[0]: (r[1], r[2]) for r in rows_after}
    for feature_id in timestamps_before:
        assert timestamps_after[feature_id] == timestamps_before[feature_id]


def test_assembly_import_feature_attribute_drift_fails_closed(
    tmp_path: Path, isolated_session: Session
) -> None:
    """If an existing database record is altered, re-importing must fail closed."""
    snapshot_path = create_synthetic_valid_snapshot(tmp_path)
    service = AssemblyImportService(isolated_session)

    # Initial import
    stats = service.import_osm_snapshot(
        snapshot_path, strict_checksum=False, strict_contract=False
    )

    # Corrupt a record's name in the database
    isolated_session.execute(
        text("""
            UPDATE assembly_areas
            SET name = 'Corrupted Name'
            WHERE dataset_id = :d AND source_feature_id = 'node/9001'
        """),
        {"d": stats.dataset_id},
    )

    # Re-import should detect attribute drift
    with pytest.raises(ValueError, match="Attribute drift in node/9001"):
        service.import_osm_snapshot(
            snapshot_path, strict_checksum=False, strict_contract=False
        )


def test_assembly_import_feature_spatial_drift_fails_closed(
    tmp_path: Path, isolated_session: Session
) -> None:
    """If an existing database geometry is shifted, re-importing must fail closed."""
    snapshot_path = create_synthetic_valid_snapshot(tmp_path)
    service = AssemblyImportService(isolated_session)

    stats = service.import_osm_snapshot(
        snapshot_path, strict_checksum=False, strict_contract=False
    )

    # Alter geometry in DB
    isolated_session.execute(
        text("""
            UPDATE assembly_areas
            SET geometry = ST_SetSRID(ST_MakePoint(29.0, 41.5), 4326)
            WHERE dataset_id = :d AND source_feature_id = 'node/9002'
        """),
        {"d": stats.dataset_id},
    )

    # Re-import should detect spatial drift
    with pytest.raises(
        ValueError, match="Spatial drift detected for feature node/9002"
    ):
        service.import_osm_snapshot(
            snapshot_path, strict_checksum=False, strict_contract=False
        )


def test_assembly_dataset_cascade_delete(
    tmp_path: Path, isolated_session: Session
) -> None:
    """Deleting an assembly dataset must cascade delete all associated areas."""
    snapshot_path = create_synthetic_valid_snapshot(tmp_path)
    service = AssemblyImportService(isolated_session)

    stats = service.import_osm_snapshot(
        snapshot_path, strict_checksum=False, strict_contract=False
    )
    assert service.repository.count_areas_for_dataset(stats.dataset_id) == 3

    dataset = isolated_session.get(AssemblyAreaDataset, stats.dataset_id)
    isolated_session.delete(dataset)
    isolated_session.flush()

    # Verify features are cascaded
    count_remaining = isolated_session.execute(
        text("SELECT count(*) FROM assembly_areas WHERE dataset_id = :d"),
        {"d": stats.dataset_id},
    ).scalar()
    assert count_remaining == 0
