"""Unit and integration tests for dataset provisioning and readiness inspection."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text

from app.db.session import SessionLocal
from app.scripts.provision_datasets import (
    format_status_text,
    inspect_dataset_readiness,
    run_provision_static,
    run_status,
)
from tests.test_database_integration import is_postgres_available

# =====================================================================
# Unit Tests (Mocked DB Session & Importer Delegates)
# =====================================================================


def test_inspect_readiness_empty_database() -> None:
    """Verify that an empty database is safely handled without errors."""
    mock_session = MagicMock()

    # Faults query count = 0
    # Faults valid = 0
    # Faults srid = 0
    # Faults sources = []
    # GSHM repo get_active_gem_dataset = None
    # Assembly repo get_current_osm_dataset = None
    # Earthquakes count = 0, time_bounds = (None, None), sources = []

    mock_execute = MagicMock()
    mock_session.execute.return_value = mock_execute
    mock_execute.scalar.return_value = 0
    mock_execute.scalars.return_value.all.return_value = []
    mock_execute.fetchone.return_value = (None, None)

    with (
        patch(
            "app.scripts.provision_datasets.EarthquakeHazardRepository"
        ) as mock_hazard_repo_cls,
        patch(
            "app.scripts.provision_datasets.AssemblyAreaRepository"
        ) as mock_assembly_repo_cls,
    ):
        mock_hazard_repo = mock_hazard_repo_cls.return_value
        mock_hazard_repo.get_active_gem_dataset.return_value = None

        mock_assembly_repo = mock_assembly_repo_cls.return_value
        mock_assembly_repo.get_current_osm_dataset.return_value = None

        report = inspect_dataset_readiness(mock_session)

    assert report["overall_ready"] is False
    assert report["all_static_ready"] is False

    faults = report["datasets"]["faults"]
    assert faults["ready"] is False
    assert faults["count"] == 0

    gshm = report["datasets"]["gshm_hazard"]
    assert gshm["ready"] is False
    assert gshm["points_count"] == 0
    assert gshm["dataset_id"] is None

    assembly = report["datasets"]["assembly_areas"]
    assert assembly["ready"] is False
    assert assembly["total_areas"] == 0
    assert assembly["dataset_id"] is None

    eq = report["datasets"]["earthquakes"]
    assert eq["ready"] is False
    assert eq["count"] == 0


def test_format_status_text() -> None:
    """Verify text formatting contains status badges and key metrics."""
    dummy_report = {
        "inspected_at": "2026-09-08T00:00:00Z",
        "overall_ready": True,
        "all_static_ready": True,
        "datasets": {
            "faults": {
                "dataset_type": "static",
                "ready": True,
                "count": 722,
                "valid_geometry_count": 722,
                "srid_4326_count": 722,
                "sources": ["GEM_GAF"],
            },
            "gshm_hazard": {
                "dataset_type": "static",
                "ready": True,
                "dataset_id": "test-uuid-1",
                "source": "GEM_GSHM",
                "source_version": "2026.1",
                "hazard_metric": "PGA",
                "unit": "g",
                "return_period_years": 475,
                "exceedance_probability": 0.1,
                "reference_vs30_mps": 800.0,
                "points_count": 54291,
                "min_pga_g": 0.02,
                "max_pga_g": 0.77,
            },
            "assembly_areas": {
                "dataset_type": "static",
                "ready": True,
                "dataset_id": "test-uuid-2",
                "source": "OpenStreetMap",
                "provider": "Overpass",
                "license": "ODbL 1.0",
                "total_areas": 678,
                "point_features": 650,
                "polygon_features": 28,
            },
            "earthquakes": {
                "dataset_type": "dynamic",
                "ready": True,
                "count": 784,
                "earliest_event": "2016-09-12T00:00:00Z",
                "latest_event": "2026-08-09T00:00:00Z",
                "sources": ["AFAD"],
                "note": "Dynamic rolling catalog.",
            },
        },
    }

    formatted = format_status_text(dummy_report)
    assert "AFET360 DATASET READINESS STATUS" in formatted
    assert "Overall Readiness : READY" in formatted
    assert "Static Datasets   : ALL READY" in formatted
    assert "Active Faults (Static) [READY]" in formatted
    assert "GEM GSHM Seismic Hazard (Static) [READY]" in formatted
    assert "Emergency Assembly Areas (Static) [READY]" in formatted
    assert "Earthquake Catalog (Dynamic) [READY]" in formatted


def test_run_status_json_and_check(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify run_status JSON output and check exit codes."""
    dummy_report = {
        "inspected_at": "2026-09-08T00:00:00Z",
        "overall_ready": True,
        "all_static_ready": True,
        "datasets": {
            "faults": {"ready": True, "count": 722, "sources": ["GEM_GAF"]},
            "gshm_hazard": {"ready": True, "points_count": 54291},
            "assembly_areas": {"ready": True, "total_areas": 678},
            "earthquakes": {"ready": True, "count": 784, "sources": ["AFAD"]},
        },
    }

    with patch(
        "app.scripts.provision_datasets.inspect_dataset_readiness",
        return_value=dummy_report,
    ):
        code = run_status(as_json=True, check_exit=True)
        assert code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["overall_ready"] is True
        assert data["all_static_ready"] is True

    # Test check_exit with unready report returns 1
    unready_report = dict(dummy_report)
    unready_report["all_static_ready"] = False
    with patch(
        "app.scripts.provision_datasets.inspect_dataset_readiness",
        return_value=unready_report,
    ):
        code = run_status(as_json=False, check_exit=True)
        assert code == 1


