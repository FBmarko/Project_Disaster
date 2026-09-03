"""Query service for reading and transforming Earthquake entities into GeoJSON."""

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.earthquake_event import EarthquakeEventRepository
from app.repositories.fault_segment import FaultSegmentRepository
from app.schemas.earthquake_api import (
    ASSOCIATION_METHOD_SPATIAL_PROXIMITY,
    DEFAULT_AFAD_ATTRIBUTION,
    DEFAULT_AFAD_DATASET,
    DEFAULT_AFAD_DISCLAIMER,
    DEFAULT_AFAD_SOURCE,
    DEFAULT_DATA_DELIVERY,
    DEFAULT_FAULT_ATTRIBUTION,
    DEFAULT_FAULT_LICENSE,
    DEFAULT_FAULT_SOURCE,
    SCIENTIFIC_PROXIMITY_DISCLAIMER,
    EarthquakeApiMetadata,
    EarthquakeFeature,
    EarthquakeFeatureCollection,
    EarthquakeFeatureProperties,
    EarthquakePointGeometry,
)


def _row_to_feature(
    row: dict[str, Any],
    include_proximity: bool = False,
    include_metadata: bool = False,
) -> EarthquakeFeature:
    """Transform an earthquake database mapping into a public GeoJSON Feature."""
    geom_data = json.loads(row["geojson"])
    geometry = EarthquakePointGeometry(
        type="Point",
        coordinates=geom_data.get("coordinates", [0.0, 0.0]),
    )

    dist_km = row.get("distance_to_fault_km")
    if dist_km is not None:
        dist_km = round(dist_km, 3)

    nearest_fault_id = row.get("nearest_fault_id")
    nearest_fault_source_feature_id = row.get("nearest_fault_source_feature_id")

    association_method = (
        ASSOCIATION_METHOD_SPATIAL_PROXIMITY
        if (include_proximity and dist_km is not None)
        else None
    )
    proximity_disclaimer = (
        SCIENTIFIC_PROXIMITY_DISCLAIMER
        if (include_proximity and dist_km is not None)
        else None
    )

    properties = EarthquakeFeatureProperties(
        id=row["id"],
        source=row["source"],
        source_event_id=row["source_event_id"],
        occurred_at=row["occurred_at"],
        depth_km=round(row["depth_km"], 2),
        magnitude=round(row["magnitude"], 2),
        magnitude_type=row["magnitude_type"],
        location_name=row.get("location_name"),
        country=row.get("country"),
        province=row.get("province"),
        district=row.get("district"),
        neighborhood=row.get("neighborhood"),
        distance_to_fault_km=dist_km if include_proximity else None,
        nearest_fault_id=nearest_fault_id if include_proximity else None,
        nearest_fault_source_feature_id=(
            nearest_fault_source_feature_id if include_proximity else None
        ),
        association_method=association_method,
        proximity_disclaimer=proximity_disclaimer,
    )

    metadata = None
    if include_metadata:
        metadata = EarthquakeApiMetadata(
            count=1,
            source=DEFAULT_AFAD_SOURCE,
            dataset=DEFAULT_AFAD_DATASET,
            attribution=DEFAULT_AFAD_ATTRIBUTION,
            disclaimer=DEFAULT_AFAD_DISCLAIMER,
            data_delivery=DEFAULT_DATA_DELIVERY,
        )

    return EarthquakeFeature(
        type="Feature",
        id=row["id"],
        geometry=geometry,
        properties=properties,
        metadata=metadata,
    )


