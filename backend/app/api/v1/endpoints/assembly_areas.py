"""Public read-only REST API endpoints for emergency assembly areas."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.assembly_api import (
    AssemblyAreaFeatureCollection,
    AssemblyAreaNearbyFeatureCollection,
    AssemblyDatasetResponse,
)
from app.services.assembly_query import AssemblyQueryService

router = APIRouter()


def parse_assembly_bbox(
    bbox: str | None,
) -> tuple[float, float, float, float] | None:
    """Validate and parse bounding box parameter (min_lon,min_lat,max_lon,max_lat)."""
    if bbox is None:
        return None

    parts = [p.strip() for p in bbox.split(",")]
    if len(parts) != 4:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Bounding box must contain exactly 4 numbers: "
                "min_lon,min_lat,max_lon,max_lat"
            ),
        )
    try:
        coords = (
            float(parts[0]),
            float(parts[1]),
            float(parts[2]),
            float(parts[3]),
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Bounding box values must be valid floating-point numbers",
        ) from err

    b_min_lon, b_min_lat, b_max_lon, b_max_lat = coords

    if not (-180.0 <= b_min_lon <= 180.0 and -180.0 <= b_max_lon <= 180.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Longitude values in bounding box must be between -180 and 180",
        )

    if not (-90.0 <= b_min_lat <= 90.0 and -90.0 <= b_max_lat <= 90.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Latitude values in bounding box must be between -90 and 90",
        )

    if b_min_lon >= b_max_lon:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="min_lon must be strictly less than max_lon in bounding box",
        )

    if b_min_lat >= b_max_lat:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="min_lat must be strictly less than max_lat in bounding box",
        )

    return (b_min_lon, b_min_lat, b_max_lon, b_max_lat)


@router.get(
    "/dataset",
    response_model=AssemblyDatasetResponse,
    summary="Get active OpenStreetMap emergency assembly area dataset metadata",
    description=(
        "Retrieve comprehensive provenance, ODbL 1.0 licensing, "
        "OpenStreetMap contributors attribution, timestamps, cryptographic "
        "checksum, and geometry counts (discrete Points and closed Polygons) "
        "for the active emergency assembly area dataset. "
        "Data represents community-contributed gathering points and does NOT "
        "represent official Turkish government / AFAD disaster gathering area data."
    ),
)
def get_assembly_area_dataset_metadata(
    db: Annotated[Session, Depends(get_db)],
) -> AssemblyDatasetResponse:
    """Return active assembly area dataset provenance metadata."""
    service = AssemblyQueryService(db)
    return service.get_dataset_metadata()


@router.get(
    "/nearby",
    response_model=AssemblyAreaNearbyFeatureCollection,
    summary="Query nearby emergency assembly areas within a geodesic radius",
    description=(
        "Find emergency assembly areas within a specified geodesic radius "
        "(radius_km) from a WGS84 coordinate [lon, lat], returning an RFC 7946 "
        "GeoJSON FeatureCollection ordered by proximity. Distance is calculated "
        "using PostGIS spheroidal geography (WGS84 ellipsoid). For Polygon "
        "geometries, distance represents the minimum geodesic distance to the "
        "polygon boundary; for coordinates inside a polygon, distance is exactly 0. "
        "The technical maximum radius of 200 km is a resource boundary, NOT a safe "
        "walking or evacuation distance."
    ),
)
def get_nearby_assembly_areas(
    lat: Annotated[
        float,
        Query(
            description="Latitude in WGS84 decimal degrees (-90 to 90)",
            examples=[41.01],
        ),
    ],
    lon: Annotated[
        float,
        Query(
            description="Longitude in WGS84 decimal degrees (-180 to 180)",
            examples=[28.97],
        ),
    ],
    radius_km: Annotated[
        float,
        Query(
            description="Geodesic search radius in kilometers (0 < radius_km <= 200)",
            examples=[5.0],
        ),
    ],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Max features to return (1-100, default: 20)",
        ),
    ] = 20,
) -> AssemblyAreaNearbyFeatureCollection:
    """Find nearby assembly areas ordered by geodesic proximity."""
    if not (-90.0 <= lat <= 90.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Latitude must be between -90 and 90 degrees",
        )
    if not (-180.0 <= lon <= 180.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Longitude must be between -180 and 180 degrees",
        )
    if radius_km <= 0.0 or radius_km > 200.0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="radius_km must be greater than 0 and at most 200 km",
        )

    service = AssemblyQueryService(db)
    return service.get_nearby(
        longitude=lon,
        latitude=lat,
        radius_km=radius_km,
        limit=limit,
    )


@router.get(
    "",
    response_model=AssemblyAreaFeatureCollection,
    summary="List emergency assembly areas with optional bounding box filter",
    description=(
        "Retrieve emergency assembly areas as an RFC 7946 GeoJSON FeatureCollection "
        "for map visualization. Supports optional viewport bounding box filtering. "
        "Both Point and Polygon geometries are preserved in their native PostGIS "
        "representation without centroid flattening. "
        "Results are ordered deterministically by source_feature_id ASC."
    ),
)
def list_assembly_areas(
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=2000,
            description="Max features to return (1-2000, default: 1000)",
        ),
    ] = 1000,
    bbox: Annotated[
        str | None,
        Query(
            description="Viewport bounding box: min_lon,min_lat,max_lon,max_lat",
            examples=["28.0,40.5,29.5,41.5"],
        ),
    ] = None,
) -> AssemblyAreaFeatureCollection:
    """Retrieve assembly areas with optional viewport bounding box filter."""
    bbox_tuple = parse_assembly_bbox(bbox=bbox)

    service = AssemblyQueryService(db)
    if bbox_tuple is not None:
        b_min_lon, b_min_lat, b_max_lon, b_max_lat = bbox_tuple
        return service.get_collection(
            min_lon=b_min_lon,
            min_lat=b_min_lat,
            max_lon=b_max_lon,
            max_lat=b_max_lat,
            limit=limit,
        )

    return service.get_collection(limit=limit)
