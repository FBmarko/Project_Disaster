import importlib.util
import socket
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import engine
from app.integrations.gem.hazard_constants import (
    GEM_ATTRIBUTION,
    GEM_CONCEPT_DOI,
    GEM_HAZARD_METRIC,
    GEM_LICENSE,
    GEM_MODEL_NAME,
    GEM_REFERENCE_GROUND,
    GEM_REFERENCE_VS30_MPS,
    GEM_RETURN_PERIOD_YEARS,
    GEM_SOURCE_NAME,
    GEM_SOURCE_VERSION,
    GEM_TIME_HORIZON_YEARS,
    GEM_UNIT,
    GEM_VERSION_DOI,
    GEM_ZIP_FILENAME,
    GEM_ZIP_MD5,
    GEM_ZIP_SIZE_BYTES,
    TURKEY_CONTEXT_SCOPE,
)
from app.repositories.earthquake_hazard import EarthquakeHazardRepository
from app.services.hazard_import import HazardImportService
from tests.test_hazard_adapter import create_synthetic_gpkg


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


def test_alembic_migration_metadata_and_version_column_length() -> None:
    """Verify revision ID length <= 32 and alembic_version column is VARCHAR(32)."""
    # 1. Load migration 0004 file directly to inspect revision ID and parent
    mig_path = (
        Path(__file__).parent.parent
        / "alembic"
        / "versions"
        / "0004_create_hazard_tables.py"
    )
    assert mig_path.is_file(), f"Migration file {mig_path} must exist"

    spec = importlib.util.spec_from_file_location("mig_0004", mig_path)
    assert spec is not None and spec.loader is not None
    mig_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig_mod)

    assert len(mig_mod.revision) <= 32
    assert mig_mod.revision == "0004_create_hazard_tables"
    assert mig_mod.down_revision == "0003_create_earthquake_events"

    # 2. Query PostgreSQL information_schema to verify standard VARCHAR(32)
    with engine.connect() as conn:
        res = conn.execute(
            text(
                "SELECT character_maximum_length "
                "FROM information_schema.columns "
                "WHERE table_name = 'alembic_version' AND column_name = 'version_num';"
            )
        ).scalar()
    assert res == 32, f"alembic_version.version_num must be VARCHAR(32), got {res}"


def test_hazard_tables_and_gist_index_exist() -> None:
    """Verify hazard tables, constraints, and GiST index exist in PostgreSQL."""
    inspector = inspect(engine)
    tables = inspector.get_table_names(schema="public")
    assert "hazard_datasets" in tables
    assert "earthquake_hazard_points" in tables

    ds_cols = {c["name"] for c in inspector.get_columns("hazard_datasets")}
    assert {
        "id",
        "source",
        "source_version",
        "model_name",
        "hazard_metric",
        "version_doi",
    }.issubset(ds_cols)

    pt_cols = {c["name"] for c in inspector.get_columns("earthquake_hazard_points")}
    assert {"id", "dataset_id", "longitude", "latitude", "pga_g", "geometry"}.issubset(
        pt_cols
    )

    indexes = inspector.get_indexes("earthquake_hazard_points")
    gist_indexes = [
        idx
        for idx in indexes
        if idx.get("dialect_options", {}).get("postgresql_using") == "gist"
    ]
    assert len(gist_indexes) >= 1
    assert any(
        idx["name"] == "idx_earthquake_hazard_points_geometry" for idx in gist_indexes
    )


def test_hazard_import_service_idempotency(
    isolated_session: Session, tmp_path: Path
) -> None:
    """Verify synthetic hazard import is idempotent and handles reruns cleanly."""
    gpkg_file = tmp_path / "hazard_sample.gpkg"
    points = [
        (101, 30.0, 38.0, 0.12),
        (102, 32.0, 39.0, 0.22),
        (103, 34.0, 40.0, 0.32),
    ]
    create_synthetic_gpkg(gpkg_file, points)

    service = HazardImportService(isolated_session)

    # First import run: 3 points inserted
    stats_1 = service.import_gem_hazard_data(
        gpkg_path=gpkg_file,
        check_full_size=False,
        batch_size=2,
    )
    assert stats_1.source_rows == 3
    assert stats_1.inserted == 3
    assert stats_1.unchanged == 0
    assert stats_1.conflicts == 0

    # Second run with identical data: 3 unchanged, 0 inserted
    stats_2 = service.import_gem_hazard_data(
        gpkg_path=gpkg_file,
        check_full_size=False,
        batch_size=2,
    )
    assert stats_2.source_rows == 3
    assert stats_2.inserted == 0
    assert stats_2.unchanged == 3
    assert stats_2.conflicts == 0


