"""Unit tests for OSM snapshot reader, validator, and geometry constructor."""

import hashlib
import json
from pathlib import Path

import pytest

from app.integrations.osm.osm_reader import (
    read_and_validate_osm_snapshot,
    verify_snapshot_integrity,
)


def create_synthetic_snapshot(
    tmp_path: Path,
    elements: list[dict],
    filename: str = "test_snapshot.json",
    generator: str = "Test Overpass",
    areas_base: str = "2026-09-03T10:22:36Z",
) -> Path:
    """Create a temporary synthetic Overpass JSON file for testing."""
    payload = {
        "version": 0.6,
        "generator": generator,
        "osm3s": {
            "timestamp_osm_base": "2026-09-04T08:48:11Z",
            "timestamp_areas_base": areas_base,
        },
        "elements": elements,
    }
    file_path = tmp_path / filename
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    return file_path


def test_node_parsing_creates_point_geometry(tmp_path: Path) -> None:
    """A valid node element must be parsed into a WKT POINT(lon lat)."""
    elements = [
        {
            "type": "node",
            "id": 1001,
            "lat": 41.0082376,
            "lon": 28.9783589,
            "tags": {
                "emergency": "assembly_point",
                "name": "Sultanahmet Meydanı",
                "operator": "İBB",
            },
        }
    ]
    snapshot = create_synthetic_snapshot(tmp_path, elements)
    points, meta = read_and_validate_osm_snapshot(
        snapshot, strict_checksum=False, strict_contract=False
    )

    assert len(points) == 1
    pt = points[0]
    assert pt.osm_id == 1001
    assert pt.osm_type == "node"
    assert pt.source_feature_id == "node/1001"
    assert pt.name == "Sultanahmet Meydanı"
    assert pt.operator == "İBB"
    assert pt.geometry_type == "Point"
    # Longitude first, Latitude second in WKT
    assert pt.wkt_geometry == "POINT(28.9783589 41.0082376)"
    assert meta["feature_count"] == 1
    assert meta["node_count"] == 1
    assert meta["way_count"] == 0


def test_way_parsing_creates_polygon_geometry(tmp_path: Path) -> None:
    """A valid closed way must be parsed into a WKT POLYGON((...))."""
    elements = [
        {
            "type": "way",
            "id": 2001,
            "geometry": [
                {"lat": 41.0, "lon": 28.0},
                {"lat": 41.0, "lon": 28.01},
                {"lat": 41.01, "lon": 28.01},
                {"lat": 41.01, "lon": 28.0},
                {"lat": 41.0, "lon": 28.0},  # Closing coordinate
            ],
            "tags": {
                "emergency": "assembly_point",
                "name": "Büyük Park",
            },
        }
    ]
    snapshot = create_synthetic_snapshot(tmp_path, elements)
    points, meta = read_and_validate_osm_snapshot(
        snapshot, strict_checksum=False, strict_contract=False
    )

    assert len(points) == 1
    pt = points[0]
    assert pt.osm_id == 2001
    assert pt.osm_type == "way"
    assert pt.source_feature_id == "way/2001"
    assert pt.geometry_type == "Polygon"
    assert pt.wkt_geometry.startswith("POLYGON((28.0000000 41.0000000")
    assert pt.wkt_geometry.endswith("28.0000000 41.0000000))")
    assert meta["way_count"] == 1


def test_open_way_rejected(tmp_path: Path) -> None:
    """An open way (first coord != last coord) must be rejected."""
    elements = [
        {
            "type": "way",
            "id": 2002,
            "geometry": [
                {"lat": 41.0, "lon": 28.0},
                {"lat": 41.0, "lon": 28.01},
                {"lat": 41.01, "lon": 28.01},
                {"lat": 41.01, "lon": 28.0},
                {"lat": 41.005, "lon": 28.005},  # Does not match start
            ],
            "tags": {"emergency": "assembly_point"},
        }
    ]
    snapshot = create_synthetic_snapshot(tmp_path, elements)
    with pytest.raises(ValueError, match="is open"):
        read_and_validate_osm_snapshot(
            snapshot, strict_checksum=False, strict_contract=False
        )


def test_way_with_insufficient_nodes_rejected(tmp_path: Path) -> None:
    """Way with fewer than 4 nodes cannot form a valid closed polygon."""
    elements = [
        {
            "type": "way",
            "id": 2003,
            "geometry": [
                {"lat": 41.0, "lon": 28.0},
                {"lat": 41.0, "lon": 28.01},
                {"lat": 41.0, "lon": 28.0},
            ],
            "tags": {"emergency": "assembly_point"},
        }
    ]
    snapshot = create_synthetic_snapshot(tmp_path, elements)
    with pytest.raises(ValueError, match="minimum 4 required"):
        read_and_validate_osm_snapshot(
            snapshot, strict_checksum=False, strict_contract=False
        )


