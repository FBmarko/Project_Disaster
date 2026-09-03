import logging
from typing import Any

from pydantic import ValidationError

from app.integrations.gem.mapping import (
    GEM_SOURCE_IDENTIFIER,
    build_gem_source_feature_id,
    build_gem_source_reference,
    is_feature_in_bbox,
    normalize_geometry_to_multilinestring,
)
from app.schemas.fault_segment import FaultSegmentCreate

logger = logging.getLogger(__name__)


def parse_gem_feature(
    feature: dict[str, Any],
    bbox: tuple[float, float, float, float] | None = None,
) -> FaultSegmentCreate | None:
    """Parse and normalize a single GEM GeoJSON feature into a FaultSegmentCreate model.

    Returns None if feature does not fall within the optional bbox.
    Raises ValueError or ValidationError if feature is malformed.
    """
    geom = feature.get("geometry")
    if not geom or not isinstance(geom, dict):
        raise ValueError("Feature missing geometry object")

    geom_type = geom.get("type")
    raw_coords = geom.get("coordinates")
    if not geom_type or not raw_coords:
        raise ValueError("Feature geometry missing type or coordinates")

    # Normalize geometry to MultiLineString
    normalized_coords = normalize_geometry_to_multilinestring(geom_type, raw_coords)

    # Apply bounding box filter if specified
    if bbox is not None and not is_feature_in_bbox(normalized_coords, bbox):
        return None

    properties = feature.get("properties") or {}

    source_feature_id = build_gem_source_feature_id(properties, normalized_coords)
    source_reference = build_gem_source_reference(properties)

    name = properties.get("name")
    if name:
        name = str(name).strip()

    # In GEM GAF, catalog_id is an identifier, not a segment name; segment_name is None
    segment_name = None

    fault_type = properties.get("slip_type")
    if fault_type:
        fault_type = str(fault_type).strip()

    # activity_confidence is stored in source_properties; activity_status is None
    activity_status = None

    return FaultSegmentCreate(
        source=GEM_SOURCE_IDENTIFIER,
        source_feature_id=source_feature_id,
        name=name or None,
        segment_name=segment_name,
        fault_type=fault_type or None,
        activity_status=activity_status,
        source_reference=source_reference,
        source_properties=properties,
        coordinates=normalized_coords,
    )


def parse_gem_feature_collection(
    data: dict[str, Any],
    bbox: tuple[float, float, float, float] | None = None,
) -> tuple[list[FaultSegmentCreate], int, int]:
    """Parse an entire GEM GeoJSON FeatureCollection.

    Returns:
        (valid_records, skipped_outside_bbox_count, failed_count)
    """
    features = data.get("features")
    if not isinstance(features, list):
        raise ValueError("Invalid GeoJSON: 'features' must be a list")

    valid_records: list[FaultSegmentCreate] = []
    skipped_count = 0
    failed_count = 0

    for idx, feat in enumerate(features):
        try:
            parsed = parse_gem_feature(feat, bbox=bbox)
            if parsed is None:
                skipped_count += 1
            else:
                valid_records.append(parsed)
        except (ValueError, ValidationError) as e:
            failed_count += 1
            logger.warning("Failed to parse GEM feature index %d: %s", idx, e)

    return valid_records, skipped_count, failed_count