def test_hazard_import_partial_rerun(isolated_session: Session, tmp_path: Path) -> None:
    """Verify partial existing points can be complemented without duplication."""
    gpkg_part1 = tmp_path / "part1.gpkg"
    create_synthetic_gpkg(
        gpkg_part1,
        [
            (201, 31.0, 38.0, 0.15),
            (202, 33.0, 39.0, 0.25),
        ],
    )

    service = HazardImportService(isolated_session)
    stats_1 = service.import_gem_hazard_data(
        gpkg_path=gpkg_part1,
        check_full_size=False,
    )
    assert stats_1.inserted == 2

    gpkg_full = tmp_path / "full.gpkg"
    create_synthetic_gpkg(
        gpkg_full,
        [
            (201, 31.0, 38.0, 0.15),
            (202, 33.0, 39.0, 0.25),
            (203, 35.0, 40.0, 0.35),
            (204, 37.0, 41.0, 0.45),
        ],
    )

    stats_2 = service.import_gem_hazard_data(
        gpkg_path=gpkg_full,
        check_full_size=False,
    )
    assert stats_2.source_rows == 4
    assert stats_2.inserted == 2
    assert stats_2.unchanged == 2
    assert stats_2.conflicts == 0


def test_hazard_import_point_conflict_material_diff(
    isolated_session: Session, tmp_path: Path
) -> None:
    """Verify materially different PGA raises ValueError."""
    gpkg_file1 = tmp_path / "base.gpkg"
    create_synthetic_gpkg(gpkg_file1, [(301, 32.0, 39.0, 0.20)])

    service = HazardImportService(isolated_session)
    service.import_gem_hazard_data(gpkg_file1, check_full_size=False)

    gpkg_file2 = tmp_path / "conflict.gpkg"
    create_synthetic_gpkg(gpkg_file2, [(301, 32.0, 39.0, 0.99)])

    with pytest.raises(ValueError, match="Conflict at"):
        service.import_gem_hazard_data(gpkg_file2, check_full_size=False)


def test_hazard_import_point_conflict_tiny_pga_diff(
    isolated_session: Session, tmp_path: Path
) -> None:
    """Verify tiny PGA difference (5e-5) raises ValueError instead of being ignored."""
    gpkg_file1 = tmp_path / "base_tiny.gpkg"
    create_synthetic_gpkg(gpkg_file1, [(302, 32.5, 39.5, 0.20000)])

    service = HazardImportService(isolated_session)
    service.import_gem_hazard_data(gpkg_file1, check_full_size=False)

    # 5e-5 difference: 0.20005 g vs 0.20000 g
    gpkg_file2 = tmp_path / "conflict_tiny.gpkg"
    create_synthetic_gpkg(gpkg_file2, [(302, 32.5, 39.5, 0.20005)])

    with pytest.raises(ValueError, match="Conflict at"):
        service.import_gem_hazard_data(gpkg_file2, check_full_size=False)


def test_hazard_import_point_conflict_different_source_record_id(
    isolated_session: Session, tmp_path: Path
) -> None:
    """Verify different source_record_id for same coordinate raises conflict."""
    gpkg_file1 = tmp_path / "fid1.gpkg"
    create_synthetic_gpkg(gpkg_file1, [(501, 33.0, 39.0, 0.25)])

    service = HazardImportService(isolated_session)
    service.import_gem_hazard_data(gpkg_file1, check_full_size=False)

    # Different FID: 999 instead of 501
    gpkg_file2 = tmp_path / "fid2.gpkg"
    create_synthetic_gpkg(gpkg_file2, [(999, 33.0, 39.0, 0.25)])

    with pytest.raises(ValueError, match="Conflict at"):
        service.import_gem_hazard_data(gpkg_file2, check_full_size=False)