def test_provision_static_no_args() -> None:
    """Verify that calling provision-static with no datasets fails gracefully."""
    code = run_provision_static()
    assert code == 1


def test_provision_static_missing_file() -> None:
    """Verify that non-existent input files cause immediate exit code 1."""
    code = run_provision_static(faults_file="/non/existent/path.geojson")
    assert code == 1

    code = run_provision_static(gshm_gpkg="/non/existent/path.gpkg")
    assert code == 1

    code = run_provision_static(gshm_cache_dir="/non/existent/dir")
    assert code == 1

    code = run_provision_static(assembly_snapshot="/non/existent/snapshot.json")
    assert code == 1


def test_provision_static_delegates_to_importers(tmp_path: Path) -> None:
    """Verify that existing importer functions are called with correct arguments."""
    fault_file = tmp_path / "faults.geojson"
    fault_file.write_text("{}", encoding="utf-8")

    gpkg_file = tmp_path / "gem_gshm.gpkg"
    gpkg_file.write_text("", encoding="utf-8")

    assembly_file = tmp_path / "snapshot.json"
    assembly_file.write_text("{}", encoding="utf-8")

    with (
        patch(
            "app.scripts.provision_datasets.run_faults_import", return_value=0
        ) as mock_faults,
        patch(
            "app.scripts.provision_datasets.run_hazard_import", return_value=0
        ) as mock_hazard,
        patch(
            "app.scripts.provision_datasets.run_assembly_import", return_value=0
        ) as mock_assembly,
        patch(
            "app.scripts.provision_datasets.run_status", return_value=0
        ) as mock_status,
    ):
        code = run_provision_static(
            faults_file=str(fault_file),
            faults_scope="turkey-only",
            gshm_gpkg=str(gpkg_file),
            assembly_snapshot=str(assembly_file),
        )
        assert code == 0
        mock_faults.assert_called_once_with(
            file_path=str(fault_file),
            download=False,
            scope="turkey-only",
        )
        mock_hazard.assert_called_once_with(
            cache_dir=None,
            gpkg_path=str(gpkg_file),
            zip_path=None,
            verify_zip=True,
        )
        mock_assembly.assert_called_once_with(str(assembly_file))
        mock_status.assert_called_once_with(as_json=False, check_exit=False)