def test_relation_element_rejected(tmp_path: Path) -> None:
    """Any relation element must be explicitly rejected."""
    elements = [
        {
            "type": "relation",
            "id": 3001,
            "tags": {"emergency": "assembly_point"},
        }
    ]
    snapshot = create_synthetic_snapshot(tmp_path, elements)
    with pytest.raises(ValueError, match="Unexpected relation element"):
        read_and_validate_osm_snapshot(
            snapshot, strict_checksum=False, strict_contract=False
        )


def test_missing_emergency_tag_rejected(tmp_path: Path) -> None:
    """Elements without emergency=assembly_point must be rejected."""
    elements = [
        {
            "type": "node",
            "id": 1002,
            "lat": 41.0,
            "lon": 28.0,
            "tags": {"amenity": "shelter"},
        }
    ]
    snapshot = create_synthetic_snapshot(tmp_path, elements)
    with pytest.raises(
        ValueError, match="missing required tag 'emergency=assembly_point'"
    ):
        read_and_validate_osm_snapshot(
            snapshot, strict_checksum=False, strict_contract=False
        )


def test_wrong_emergency_value_rejected(tmp_path: Path) -> None:
    """Elements with emergency!=assembly_point must be rejected."""
    elements = [
        {
            "type": "node",
            "id": 1003,
            "lat": 41.0,
            "lon": 28.0,
            "tags": {"emergency": "phone"},
        }
    ]
    snapshot = create_synthetic_snapshot(tmp_path, elements)
    with pytest.raises(
        ValueError, match="missing required tag 'emergency=assembly_point'"
    ):
        read_and_validate_osm_snapshot(
            snapshot, strict_checksum=False, strict_contract=False
        )


def test_duplicate_natural_identity_rejected(tmp_path: Path) -> None:
    """Duplicate (type, id) in snapshot must trigger a ValueError."""
    elements = [
        {
            "type": "node",
            "id": 1004,
            "lat": 41.0,
            "lon": 28.0,
            "tags": {"emergency": "assembly_point"},
        },
        {
            "type": "node",
            "id": 1004,  # Duplicate node ID
            "lat": 41.05,
            "lon": 28.05,
            "tags": {"emergency": "assembly_point"},
        },
    ]
    snapshot = create_synthetic_snapshot(tmp_path, elements)
    with pytest.raises(ValueError, match="Duplicate natural identity detected"):
        read_and_validate_osm_snapshot(
            snapshot, strict_checksum=False, strict_contract=False
        )


def test_out_of_range_coordinates_rejected(tmp_path: Path) -> None:
    """Latitude > 90 or Longitude > 180 must be rejected."""
    elements = [
        {
            "type": "node",
            "id": 1005,
            "lat": 95.0,  # Invalid latitude
            "lon": 28.0,
            "tags": {"emergency": "assembly_point"},
        }
    ]
    snapshot = create_synthetic_snapshot(tmp_path, elements)
    with pytest.raises(ValueError, match="coords out of range"):
        read_and_validate_osm_snapshot(
            snapshot, strict_checksum=False, strict_contract=False
        )


def test_non_finite_coordinates_rejected(tmp_path: Path) -> None:
    """NaN or Inf coordinates must be rejected."""
    elements = [
        {
            "type": "node",
            "id": 1006,
            "lat": "NaN",
            "lon": 28.0,
            "tags": {"emergency": "assembly_point"},
        }
    ]
    snapshot = create_synthetic_snapshot(tmp_path, elements)
    with pytest.raises(ValueError, match="non-finite coords"):
        read_and_validate_osm_snapshot(
            snapshot, strict_checksum=False, strict_contract=False
        )


def test_verify_snapshot_integrity(tmp_path: Path) -> None:
    """Integrity check must verify file existence, exact size, and SHA-256."""
    content = b'{"elements": []}'
    test_file = tmp_path / "integrity_test.json"
    test_file.write_bytes(content)

    expected_size = len(content)
    expected_sha256 = hashlib.sha256(content).hexdigest()

    # Success case
    size, sha = verify_snapshot_integrity(
        test_file, expected_size=expected_size, expected_sha256=expected_sha256
    )
    assert size == expected_size
    assert sha == expected_sha256

    # File not found
    with pytest.raises(FileNotFoundError):
        verify_snapshot_integrity(tmp_path / "non_existent.json")

    # Size mismatch
    with pytest.raises(ValueError, match="size mismatch"):
        verify_snapshot_integrity(
            test_file, expected_size=9999, expected_sha256=expected_sha256
        )

    # SHA-256 mismatch
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        verify_snapshot_integrity(
            test_file,
            expected_size=expected_size,
            expected_sha256="0000000000000000000000000000000000000000000000000000000000000000",
        )


def test_strict_contract_validation_fails_on_wrong_counts(tmp_path: Path) -> None:
    """strict_contract=True must fail closed when counts do not equal 678/650/28/0."""
    elements = [
        {
            "type": "node",
            "id": 1007,
            "lat": 41.0,
            "lon": 28.0,
            "tags": {"emergency": "assembly_point"},
        }
    ]
    snapshot = create_synthetic_snapshot(tmp_path, elements)
    with pytest.raises(ValueError, match="OSM contract violation"):
        read_and_validate_osm_snapshot(
            snapshot, strict_checksum=False, strict_contract=True
        )