class EarthquakeQueryService:
    """Service coordinating public earthquake queries and GeoJSON formatting."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = EarthquakeEventRepository(session)
        self.fault_repo = FaultSegmentRepository(session)

    def get_earthquake_by_id(self, event_id: uuid.UUID) -> EarthquakeFeature | None:
        """Retrieve a single earthquake event by its unique AFET360 UUID."""
        row = self.repo.get_by_id_with_geojson(event_id)
        if not row:
            return None
        return _row_to_feature(row, include_metadata=True)

    def list_earthquakes(
        self,
        min_magnitude: float | None = None,
        max_magnitude: float | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        magnitude_type: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> EarthquakeFeatureCollection:
        """Query earthquakes with spatial, temporal, and magnitude filtering."""
        rows = self.repo.list_events(
            min_magnitude=min_magnitude,
            max_magnitude=max_magnitude,
            start_time=start_time,
            end_time=end_time,
            magnitude_type=magnitude_type,
            bbox=bbox,
            limit=limit,
            offset=offset,
        )

        features = [_row_to_feature(r) for r in rows]
        metadata = EarthquakeApiMetadata(
            count=len(features),
            source=DEFAULT_AFAD_SOURCE,
            dataset=DEFAULT_AFAD_DATASET,
            attribution=DEFAULT_AFAD_ATTRIBUTION,
            disclaimer=DEFAULT_AFAD_DISCLAIMER,
            data_delivery=DEFAULT_DATA_DELIVERY,
        )
        return EarthquakeFeatureCollection(
            type="FeatureCollection",
            metadata=metadata,
            features=features,
        )

    def list_recent_major(
        self,
        days: int = 365,
        min_magnitude: float = 5.0,
        max_distance_km: float | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> EarthquakeFeatureCollection:
        """Query recent major earthquakes, optionally filtered near faults."""
        since = datetime.now(UTC) - timedelta(days=days)
        rows = self.repo.list_recent_major(
            since=since,
            min_magnitude=min_magnitude,
            max_distance_km=max_distance_km,
            limit=limit,
            offset=offset,
        )

        include_proximity = max_distance_km is not None
        features = [
            _row_to_feature(r, include_proximity=include_proximity) for r in rows
        ]

        metadata = EarthquakeApiMetadata(
            count=len(features),
            source=DEFAULT_AFAD_SOURCE,
            dataset=DEFAULT_AFAD_DATASET,
            attribution=DEFAULT_AFAD_ATTRIBUTION,
            disclaimer=DEFAULT_AFAD_DISCLAIMER,
            data_delivery=DEFAULT_DATA_DELIVERY,
            max_distance_km=max_distance_km,
            fault_attribution=DEFAULT_FAULT_ATTRIBUTION if include_proximity else None,
            fault_license=DEFAULT_FAULT_LICENSE if include_proximity else None,
            scientific_disclaimer=(
                SCIENTIFIC_PROXIMITY_DISCLAIMER if include_proximity else None
            ),
        )
        return EarthquakeFeatureCollection(
            type="FeatureCollection",
            metadata=metadata,
            features=features,
        )

    def list_earthquakes_near_fault(
        self,
        fault_id: uuid.UUID,
        max_distance_km: float,
        min_magnitude: float = 5.0,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "recent",
    ) -> EarthquakeFeatureCollection | None:
        """Query earthquakes within max_distance_km of a specific mapped fault trace."""
        fault = self.fault_repo.get_by_id(fault_id)
        if not fault:
            return None

        rows = self.repo.list_near_fault(
            fault_id=fault_id,
            max_distance_km=max_distance_km,
            min_magnitude=min_magnitude,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
            order_by=order_by,
        )

        # Populate nearest fault identity for each matched earthquake
        for r in rows:
            r["nearest_fault_id"] = fault.id
            r["nearest_fault_source_feature_id"] = fault.source_feature_id

        features = [_row_to_feature(r, include_proximity=True) for r in rows]

        metadata = EarthquakeApiMetadata(
            count=len(features),
            source=DEFAULT_AFAD_SOURCE,
            dataset=DEFAULT_AFAD_DATASET,
            attribution=DEFAULT_AFAD_ATTRIBUTION,
            disclaimer=DEFAULT_AFAD_DISCLAIMER,
            data_delivery=DEFAULT_DATA_DELIVERY,
            fault_id=fault.id,
            fault_source=DEFAULT_FAULT_SOURCE,
            fault_source_feature_id=fault.source_feature_id,
            max_distance_km=max_distance_km,
            fault_attribution=DEFAULT_FAULT_ATTRIBUTION,
            fault_license=DEFAULT_FAULT_LICENSE,
            scientific_disclaimer=SCIENTIFIC_PROXIMITY_DISCLAIMER,
        )
        return EarthquakeFeatureCollection(
            type="FeatureCollection",
            metadata=metadata,
            features=features,
        )
