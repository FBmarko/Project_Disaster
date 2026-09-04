import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.api.v1.endpoints.earthquakes import validate_temporal_params
from app.db.dependencies import get_db
from app.schemas.earthquake_api import EarthquakeFeatureCollection
from app.schemas.fault_line_api import FaultFeature, FaultFeatureCollection
from app.services.earthquake_query import EarthquakeQueryService
from app.services.fault_query import FaultQueryService

router = APIRouter()


def parse_bbox_param(bbox: str | None) -> tuple[float, float, float, float] | None:
    """Validate and parse bounding box (min_lon, min_lat, max_lon, max_lat)."""
    if bbox is None:
        return None

    parts = bbox.split(",")
    if len(parts) != 4:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Bounding box must contain exactly 4 numbers: "
                "min_lon,min_lat,max_lon,max_lat"
            ),
        )

    try:
        min_lon, min_lat, max_lon, max_lat = map(float, parts)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Bounding box values must be valid floating-point numbers",
        ) from err

    if not (-180.0 <= min_lon <= 180.0 and -180.0 <= max_lon <= 180.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Longitude values in bounding box must be between -180 and 180",
        )

    if not (-90.0 <= min_lat <= 90.0 and -90.0 <= max_lat <= 90.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Latitude values in bounding box must be between -90 and 90",
        )

    if min_lon >= max_lon:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="min_lon must be strictly less than max_lon in bounding box",
        )

    if min_lat >= max_lat:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="min_lat must be strictly less than max_lat in bounding box",
        )

    return min_lon, min_lat, max_lon, max_lat


@router.get(
    "",
    response_model=FaultFeatureCollection,
    summary="List active fault lines in GeoJSON format",
    description=(
        "Retrieve geological fault segments as a standard RFC 7946 "
        "GeoJSON FeatureCollection. Supports optional viewport bounding box "
        "filtering (min_lon,min_lat,max_lon,max_lat) via GiST index, "
        "optional fault_type filtering, and bounded result limits."
    ),
)
def list_fault_lines(
    bbox: Annotated[
        str | None,
        Query(
            description="Viewport bbox: min_lon,min_lat,max_lon,max_lat",
            examples=["26.0,36.0,45.0,42.0"],
        ),
    ] = None,
    fault_type: Annotated[
        str | None,
        Query(
            description="Filter by normalized kinematic fault type (e.g. Dextral)",
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=2000,
            description="Max features to return (1-2000, default: 1000)",
        ),
    ] = 1000,
    db: Annotated[Session, Depends(get_db)] = None,
) -> FaultFeatureCollection:
    parsed_bbox = parse_bbox_param(bbox)
    service = FaultQueryService(db)
    return service.get_fault_lines(bbox=parsed_bbox, fault_type=fault_type, limit=limit)


@router.get(
    "/nearby",
    response_model=FaultFeatureCollection,
    summary="Query nearby fault lines by geographic proximity",
    description=(
        "Find geological fault segments within a required geodesic radius "
        "(in km) from a given WGS84 point. Calculates geodesic distance "
        "using PostGIS geography ST_DWithin and ST_Distance, returning "
        "features sorted by proximity with distance_km included."
    ),
)
def get_nearby_fault_lines(
    latitude: Annotated[
        float,
        Query(
            ge=-90.0,
            le=90.0,
            description="Query location latitude in WGS84 degrees (-90 to 90)",
            examples=[41.0082],
        ),
    ],
    longitude: Annotated[
        float,
        Query(
            ge=-180.0,
            le=180.0,
            description="Query location longitude in WGS84 degrees (-180 to 180)",
            examples=[28.9784],
        ),
    ],
    radius_km: Annotated[
        float,
        Query(
            gt=0.0,
            le=500.0,
            description="Search radius in kilometers (must be > 0 and <= 500 km)",
            examples=[50.0],
        ),
    ],
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Max nearby features to return (1-100, default: 20)",
        ),
    ] = 20,
    db: Annotated[Session, Depends(get_db)] = None,
) -> FaultFeatureCollection:
    service = FaultQueryService(db)
    return service.get_nearby_faults(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        limit=limit,
    )


@router.get(
    "/{fault_id}",
    response_model=FaultFeature,
    summary="Get a single fault line feature by UUID",
    description="Retrieve a single geological fault segment by AFET360 internal UUID.",
    responses={
        404: {
            "description": "Fault line with the specified UUID was not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Fault line with id '...' not found"}
                }
            },
        }
    },
)
def get_fault_line_by_id(
    fault_id: Annotated[
        uuid.UUID,
        Path(description="Unique AFET360 internal UUID of the fault segment"),
    ],
    db: Annotated[Session, Depends(get_db)] = None,
) -> FaultFeature:
    service = FaultQueryService(db)
    feature = service.get_fault_by_id(fault_id)
    if not feature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fault line with id '{fault_id}' not found",
        )
    return feature


@router.get(
    "/{fault_id}/earthquakes",
    response_model=EarthquakeFeatureCollection,
    summary="Get earthquakes near a mapped fault trace",
    description=(
        "Retrieve earthquake epicenters within a caller-specified geographic distance "
        "(max_distance_km) of this mapped fault trace from the locally synchronized "
        "AFAD snapshot. Mandatory note: spatial proximity does not establish that "
        "the earthquake ruptured on or was caused by this fault."
    ),
    responses={
        404: {
            "description": "Fault line with the specified UUID was not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Fault line with id '...' not found"}
                }
            },
        }
    },
)
def get_earthquakes_near_fault(
    fault_id: Annotated[
        uuid.UUID,
        Path(description="Unique AFET360 internal UUID of the target fault segment"),
    ],
    max_distance_km: Annotated[
        float,
        Query(
            description=(
                "Maximum geographic proximity radius in km "
                "(required, 0 < max_distance_km <= 500.0)"
            ),
            gt=0.0,
            le=500.0,
        ),
    ],
    db: Annotated[Session, Depends(get_db)],
    min_magnitude: Annotated[
        float,
        Query(
            description="Minimum magnitude threshold (default: 5.0)",
            ge=-2.0,
            le=10.0,
        ),
    ] = 5.0,
    start_time: Annotated[
        datetime | None,
        Query(
            description=(
                "Start timestamp filter (timezone-aware UTC, e.g. 2026-01-01T00:00:00Z)"
            ),
        ),
    ] = None,
    end_time: Annotated[
        datetime | None,
        Query(
            description=(
                "End timestamp filter (timezone-aware UTC, e.g. 2026-01-02T00:00:00Z)"
            ),
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            description="Maximum number of features to return (1-500, default: 100)",
            ge=1,
            le=500,
        ),
    ] = 100,
    offset: Annotated[
        int,
        Query(description="Pagination offset index (default: 0)", ge=0),
    ] = 0,
    order_by: Annotated[
        str,
        Query(
            description=(
                "Sort ordering: 'recent' (default, newest first) or 'distance' "
                "(closest first)"
            ),
            pattern="^(recent|distance)$",
        ),
    ] = "recent",
) -> EarthquakeFeatureCollection:
    """Retrieve earthquakes within max_distance_km of the specified fault trace."""
    validate_temporal_params(start_time, end_time)
    service = EarthquakeQueryService(db)
    result = service.list_earthquakes_near_fault(
        fault_id=fault_id,
        max_distance_km=max_distance_km,
        min_magnitude=min_magnitude,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
        order_by=order_by,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fault line with id '{fault_id}' not found",
        )
    return result
