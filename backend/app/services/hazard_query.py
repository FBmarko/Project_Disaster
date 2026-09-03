"""Service layer orchestrating public queries for GEM seismic hazard data."""

import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.integrations.gem.hazard_constants import TURKEY_CONTEXT_BBOX
from app.models.hazard_dataset import HazardDataset
from app.repositories.earthquake_hazard import EarthquakeHazardRepository
from app.schemas.hazard_api import (
    DEFAULT_HAZARD_BBOX_DISCLAIMER,
    DEFAULT_HAZARD_DATA_DELIVERY,
    DEFAULT_HAZARD_DISCLAIMER,
    HazardDatasetMetadataResponse,
    HazardFeatureCollection,
    HazardFeatureCollectionMetadata,
    HazardNearestFeature,
    HazardNearestFeatureProperties,
    HazardNearestMetadata,
    HazardPointFeature,
    HazardPointGeometry,
    HazardPointProperties,
    QueryCoordinates,
    ScopeBounds,
)

logger = logging.getLogger(__name__)

MIN_LON_SCOPE, MIN_LAT_SCOPE, MAX_LON_SCOPE, MAX_LAT_SCOPE = TURKEY_CONTEXT_BBOX


class HazardQueryService:
    """Service providing read-only queries for seismic hazard data."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = EarthquakeHazardRepository(session)

    def get_active_dataset(self) -> HazardDataset:
        """Resolve active imported GEM GSHM dataset or raise HTTP 503."""
        dataset = self.repository.get_active_gem_dataset()
        if dataset is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Earthquake hazard dataset is currently unavailable.",
            )
        return dataset

    def get_dataset_metadata(self) -> HazardDatasetMetadataResponse:
        """Fetch active dataset metadata with current persisted point count."""
        dataset = self.get_active_dataset()
        point_count = self.repository.count_points_for_dataset(dataset.id)

        scope = ScopeBounds(
            min_longitude=dataset.scope_min_longitude,
            min_latitude=dataset.scope_min_latitude,
            max_longitude=dataset.scope_max_longitude,
            max_latitude=dataset.scope_max_latitude,
        )

        return HazardDatasetMetadataResponse(
            source=dataset.source,
            source_version=dataset.source_version,
            model_name=dataset.model_name,
            hazard_metric=dataset.hazard_metric,
            unit=dataset.unit,
            return_period_years=dataset.return_period_years,
            exceedance_probability=dataset.exceedance_probability,
            time_horizon_years=dataset.time_horizon_years,
            reference_vs30_mps=dataset.reference_vs30_mps,
            reference_ground=dataset.reference_ground,
            version_doi=dataset.version_doi,
            concept_doi=dataset.concept_doi,
            license=dataset.license,
            attribution=dataset.attribution,
            ingest_scope=dataset.ingest_scope,
            scope=scope,
            point_count=point_count,
            data_delivery=DEFAULT_HAZARD_DATA_DELIVERY,
            source_artifact=dataset.source_artifact,
            source_checksum_algorithm=dataset.source_checksum_algorithm,
            source_checksum_value=dataset.source_checksum_value,
        )

    def validate_coordinate(self, longitude: float, latitude: float) -> None:
        """Validate that coordinate is valid WGS84 and within Türkiye scope."""
        if not (-180.0 <= longitude <= 180.0):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Longitude must be between -180.0 and 180.0 degrees.",
            )
        if not (-90.0 <= latitude <= 90.0):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Latitude must be between -90.0 and 90.0 degrees.",
            )

        if not (
            MIN_LON_SCOPE <= longitude <= MAX_LON_SCOPE
            and MIN_LAT_SCOPE <= latitude <= MAX_LAT_SCOPE
        ):
            err_msg = (
                f"Requested coordinate ({longitude}, {latitude}) is outside "
                f"imported AFET360 GEM Türkiye-context coverage "
                f"[{MIN_LON_SCOPE}..{MAX_LON_SCOPE}°E, "
                f"{MIN_LAT_SCOPE}..{MAX_LAT_SCOPE}°N]."
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=err_msg,
            )

    def get_nearest_hazard_point(
        self, longitude: float, latitude: float
    ) -> HazardNearestFeature:
        """Find nearest GEM source node and exact geodesic distance in km."""
        self.validate_coordinate(longitude, latitude)
        dataset = self.get_active_dataset()

        nearest_row = self.repository.find_nearest_hazard_point(
            dataset.id, longitude, latitude, candidate_count=32
        )
        if nearest_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No seismic hazard point found in dataset.",
            )

        geom = HazardPointGeometry(
            coordinates=[nearest_row["longitude"], nearest_row["latitude"]]
        )
        props = HazardNearestFeatureProperties(
            id=nearest_row["id"],
            source_record_id=nearest_row["source_record_id"],
            pga_g=nearest_row["pga_g"],
            distance_to_source_node_km=nearest_row["distance_km"],
            semantics="nearest_source_node",
        )
        metadata = HazardNearestMetadata(
            query=QueryCoordinates(longitude=longitude, latitude=latitude),
            source=dataset.source,
            source_version=dataset.source_version,
            hazard_metric=dataset.hazard_metric,
            unit=dataset.unit,
            return_period_years=dataset.return_period_years,
            reference_vs30_mps=dataset.reference_vs30_mps,
            version_doi=dataset.version_doi,
            license=dataset.license,
            attribution=dataset.attribution,
            disclaimer=DEFAULT_HAZARD_DISCLAIMER,
        )

        return HazardNearestFeature(
            geometry=geom,
            properties=props,
            metadata=metadata,
        )

    def validate_and_parse_bbox(
        self, bbox_str: str | None
    ) -> tuple[float, float, float, float]:
        """Validate and parse bounding box parameter."""
        if not bbox_str:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "bbox query parameter is required: min_lon,min_lat,max_lon,max_lat"
                ),
            )

        parts = bbox_str.split(",")
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
                detail="Bounding box values must be valid floating-point numbers.",
            ) from err

        if not (-180.0 <= min_lon <= 180.0 and -180.0 <= max_lon <= 180.0):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Longitude values in bbox must be between -180 and 180.",
            )
        if not (-90.0 <= min_lat <= 90.0 and -90.0 <= max_lat <= 90.0):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Latitude values in bbox must be between -90 and 90.",
            )

        if min_lon >= max_lon:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="min_lon must be strictly less than max_lon in bbox.",
            )
        if min_lat >= max_lat:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="min_lat must be strictly less than max_lat in bbox.",
            )

        # Ensure entire bbox is inside imported dataset scope
        if not (
            MIN_LON_SCOPE <= min_lon <= MAX_LON_SCOPE
            and MIN_LON_SCOPE <= max_lon <= MAX_LON_SCOPE
            and MIN_LAT_SCOPE <= min_lat <= MAX_LAT_SCOPE
            and MIN_LAT_SCOPE <= max_lat <= MAX_LAT_SCOPE
        ):
            err_msg = (
                f"Requested bounding box is outside imported AFET360 GEM "
                f"Türkiye-context coverage [{MIN_LON_SCOPE}..{MAX_LON_SCOPE}°E, "
                f"{MIN_LAT_SCOPE}..{MAX_LAT_SCOPE}°N]."
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=err_msg,
            )

        return min_lon, min_lat, max_lon, max_lat

    def get_hazard_points_in_bbox(
        self, bbox_str: str, limit: int = 1000, offset: int = 0
    ) -> HazardFeatureCollection:
        """Fetch discrete hazard grid nodes within a bounding box."""
        min_lon, min_lat, max_lon, max_lat = self.validate_and_parse_bbox(bbox_str)

        if not (1 <= limit <= 2000):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Limit must be an integer between 1 and 2000.",
            )
        if offset < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Offset must be a non-negative integer.",
            )

        dataset = self.get_active_dataset()
        rows, has_more = self.repository.list_hazard_points_in_bbox(
            dataset.id,
            min_lon,
            min_lat,
            max_lon,
            max_lat,
            limit=limit,
            offset=offset,
        )

        features = [
            HazardPointFeature(
                geometry=HazardPointGeometry(
                    coordinates=[r["longitude"], r["latitude"]]
                ),
                properties=HazardPointProperties(
                    id=r["id"],
                    pga_g=r["pga_g"],
                    source_record_id=r["source_record_id"],
                ),
            )
            for r in rows
        ]

        metadata = HazardFeatureCollectionMetadata(
            count=len(features),
            bbox=[min_lon, min_lat, max_lon, max_lat],
            limit=limit,
            offset=offset,
            has_more=has_more,
            source=dataset.source,
            source_version=dataset.source_version,
            hazard_metric=dataset.hazard_metric,
            unit=dataset.unit,
            return_period_years=dataset.return_period_years,
            reference_vs30_mps=dataset.reference_vs30_mps,
            version_doi=dataset.version_doi,
            license=dataset.license,
            attribution=dataset.attribution,
            disclaimer=DEFAULT_HAZARD_BBOX_DISCLAIMER,
        )

        return HazardFeatureCollection(
            features=features,
            metadata=metadata,
        )
