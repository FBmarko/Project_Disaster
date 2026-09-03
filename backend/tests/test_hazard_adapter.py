import sqlite3
from pathlib import Path

import pytest

from app.integrations.gem.hazard_reader import (
    stream_turkey_hazard_records,
    verify_geopackage_metadata,
    verify_zip_artifact,
)


def create_synthetic_gpkg(
    path: Path, points: list[tuple[int, float, float, float]]
) -> None:
    """Create a minimal synthetic SQLite GeoPackage for testing."""
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE gpkg_contents (table_name TEXT PRIMARY KEY, "
        "data_type TEXT, identifier TEXT, min_x REAL, min_y REAL, "
        "max_x REAL, max_y REAL, srs_id INTEGER)"
    )
    cur.execute(
        "INSERT INTO gpkg_contents VALUES "
        "('v2026', 'features', 'v2026', 24.0, 34.0, 46.0, 44.0, 4326)"
    )
    cur.execute(
        "CREATE TABLE gpkg_geometry_columns (table_name TEXT, column_name TEXT, "
        "geometry_type_name TEXT, srs_id INTEGER, z INTEGER, m INTEGER)"
    )
    cur.execute(
        "INSERT INTO gpkg_geometry_columns VALUES "
        "('v2026', 'geom', 'POINT', 4326, 0, 0)"
    )
    cur.execute(
        'CREATE TABLE "v2026" ("fid" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, '
        '"geom" POINT, "lon" REAL, "lat" REAL, "pga" REAL)'
    )
    cur.execute(
        'CREATE VIRTUAL TABLE "rtree_v2026_geom" USING '
        "rtree(id, minx, maxx, miny, maxy)"
    )
    for fid, lon, lat, pga in points:
        cur.execute(
            'INSERT INTO "v2026" (fid, lon, lat, pga) VALUES (?, ?, ?, ?)',
            (fid, lon, lat, pga),
        )
        cur.execute(
            'INSERT INTO "rtree_v2026_geom" VALUES (?, ?, ?, ?, ?)',
            (fid, lon, lon, lat, lat),
        )
    conn.commit()
    conn.close()


def test_verify_zip_artifact_nonexistent(tmp_path: Path) -> None:
    """Verify FileNotFoundError on non-existent archive."""
    with pytest.raises(FileNotFoundError):
        verify_zip_artifact(tmp_path / "nonexistent.zip")


def test_verify_zip_artifact_size_mismatch(tmp_path: Path) -> None:
    """Verify size mismatch raises ValueError."""
    fake_zip = tmp_path / "test.zip"
    fake_zip.write_bytes(b"PK\x03\x04" + b"\x00" * 100)
    with pytest.raises(ValueError, match="Source ZIP size mismatch"):
        verify_zip_artifact(fake_zip)


def test_verify_geopackage_metadata_synthetic(tmp_path: Path) -> None:
    """Verify valid synthetic GeoPackage metadata passes check."""
    gpkg_file = tmp_path / "test.gpkg"
    create_synthetic_gpkg(gpkg_file, [(1, 35.0, 39.0, 0.2), (2, 36.0, 40.0, 0.3)])
    verify_geopackage_metadata(gpkg_file, check_full_size=False)


def test_verify_geopackage_metadata_missing_layer(tmp_path: Path) -> None:
    """Verify error raised when required layer is missing."""
    gpkg_file = tmp_path / "empty.gpkg"
    conn = sqlite3.connect(gpkg_file)
    conn.execute(
        "CREATE TABLE gpkg_contents (table_name TEXT, data_type TEXT, srs_id INTEGER)"
    )
    conn.commit()
    conn.close()

    with pytest.raises(ValueError, match="missing expected layer"):
        verify_geopackage_metadata(gpkg_file, check_full_size=False)


def test_stream_turkey_hazard_records(tmp_path: Path) -> None:
    """Verify streaming extraction filter with synthetic GeoPackage."""
    gpkg_file = tmp_path / "stream_test.gpkg"
    points = [
        (1, 30.0, 38.0, 0.15),  # Inside Turkey bbox
        (2, 35.0, 39.0, 0.25),  # Inside Turkey bbox
        (3, 40.0, 41.0, 0.35),  # Inside Turkey bbox
        (4, 10.0, 50.0, 0.05),  # Outside bbox (Germany)
    ]
    create_synthetic_gpkg(gpkg_file, points)

    stream = stream_turkey_hazard_records(
        gpkg_file, bbox=(24.0, 34.0, 46.0, 44.0), batch_size=2
    )
    batches = list(stream)
    assert len(batches) == 2
    all_recs = [r for b in batches for r in b]
    assert len(all_recs) == 3
    assert {r.fid for r in all_recs} == {1, 2, 3}
    assert all_recs[0].longitude == 30.0
    assert all_recs[0].pga_g == 0.15
