"""Public read-only REST endpoints for earthquakes."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.earthquake_api import (
    EarthquakeFeature,
    EarthquakeFeatureCollection,
)
from app.services.earthquake_query import EarthquakeQueryService

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


def validate_temporal_params(
    start_time: datetime | None,
    end_time: datetime | None,
) -> None:
    """Validate temporal filters for timezone-awareness and valid ordering."""
    if start_time is not None and start_time.tzinfo is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "start_time must be a timezone-aware ISO-8601 string "
                "(e.g. '2026-01-01T00:00:00Z')"
            ),
        )

    if end_time is not None and end_time.tzinfo is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "end_time must be a timezone-aware ISO-8601 string "
                "(e.g. '2026-01-02T00:00:00Z')"
            ),
        )

    if start_time is not None and end_time is not None and start_time > end_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_time must be earlier than or equal to end_time",
        )


@router.get(
    "",
    response_model=EarthquakeFeatureCollection,
    summary="List earthquakes",
    description=(
        "Retrieve a GeoJSON FeatureCollection of seismic events from the locally "
        "synchronized AFAD snapshot. Supports magnitude, bounding box, and temporal "
        "filtering with default ordering by occurred_at DESC."
    ),
)
def get_earthquakes(
    db: Annotated[Session, Depends(get_db)],
    min_magnitude: Annotated[
        float | None,
        Query(
            description="Minimum magnitude filter threshold",
            ge=-2.0,
            le=10.0,
        ),
    ] = None,
    max_magnitude: Annotated[
        float | None,
        Query(
            description="Maximum magnitude filter threshold",
            ge=-2.0,
            le=10.0,
        ),
    ] = None,
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
    magnitude_type: Annotated[
        str | None,
        Query(
            description="Magnitude scale filter (e.g. MW, ML, MD)",
            max_length=20,
        ),
    ] = None,
    bbox: Annotated[
        str | None,
        Query(
            description=(
                "Spatial bounding box filter formatted as: "
                "min_lon,min_lat,max_lon,max_lat (e.g. '28.0,40.0,30.0,41.5')"
            ),
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            description="Maximum number of features to return (1-1000, default: 100)",
            ge=1,
            le=1000,
        ),
    ] = 100,
    offset: Annotated[
        int,
        Query(description="Pagination offset index (default: 0)", ge=0),
    ] = 0,
) -> EarthquakeFeatureCollection:
    """List earthquake features matching optional query filters."""
    if (
        min_magnitude is not None
        and max_magnitude is not None
        and min_magnitude > max_magnitude
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="min_magnitude must be less than or equal to max_magnitude",
        )

    validate_temporal_params(start_time, end_time)
    parsed_bbox = parse_bbox_param(bbox)

    service = EarthquakeQueryService(db)
    return service.list_earthquakes(
        min_magnitude=min_magnitude,
        max_magnitude=max_magnitude,
        start_time=start_time,
        end_time=end_time,
        magnitude_type=magnitude_type,
        bbox=parsed_bbox,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/recent-major",
    response_model=EarthquakeFeatureCollection,
    summary="List recent major earthquakes",
    description=(
        "Retrieve recent major earthquakes (default: M>=5.0, past 365 days) from the "
        "locally synchronized AFAD snapshot. Supports an optional max_distance_km "
        "filter to find events geographically proximate to mapped active faults. "
        "Note: spatial proximity does not establish geological causality."
    ),
)
def get_recent_major_earthquakes(
    db: Annotated[Session, Depends(get_db)],
    days: Annotated[
        int,
        Query(
            description="Recency window in days (1-3650, default: 365)",
            ge=1,
            le=3650,
        ),
    ] = 365,
    min_magnitude: Annotated[
        float,
        Query(
            description="Minimum magnitude threshold (default: 5.0)",
            ge=0.0,
            le=10.0,
        ),
    ] = 5.0,
    max_distance_km: Annotated[
        float | None,
        Query(
            description=(
                "Optional maximum geographic distance to nearest mapped fault in km "
                "(0 < max_distance_km <= 500.0)"
            ),
            gt=0.0,
            le=500.0,
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
) -> EarthquakeFeatureCollection:
    """Retrieve recent major earthquakes with optional fault proximity enrichment."""
    service = EarthquakeQueryService(db)
    return service.list_recent_major(
        days=days,
        min_magnitude=min_magnitude,
        max_distance_km=max_distance_km,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{event_id}",
    response_model=EarthquakeFeature,
    summary="Get single earthquake detail",
    description=(
        "Fetch a single earthquake feature by its unique AFET360 internal UUID. "
        "Returns GeoJSON Feature geometry and normalized attributes with AFAD "
        "attribution."
    ),
)
def get_single_earthquake(
    event_id: Annotated[
        uuid.UUID,
        Path(description="AFET360 internal UUID of the earthquake event"),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> EarthquakeFeature:
    """Fetch a single earthquake GeoJSON feature by UUID."""
    service = EarthquakeQueryService(db)
    feature = service.get_earthquake_by_id(event_id)
    if not feature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Earthquake event with ID '{event_id}' not found",
        )
    return feature
