import hashlib
import json
from typing import Any

# Regional tectonic bounding box for Türkiye and immediate border context
# Longitude: 24.0°E (Aegean / Greece) to 46.0°E (Iran / Caucasus)
# Latitude: 34.0°N (Mediterranean / Cyprus) to 44.0°N (Black Sea)
TURKEY_CONTEXT_BBOX = (24.0, 34.0, 46.0, 44.0)

GEM_SOURCE_IDENTIFIER = "GEM_GAF"
GEM_BASE_CITATION = "Styron & Pagani (2020), GEM Global Active Faults Database"


def build_gem_source_feature_id(
    properties: dict[str, Any], coordinates: list[Any]
) -> str:
    """Derive stable source feature identifier from GEM properties.

    Uses `catalog_id` directly as the primary identifier. Falls back
    to a deterministic coordinate hash only if catalog_id is absent.
    """
    catalog_id = properties.get("catalog_id")
    if catalog_id:
        return str(catalog_id).strip()

    # Fallback to deterministic SHA-256 hash of coordinates
    coords_json = json.dumps(coordinates, sort_keys=True)
    coord_hash = hashlib.sha256(coords_json.encode("utf-8")).hexdigest()[:16]
    return f"GEM_UNKNOWN:{coord_hash}"


def build_gem_source_reference(properties: dict[str, Any]) -> str:
    """Generate a clean citation and reference string for the GEM record."""
    catalog_name = properties.get("catalog_name")
    if catalog_name:
        return f"{GEM_BASE_CITATION} [{catalog_name.strip()}]"
    return GEM_BASE_CITATION


def normalize_geometry_to_multilinestring(
    geom_type: str,
    raw_coords: list[Any],
) -> list[list[list[float]]]:
    """Convert LineString or MultiLineString to 2D MultiLineString format.

    Ensures all points are [longitude, latitude] floats and trims Z values.
    """
    if geom_type == "LineString":
        # Raw coords: [[lon, lat], [lon, lat], ...]
        line = [[float(pt[0]), float(pt[1])] for pt in raw_coords if len(pt) >= 2]
        return [line]

    if geom_type == "MultiLineString":
        # Raw coords: [[[lon, lat], ...], ...]
        multiline = []
        for raw_line in raw_coords:
            line = [[float(pt[0]), float(pt[1])] for pt in raw_line if len(pt) >= 2]
            if len(line) >= 2:
                multiline.append(line)
        return multiline

    raise ValueError(
        f"Unsupported geometry type: '{geom_type}'. "
        "Must be LineString or MultiLineString."
    )


def is_feature_in_bbox(
    coordinates: list[list[list[float]]],
    bbox: tuple[float, float, float, float],
) -> bool:
    """Check if any coordinate point falls within bounding box."""
    min_lon, min_lat, max_lon, max_lat = bbox
    for line in coordinates:
        for pt in line:
            lon, lat = pt[0], pt[1]
            if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
                return True
    return False
