"""Service layer orchestrating public read queries for emergency assembly areas."""

import json
import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.assembly_area_dataset import AssemblyAreaDataset
from app.repositories.assembly_area import AssemblyAreaRepository
from app.schemas.assembly_api import (
    DEFAULT_ASSEMBLY_ATTRIBUTION,
    DEFAULT_ASSEMBLY_CLASSIFICATION,
    DEFAULT_ASSEMBLY_DISCLAIMER,
    DEFAULT_ASSEMBLY_LICENSE,
    DEFAULT_ASSEMBLY_PROVIDER,
    DEFAULT_ASSEMBLY_SOURCE,
    DEFAULT_ASSEMBLY_SOURCE_REFERENCE,
    DEFAULT_LABEL_EN,
    DEFAULT_LABEL_TR,
    AssemblyAreaFeature,
    AssemblyAreaFeatureCollection,
    AssemblyAreaNearbyFeature,
    AssemblyAreaNearbyFeatureCollection,
    AssemblyAreaNearbyProperties,
    AssemblyAreaProperties,
    AssemblyCollectionMetadata,
    AssemblyDatasetResponse,
    GeoJSONPoint,
    GeoJSONPolygon,
)

logger = logging.getLogger(__name__)


def parse_geojson_geometry(geojson_str: str) -> GeoJSONPoint | GeoJSONPolygon:
    """Parse a PostGIS GeoJSON string into a Point or Polygon geometry schema."""
    data = json.loads(geojson_str)
    geom_type = data.get("type")
    if geom_type == "Point":
        return GeoJSONPoint(coordinates=data["coordinates"])
    elif geom_type == "Polygon":
        return GeoJSONPolygon(coordinates=data["coordinates"])
    else:
        raise ValueError(
            f"Unexpected geometry type '{geom_type}' in assembly area dataset. "
            "Only 'Point' and 'Polygon' are supported by the public API."
        )


