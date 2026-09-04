import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.integrations.gem.mapping import (
    GEM_SOURCE_IDENTIFIER,
    TURKEY_CONTEXT_BBOX,
    build_gem_source_feature_id,
    build_gem_source_reference,
    is_feature_in_bbox,
    normalize_geometry_to_multilinestring,
)
from app.integrations.gem.parser import parse_gem_feature_collection
from app.schemas.fault_segment import FaultSegmentCreate


def test_gem_source_feature_id_derivation() -> None:
    """Verify source_feature_id directly uses catalog_id."""
    props = {"catalog_id": "ME_BGCS001", "catalog_name": "EMME"}
    coords = [[[26.0, 41.0], [26.5, 41.5]]]
    feature_id = build_gem_source_feature_id(props, coords)
    assert feature_id == "ME_BGCS001"

    # Fallback to deterministic coordinate hash when catalog_id is absent
    fallback_id = build_gem_source_feature_id({}, coords)
    assert fallback_id.startswith("GEM_UNKNOWN:")


def test_gem_source_reference() -> None:
    """Verify source reference string includes citation and catalog name."""
    props = {"catalog_name": "EMME"}
    ref = build_gem_source_reference(props)
    assert "Styron & Pagani (2020)" in ref
    assert "[EMME]" in ref


def test_geometry_normalization_linestring_to_multilinestring() -> None:
    """Verify LineString coordinates are normalized to MultiLineString and 2D."""
    raw_coords = [[26.1, 41.2, 10.0], [26.2, 41.3, 12.0]]
    multiline = normalize_geometry_to_multilinestring("LineString", raw_coords)
    assert len(multiline) == 1
    assert multiline[0] == [[26.1, 41.2], [26.2, 41.3]]


def test_geometry_normalization_unsupported_type() -> None:
    """Verify unsupported geometry types raise ValueError."""
    with pytest.raises(ValueError, match="Unsupported geometry type"):
        normalize_geometry_to_multilinestring("Point", [26.0, 41.0])


def test_bbox_filtering() -> None:
    """Verify is_feature_in_bbox identifies coordinates inside and outside."""
    inside_coords = [[[29.0, 40.5], [29.5, 40.6]]]
    outside_coords = [[[10.0, 50.0], [10.5, 50.5]]]

    assert is_feature_in_bbox(inside_coords, TURKEY_CONTEXT_BBOX) is True
    assert is_feature_in_bbox(outside_coords, TURKEY_CONTEXT_BBOX) is False


def test_parse_gem_feature_collection_from_fixture() -> None:
    """Verify parsing sample features from fixture with corrected semantics."""
    fixture_path = Path(__file__).parent / "fixtures" / "gem_faults_turkey_sample.json"
    with open(fixture_path, encoding="utf-8") as f:
        fixture_data = json.load(f)

    records, skipped, failed = parse_gem_feature_collection(
        fixture_data, bbox=TURKEY_CONTEXT_BBOX
    )
    assert len(records) == 5
    assert skipped == 0
    assert failed == 0

    first = records[0]
    assert first.source == GEM_SOURCE_IDENTIFIER
    assert first.source_feature_id == "ME_BGCS001"
    # Semantics: segment_name is NULL for GEM, activity_status is NULL
    assert first.segment_name is None
    assert first.activity_status is None
    # Raw source properties preserved in JSONB
    assert first.source_properties.get("epistemic_quality") == "1"
    assert first.fault_type == "Sinistral-Normal"
    assert len(first.coordinates) == 1
    assert len(first.coordinates[0]) == 16


def test_parse_gem_feature_malformed() -> None:
    """Verify malformed features are recorded as failures rather than crashing."""
    malformed_data = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {}, "geometry": None},
            {
                "type": "Feature",
                "properties": {},
                "geometry": {"type": "LineString", "coordinates": []},
            },
        ],
    }
    records, skipped, failed = parse_gem_feature_collection(malformed_data)
    assert len(records) == 0
    assert failed == 2


def test_pydantic_coordinate_validation() -> None:
    """Verify Pydantic validation rejects out-of-range coordinates."""
    with pytest.raises(ValidationError):
        FaultSegmentCreate(
            source="GEM_GAF",
            source_feature_id="TEST:1",
            coordinates=[[[200.0, 41.0], [201.0, 41.5]]],  # Longitude > 180
        )
