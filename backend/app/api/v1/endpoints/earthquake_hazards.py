"""Public read-only REST API endpoints for seismic hazard data."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.hazard_api import (
    HazardDatasetMetadataResponse,
    HazardFeatureCollection,
    HazardNearestFeature,
)
from app.services.hazard_query import HazardQueryService

router = APIRouter()


@router.get(
    "/dataset",
    response_model=HazardDatasetMetadataResponse,
    summary="Get active seismic hazard dataset metadata",
    description=(
        "Retrieve comprehensive scientific provenance, return period, reference rock "
        "conditions (Vs30 = 800 m/s), DOIs, license, and geographic scope for the "
        "active GEM GSHM v2026.1 dataset."
    ),
)
def get_hazard_dataset_metadata(
    db: Annotated[Session, Depends(get_db)],
) -> HazardDatasetMetadataResponse:
    """Return active seismic hazard dataset metadata."""
    service = HazardQueryService(db)
    return service.get_dataset_metadata()


@router.get(
    "/nearest",
    response_model=HazardNearestFeature,
    summary="Query modeled hazard at the nearest GEM source node",
    description=(
        "Retrieve the modeled Peak Ground Acceleration (PGA in g) at the nearest "
        "discrete GEM GSHM v2026.1 source node, along with the exact geodesic "
        "distance in kilometers from the requested WGS84 coordinate. Local soil "
        "amplification is not represented (reference rock Vs30 = 800 m/s). "
        "Coordinates must fall within the imported Türkiye-context scope "
        "[24.0..46.0°E, 34.0..44.0°N]."
    ),
)
def get_nearest_hazard(
    lat: Annotated[
        float,
        Query(
            description="Latitude in WGS84 decimal degrees (-90 to 90)",
            examples=[39.93],
        ),
    ],
    lon: Annotated[
        float,
        Query(
            description="Longitude in WGS84 decimal degrees (-180 to 180)",
            examples=[32.85],
        ),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> HazardNearestFeature:
    """Find nearest modeled GEM source node and distance."""
    service = HazardQueryService(db)
    return service.get_nearest_hazard_point(longitude=lon, latitude=lat)


@router.get(
    "",
    response_model=HazardFeatureCollection,
    summary="List discrete hazard points within a bounding box",
    description=(
        "Retrieve discrete GEM GSHM v2026.1 hazard nodes as an RFC 7946 GeoJSON "
        "FeatureCollection for map viewport display. Bounding box is required and must "
        "fall within the imported Türkiye-context scope [24.0..46.0°E, 34.0..44.0°N]."
    ),
)
def list_hazard_points_in_bbox(
    bbox: Annotated[
        str,
        Query(
            description="Viewport bounding box: min_lon,min_lat,max_lon,max_lat",
            examples=["28.0,40.0,30.0,42.0"],
        ),
    ],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=2000,
            description="Max features to return (1-2000, default: 1000)",
        ),
    ] = 1000,
    offset: Annotated[
        int,
        Query(
            ge=0,
            description="Number of features to skip for pagination (default: 0)",
        ),
    ] = 0,
) -> HazardFeatureCollection:
    """List discrete hazard points within a bounding box."""
    service = HazardQueryService(db)
    return service.get_hazard_points_in_bbox(bbox_str=bbox, limit=limit, offset=offset)