def test_provision_static_halts_on_failure(tmp_path: Path) -> None:
    """Verify that if an importer fails, execution halts and returns non-zero."""
    fault_file = tmp_path / "faults.geojson"
    fault_file.write_text("{}", encoding="utf-8")

    gpkg_file = tmp_path / "gem_gshm.gpkg"
    gpkg_file.write_text("", encoding="utf-8")

    with (
        patch(
            "app.scripts.provision_datasets.run_faults_import", return_value=2
        ) as mock_faults,
        patch(
            "app.scripts.provision_datasets.run_hazard_import", return_value=0
        ) as mock_hazard,
    ):
        code = run_provision_static(
            faults_file=str(fault_file),
            gshm_gpkg=str(gpkg_file),
        )
        assert code == 2
        mock_faults.assert_called_once()
        # GSHM should not even run after fault failure
        mock_hazard.assert_not_called()


# =====================================================================
# Live Integration Tests (Read-Only against Development Database)
# =====================================================================


@pytest.mark.integration
@pytest.mark.skipif(
    not is_postgres_available(),
    reason="PostgreSQL/PostGIS database is not reachable",
)
def test_live_inspect_dataset_readiness_read_only() -> None:
    """Verify read-only inspection against the live populated database.

    Guarantees:
    - All 3 static datasets and dynamic earthquakes are detected and ready.
    - Zero rows are modified, inserted, or deleted during inspection.
    """

    def get_counts(s: SessionLocal) -> dict[str, int]:
        return {
            "faults": s.execute(text("SELECT count(*) FROM fault_segments")).scalar(),
            "hazard_ds": s.execute(
                text("SELECT count(*) FROM hazard_datasets")
            ).scalar(),
            "hazard_pts": s.execute(
                text("SELECT count(*) FROM earthquake_hazard_points")
            ).scalar(),
            "assembly_ds": s.execute(
                text("SELECT count(*) FROM assembly_area_datasets")
            ).scalar(),
            "assembly_areas": s.execute(
                text("SELECT count(*) FROM assembly_areas")
            ).scalar(),
            "earthquakes": s.execute(
                text("SELECT count(*) FROM earthquake_events")
            ).scalar(),
        }

    with SessionLocal() as session:
        before_counts = get_counts(session)
        report = inspect_dataset_readiness(session)
        after_counts = get_counts(session)

    # Invariant: Status check must be strictly read-only
    assert before_counts == after_counts

    if before_counts["faults"] == 0:
        # Fresh unpopulated database (e.g. CI)
        assert report["overall_ready"] is False
        assert report["all_static_ready"] is False
        return

    # Invariants for currently populated database
    assert report["overall_ready"] is True
    assert report["all_static_ready"] is True

    # 1. Faults
    f = report["datasets"]["faults"]
    assert f["ready"] is True
    assert f["count"] > 0
    assert f["valid_geometry_count"] == f["count"]
    assert "GEM_GAF" in f["sources"]

    # 2. GSHM Hazard
    h = report["datasets"]["gshm_hazard"]
    assert h["ready"] is True
    assert h["points_count"] > 0
    assert h["source"] == "GEM_GSHM"
    assert h["source_version"] == "2026.1"
    assert h["hazard_metric"] == "PGA"
    assert h["unit"] == "g"
    assert h["return_period_years"] == 475
    assert h["min_pga_g"] > 0
    assert h["max_pga_g"] > h["min_pga_g"]

    # 3. Assembly Areas
    a = report["datasets"]["assembly_areas"]
    assert a["ready"] is True
    assert a["total_areas"] > 0
    assert a["source"] == "OpenStreetMap"
    assert a["point_features"] > 0

    # 4. Earthquakes
    e = report["datasets"]["earthquakes"]
    assert e["ready"] is True
    assert e["count"] > 0
    assert e["earliest_event"] is not None
    assert e["latest_event"] is not None