class AssemblyQueryService:
    """Service providing read-only queries for emergency assembly areas."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = AssemblyAreaRepository(session)

    def get_active_dataset(self) -> AssemblyAreaDataset:
        """Resolve the active OpenStreetMap assembly dataset or raise HTTP 503."""
        dataset = self.repository.get_current_osm_dataset()
        if dataset is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Assembly area dataset is currently unavailable.",
            )
        return dataset

    def get_dataset_metadata(self) -> AssemblyDatasetResponse:
        """Retrieve comprehensive provenance, licensing, and geometry counts."""
        dataset = self.get_active_dataset()
        total_count, point_count, polygon_count = (
            self.repository.get_geometry_counts_for_dataset(dataset.id)
        )

        return AssemblyDatasetResponse(
            source=dataset.source or DEFAULT_ASSEMBLY_SOURCE,
            provider=dataset.provider or DEFAULT_ASSEMBLY_PROVIDER,
            source_classification=(
                dataset.source_classification or DEFAULT_ASSEMBLY_CLASSIFICATION
            ),
            license=dataset.license or DEFAULT_ASSEMBLY_LICENSE,
            attribution=dataset.attribution or DEFAULT_ASSEMBLY_ATTRIBUTION,
            source_reference=(
                dataset.source_reference or DEFAULT_ASSEMBLY_SOURCE_REFERENCE
            ),
            snapshot_retrieved_at=dataset.snapshot_retrieved_at,
            source_data_timestamp=dataset.source_data_timestamp,
            snapshot_sha256=dataset.snapshot_sha256,
            feature_count=total_count,
            point_count=point_count,
            polygon_count=polygon_count,
            label_en=DEFAULT_LABEL_EN,
            label_tr=DEFAULT_LABEL_TR,
            disclaimer=DEFAULT_ASSEMBLY_DISCLAIMER,
        )

    def get_collection(
        self,
        min_lon: float | None = None,
        min_lat: float | None = None,
        max_lon: float | None = None,
        max_lat: float | None = None,
        limit: int = 1000,
    ) -> AssemblyAreaFeatureCollection:
        """Return assembly area features as an RFC 7946 GeoJSON FeatureCollection."""
        dataset = self.get_active_dataset()
        raw_features, truncated = self.repository.get_collection(
            dataset_id=dataset.id,
            min_lon=min_lon,
            min_lat=min_lat,
            max_lon=max_lon,
            max_lat=max_lat,
            limit=limit,
        )

        features: list[AssemblyAreaFeature] = []
        for row in raw_features:
            geom = parse_geojson_geometry(row["geojson"])
            feature = AssemblyAreaFeature(
                id=row["id"],
                geometry=geom,
                properties=AssemblyAreaProperties(
                    source_feature_id=row["source_feature_id"],
                    name=row["name"],
                    ref=row["ref"],
                    operator=row["operator"],
                ),
            )
            features.append(feature)

        metadata = AssemblyCollectionMetadata(
            returned_count=len(features),
            truncated=truncated,
            source=dataset.source or DEFAULT_ASSEMBLY_SOURCE,
            provider=dataset.provider or DEFAULT_ASSEMBLY_PROVIDER,
            source_classification=(
                dataset.source_classification or DEFAULT_ASSEMBLY_CLASSIFICATION
            ),
            license=dataset.license or DEFAULT_ASSEMBLY_LICENSE,
            attribution=dataset.attribution or DEFAULT_ASSEMBLY_ATTRIBUTION,
            source_reference=(
                dataset.source_reference or DEFAULT_ASSEMBLY_SOURCE_REFERENCE
            ),
            snapshot_retrieved_at=dataset.snapshot_retrieved_at,
            source_data_timestamp=dataset.source_data_timestamp,
            snapshot_sha256=dataset.snapshot_sha256,
            disclaimer=DEFAULT_ASSEMBLY_DISCLAIMER,
        )

        return AssemblyAreaFeatureCollection(
            type="FeatureCollection",
            features=features,
            metadata=metadata,
        )

    def get_nearby(
        self,
        longitude: float,
        latitude: float,
        radius_km: float,
        limit: int = 20,
    ) -> AssemblyAreaNearbyFeatureCollection:
        """Find assembly areas within a geodesic radius sorted by exact distance."""
        dataset = self.get_active_dataset()
        raw_features, truncated = self.repository.get_nearby(
            dataset_id=dataset.id,
            longitude=longitude,
            latitude=latitude,
            radius_km=radius_km,
            limit=limit,
        )

        features: list[AssemblyAreaNearbyFeature] = []
        for row in raw_features:
            geom = parse_geojson_geometry(row["geojson"])
            # Format distance to 3 decimal places (meter-level precision)
            dist_km = round(row["distance_km"], 3)
            feature = AssemblyAreaNearbyFeature(
                id=row["id"],
                geometry=geom,
                properties=AssemblyAreaNearbyProperties(
                    source_feature_id=row["source_feature_id"],
                    name=row["name"],
                    ref=row["ref"],
                    operator=row["operator"],
                    distance_km=dist_km,
                ),
            )
            features.append(feature)

        metadata = AssemblyCollectionMetadata(
            returned_count=len(features),
            truncated=truncated,
            source=dataset.source or DEFAULT_ASSEMBLY_SOURCE,
            provider=dataset.provider or DEFAULT_ASSEMBLY_PROVIDER,
            source_classification=(
                dataset.source_classification or DEFAULT_ASSEMBLY_CLASSIFICATION
            ),
            license=dataset.license or DEFAULT_ASSEMBLY_LICENSE,
            attribution=dataset.attribution or DEFAULT_ASSEMBLY_ATTRIBUTION,
            source_reference=(
                dataset.source_reference or DEFAULT_ASSEMBLY_SOURCE_REFERENCE
            ),
            snapshot_retrieved_at=dataset.snapshot_retrieved_at,
            source_data_timestamp=dataset.source_data_timestamp,
            snapshot_sha256=dataset.snapshot_sha256,
            disclaimer=DEFAULT_ASSEMBLY_DISCLAIMER,
        )

        return AssemblyAreaNearbyFeatureCollection(
            type="FeatureCollection",
            features=features,
            metadata=metadata,
        )