@pytest.mark.parametrize(
    ("modified_field", "modified_value"),
    [
        ("source_checksum_value", "ffffffffffffffffffffffffffffffff"),
        ("reference_vs30_mps", 760.0),
        ("version_doi", "10.5281/zenodo.99999999"),
        ("scope_max_longitude", 45.0),
    ],
)
def test_dataset_provenance_conflict_rejection(
    isolated_session: Session, modified_field: str, modified_value: object
) -> None:
    """Verify existing dataset with conflicting immutable metadata is rejected."""
    base_payload = {
        "source": GEM_SOURCE_NAME,
        "source_version": GEM_SOURCE_VERSION,
        "model_name": GEM_MODEL_NAME,
        "hazard_metric": GEM_HAZARD_METRIC,
        "unit": GEM_UNIT,
        "return_period_years": GEM_RETURN_PERIOD_YEARS,
        "exceedance_probability": 0.10,
        "time_horizon_years": GEM_TIME_HORIZON_YEARS,
        "reference_vs30_mps": GEM_REFERENCE_VS30_MPS,
        "reference_ground": GEM_REFERENCE_GROUND,
        "version_doi": GEM_VERSION_DOI,
        "concept_doi": GEM_CONCEPT_DOI,
        "license": GEM_LICENSE,
        "attribution": GEM_ATTRIBUTION,
        "source_artifact": GEM_ZIP_FILENAME,
        "source_artifact_size_bytes": GEM_ZIP_SIZE_BYTES,
        "source_checksum_algorithm": "md5",
        "source_checksum_value": GEM_ZIP_MD5,
        "ingest_scope": TURKEY_CONTEXT_SCOPE,
        "scope_min_longitude": 24.0,
        "scope_min_latitude": 34.0,
        "scope_max_longitude": 46.0,
        "scope_max_latitude": 44.0,
    }

    repo = EarthquakeHazardRepository(isolated_session)
    # 1. First call creates or gets the record
    repo.get_or_create_dataset(base_payload)

    # 2. Conflicting call with modified field
    conflicting_payload = dict(base_payload)
    conflicting_payload[modified_field] = modified_value

    with pytest.raises(ValueError, match="Provenance"):
        repo.get_or_create_dataset(conflicting_payload)


def test_postgis_point_geometry_consistency(
    isolated_session: Session, tmp_path: Path
) -> None:
    """Verify ST_X and ST_Y match longitude and latitude exactly."""
    gpkg_file = tmp_path / "geom_test.gpkg"
    create_synthetic_gpkg(
        gpkg_file,
        [
            (401, 28.5, 37.5, 0.18),
            (402, 38.5, 41.5, 0.28),
        ],
    )
    service = HazardImportService(isolated_session)
    stats = service.import_gem_hazard_data(
        gpkg_path=gpkg_file,
        check_full_size=False,
    )

    rows = (
        isolated_session.execute(
            text(
                "SELECT ST_X(geometry) as x, ST_Y(geometry) as y, "
                "longitude, latitude, ST_SRID(geometry) as srid, "
                "ST_GeometryType(geometry) as geom_type "
                "FROM earthquake_hazard_points "
                "WHERE dataset_id = :ds_id AND source_record_id IN (401, 402)"
            ),
            {"ds_id": stats.dataset_id},
        )
        .mappings()
        .all()
    )

    assert len(rows) == 2
    for r in rows:
        assert abs(r["x"] - r["longitude"]) < 1e-6
        assert abs(r["y"] - r["latitude"]) < 1e-6
        assert r["srid"] == 4326
        assert r["geom_type"] == "ST_Point"


def test_integration_suite_conserves_persistent_database() -> None:
    """Verify that test suite execution leaves the persistent database counts intact."""
    with engine.connect() as conn:
        ds_count = conn.execute(text("SELECT count(*) FROM hazard_datasets;")).scalar()
        pt_count = conn.execute(
            text("SELECT count(*) FROM earthquake_hazard_points;")
        ).scalar()
        faults = conn.execute(text("SELECT count(*) FROM fault_segments;")).scalar()
        quakes = conn.execute(text("SELECT count(*) FROM earthquake_events;")).scalar()

    assert ds_count == 1
    assert pt_count == 54291
    assert faults == 722
    assert quakes == 84
