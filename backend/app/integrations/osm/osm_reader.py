"""OSM JSON snapshot parser, validator, and geometry constructor for assembly points."""

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.integrations.osm.osm_constants import (
    OSM_EXPECTED_FEATURE_COUNT,
    OSM_EXPECTED_NODE_COUNT,
    OSM_EXPECTED_RELATION_COUNT,
    OSM_EXPECTED_SHA256,
    OSM_EXPECTED_SIZE_BYTES,
    OSM_EXPECTED_WAY_COUNT,
)
from app.integrations.osm.osm_sanitizer import sanitize_osm_tags


@dataclass(frozen=True)
class ParsedAssemblyPoint:
    """Normalized, validated assembly point record parsed from OSM snapshot."""

    osm_id: int
    osm_type: str
    source_feature_id: str
    name: str | None
    ref: str | None
    operator: str | None
    wkt_geometry: str
    geometry_type: str
    source_properties: dict[str, Any]


def verify_snapshot_integrity(
    snapshot_path: Path,
    expected_size: int = OSM_EXPECTED_SIZE_BYTES,
    expected_sha256: str = OSM_EXPECTED_SHA256,
) -> tuple[int, str]:
    """Verify that snapshot file exists, matches exact byte size and SHA-256 hash.

    Args:
        snapshot_path: Path to the snapshot JSON file.
        expected_size: Expected byte size.
        expected_sha256: Expected SHA-256 hexadecimal string.

    Returns:
        tuple of (actual_size, actual_sha256).

    Raises:
        FileNotFoundError: If the snapshot file does not exist.
        ValueError: If size or SHA-256 checksum does not match expected values.
    """
    if not snapshot_path.is_file():
        raise FileNotFoundError(f"OSM snapshot file not found: {snapshot_path}")

    actual_size = snapshot_path.stat().st_size
    if actual_size != expected_size:
        raise ValueError(
            f"OSM snapshot size mismatch: expected {expected_size} bytes, "
            f"got {actual_size} bytes."
        )

    hasher = hashlib.sha256()
    with open(snapshot_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    actual_sha256 = hasher.hexdigest().lower()

    if actual_sha256 != expected_sha256.lower():
        raise ValueError(
            f"OSM snapshot SHA-256 mismatch: expected {expected_sha256}, "
            f"got {actual_sha256}."
        )

    return actual_size, actual_sha256


def read_and_validate_osm_snapshot(
    snapshot_path: Path,
    strict_checksum: bool = True,
    strict_contract: bool = True,
) -> tuple[list[ParsedAssemblyPoint], dict[str, Any]]:
    """Parse, validate, and construct geometries from an OSM assembly-point snapshot.

    Args:
        snapshot_path: Path to the JSON snapshot file.
        strict_checksum: Whether to enforce expected size and SHA-256.
        strict_contract: Whether to enforce exact element counts (678 / 650 / 28 / 0).

    Returns:
        tuple of (parsed_points_list, source_metadata_dict).

    Raises:
        ValueError: If contract, element validation, or geometry construction fails.
    """
    if strict_checksum:
        verify_snapshot_integrity(snapshot_path)

    with open(snapshot_path, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception as err:
            raise ValueError(f"Failed to parse OSM snapshot as JSON: {err}") from err

    elements = data.get("elements")
    if not isinstance(elements, list):
        raise ValueError(
            "Invalid OSM snapshot: 'elements' array missing or not a list."
        )

    # High-level contract validation
    total_elements = len(elements)
    node_count = sum(1 for e in elements if e.get("type") == "node")
    way_count = sum(1 for e in elements if e.get("type") == "way")
    relation_count = sum(1 for e in elements if e.get("type") == "relation")

    if strict_contract:
        if total_elements != OSM_EXPECTED_FEATURE_COUNT:
            raise ValueError(
                f"OSM contract violation: expected "
                f"{OSM_EXPECTED_FEATURE_COUNT} total elements, "
                f"got {total_elements}."
            )
        if node_count != OSM_EXPECTED_NODE_COUNT:
            raise ValueError(
                f"OSM contract violation: expected {OSM_EXPECTED_NODE_COUNT} "
                f"nodes, got {node_count}."
            )
        if way_count != OSM_EXPECTED_WAY_COUNT:
            raise ValueError(
                f"OSM contract violation: expected {OSM_EXPECTED_WAY_COUNT} "
                f"ways, got {way_count}."
            )
        if relation_count != OSM_EXPECTED_RELATION_COUNT:
            raise ValueError(
                f"OSM contract violation: expected {OSM_EXPECTED_RELATION_COUNT} "
                f"relations, got {relation_count}."
            )

    # Element-by-element parsing and identity collision tracking
    seen_identities: set[str] = set()
    parsed_points: list[ParsedAssemblyPoint] = []

    for elem in elements:
        elem_type = elem.get("type")
        elem_id = elem.get("id")

        if not elem_type or elem_id is None:
            raise ValueError(f"Malformed element missing type or id: {elem}")

        source_feature_id = f"{elem_type}/{elem_id}"
        if source_feature_id in seen_identities:
            raise ValueError(
                f"Duplicate natural identity detected in snapshot: {source_feature_id}"
            )
        seen_identities.add(source_feature_id)

        # Reject relations explicitly
        if elem_type == "relation":
            raise ValueError(
                f"Unexpected relation element {source_feature_id}: relations are not "
                f"supported in this snapshot version."
            )

        # Require emergency=assembly_point
        tags = elem.get("tags") or {}
        if tags.get("emergency") != "assembly_point":
            raise ValueError(
                f"Element {source_feature_id} missing required tag "
                f"'emergency=assembly_point'. Observed tags: {tags}"
            )

        name, ref, operator, sanitized_properties = sanitize_osm_tags(tags)

        # Parse geometry
        if elem_type == "node":
            lat = elem.get("lat")
            lon = elem.get("lon")
            if lat is None or lon is None:
                raise ValueError(f"Node {source_feature_id} missing lat or lon.")

            try:
                lat_f = float(lat)
                lon_f = float(lon)
            except (ValueError, TypeError) as err:
                raise ValueError(
                    f"Node {source_feature_id} non-numeric coords: {err}"
                ) from err

            if not (math.isfinite(lat_f) and math.isfinite(lon_f)):
                raise ValueError(
                    f"Node {source_feature_id} non-finite coords: {lat_f}, {lon_f}"
                )
            if not (-90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0):
                raise ValueError(
                    f"Node {source_feature_id} coords out of range: {lat_f}, {lon_f}"
                )

            wkt_geometry = f"POINT({lon_f:.7f} {lat_f:.7f})"
            geometry_type = "Point"

        elif elem_type == "way":
            geom_nodes = elem.get("geometry")
            if not isinstance(geom_nodes, list) or len(geom_nodes) < 4:
                raise ValueError(
                    f"Way {source_feature_id} has invalid geometry nodes "
                    "(minimum 4 required for closed polygon ring)."
                )

            ring_coords: list[tuple[float, float]] = []
            for pt in geom_nodes:
                pt_lat = pt.get("lat")
                pt_lon = pt.get("lon")
                if pt_lat is None or pt_lon is None:
                    raise ValueError(
                        f"Way {source_feature_id} coordinate node missing lat/lon."
                    )

                try:
                    lat_f = float(pt_lat)
                    lon_f = float(pt_lon)
                except (ValueError, TypeError) as err:
                    raise ValueError(
                        f"Way {source_feature_id} non-numeric coords: {err}"
                    ) from err

                if not (math.isfinite(lat_f) and math.isfinite(lon_f)):
                    raise ValueError(
                        f"Way {source_feature_id} non-finite coords: {lat_f}, {lon_f}"
                    )
                if not (-90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0):
                    raise ValueError(
                        f"Way {source_feature_id} coords out of range: {lat_f}, {lon_f}"
                    )

                ring_coords.append((lon_f, lat_f))

            # Verify ring closure: first coordinate == last coordinate
            first_pt = ring_coords[0]
            last_pt = ring_coords[-1]
            if not (
                math.isclose(first_pt[0], last_pt[0], abs_tol=1e-9)
                and math.isclose(first_pt[1], last_pt[1], abs_tol=1e-9)
            ):
                raise ValueError(
                    f"Way {source_feature_id} is open (first coordinate {first_pt} "
                    f"does not match last coordinate {last_pt}). "
                    "Open ways cannot be converted to polygons."
                )

            coords_str = ", ".join(f"{lon:.7f} {lat:.7f}" for lon, lat in ring_coords)
            wkt_geometry = f"POLYGON(({coords_str}))"
            geometry_type = "Polygon"

        else:
            raise ValueError(f"Unsupported OSM element type: {elem_type}")

        parsed_points.append(
            ParsedAssemblyPoint(
                osm_id=elem_id,
                osm_type=elem_type,
                source_feature_id=source_feature_id,
                name=name,
                ref=ref,
                operator=operator,
                wkt_geometry=wkt_geometry,
                geometry_type=geometry_type,
                source_properties=sanitized_properties,
            )
        )

    # Build reproducible dataset-level metadata
    osm3s = data.get("osm3s") or {}
    source_metadata = {
        "generator": data.get("generator"),
        "areas_base_timestamp": osm3s.get("timestamp_areas_base"),
        "feature_count": total_elements,
        "node_count": node_count,
        "way_count": way_count,
        "relation_count": relation_count,
    }

    return parsed_points, source_metadata
