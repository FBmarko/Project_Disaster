import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.fault_segment import FaultSegment
from app.repositories.fault_segment import FaultSegmentRepository
from app.schemas.fault_line_api import (
    DEFAULT_FAULT_ATTRIBUTION,
    DEFAULT_FAULT_DISCLAIMER,
    DEFAULT_FAULT_LICENSE,
    DEFAULT_FAULT_SOURCE,
    FaultAttributionMetadata,
    FaultFeature,
    FaultFeatureCollection,
    FaultFeatureProperties,
    GeoJSONMultiLineStringGeometry,
)


def _row_to_feature(
    segment: FaultSegment,
    geojson_str: str,
    distance_km: float | None = None,
    include_metadata: bool = False,
) -> FaultFeature:
    """Transform a FaultSegment and GeoJSON string into a public FaultFeature."""
    geom_dict: dict[str, Any] = json.loads(geojson_str)

    geometry = GeoJSONMultiLineStringGeometry(
        type="MultiLineString",
        coordinates=geom_dict.get("coordinates", []),
    )

    properties = FaultFeatureProperties(
        id=segment.id,
        source=segment.source,
        source_feature_id=segment.source_feature_id,
        name=segment.name,
        segment_name=segment.segment_name,
        fault_type=segment.fault_type,
        activity_status=segment.activity_status,
        distance_km=round(distance_km, 3) if distance_km is not None else None,
    )

    metadata = (
        FaultAttributionMetadata(
            count=1,
            source=DEFAULT_FAULT_SOURCE,
            license=DEFAULT_FAULT_LICENSE,
            attribution=DEFAULT_FAULT_ATTRIBUTION,
            disclaimer=DEFAULT_FAULT_DISCLAIMER,
        )
        if include_metadata
        else None
    )

    return FaultFeature(
        type="Feature",
        id=segment.id,
        geometry=geometry,
        properties=properties,
        metadata=metadata,
    )


class FaultQueryService:
    """Service for querying and transforming fault segments into GeoJSON."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = FaultSegmentRepository(session)

    def get_fault_lines(
        self,
        bbox: tuple[float, float, float, float] | None = None,
        fault_type: str | None = None,
        limit: int = 1000,
    ) -> FaultFeatureCollection:
        """Query fault features matching optional bounding box and fault filters."""
        rows = self.repository.list_faults(
            bbox=bbox, fault_type=fault_type, limit=limit
        )

        features = [_row_to_feature(seg, geo_str) for seg, geo_str in rows]

        metadata = FaultAttributionMetadata(
            count=len(features),
            source=DEFAULT_FAULT_SOURCE,
            license=DEFAULT_FAULT_LICENSE,
            attribution=DEFAULT_FAULT_ATTRIBUTION,
            disclaimer=DEFAULT_FAULT_DISCLAIMER,
        )

        return FaultFeatureCollection(
            type="FeatureCollection",
            features=features,
            metadata=metadata,
        )

    def get_nearby_faults(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
        limit: int = 20,
    ) -> FaultFeatureCollection:
        """Find active faults in geographic proximity ordered by ascending distance."""
        rows = self.repository.find_nearby(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            limit=limit,
        )

        features = [
            _row_to_feature(seg, geo_str, distance_km=dist)
            for seg, geo_str, dist in rows
        ]

        metadata = FaultAttributionMetadata(
            count=len(features),
            source=DEFAULT_FAULT_SOURCE,
            license=DEFAULT_FAULT_LICENSE,
            attribution=DEFAULT_FAULT_ATTRIBUTION,
            disclaimer=DEFAULT_FAULT_DISCLAIMER,
        )

        return FaultFeatureCollection(
            type="FeatureCollection",
            features=features,
            metadata=metadata,
        )

    def get_fault_by_id(self, fault_id: uuid.UUID) -> FaultFeature | None:
        """Fetch single fault feature by UUID with attribution metadata."""
        row = self.repository.get_by_id_with_geojson(fault_id)
        if not row:
            return None
        seg, geo_str = row
        return _row_to_feature(seg, geo_str, include_metadata=True)
