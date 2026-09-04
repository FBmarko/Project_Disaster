"""Public GeoJSON schemas, metadata, and scientific disclaimers for Hazard API."""

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Centralized Scientific Disclaimers & Provenance Constants
DEFAULT_HAZARD_SOURCE = (
    "GEM Global Seismic Hazard Map (v2026.1), Global Earthquake Model Foundation"
)
DEFAULT_HAZARD_LICENSE = "CC BY-NC-SA 4.0"
DEFAULT_HAZARD_ATTRIBUTION = (
    "Global Seismic Hazard Map (v2026.1), Global Earthquake Model (GEM) Foundation. "
    "Distributed under CC BY-NC-SA 4.0."
)
DEFAULT_HAZARD_DISCLAIMER = (
    "This value is the modeled Peak Ground Acceleration (PGA) at the nearest "
    "discrete GEM source node, not an exact site-specific ground-motion "
    "calculation. Local soil and site amplification are not represented; the "
    "source model uses reference rock Vs30 = 800 m/s (10% probability of "
    "exceedance in 50 years / approximately 475-year return period). Not "
    "official regulatory Turkish hazard (TDTH) or building safety assessment."
)
DEFAULT_HAZARD_BBOX_DISCLAIMER = (
    "Earthquake hazard points represent discrete GEM GSHM v2026.1 grid nodes for "
    "reference rock conditions (Vs30 = 800 m/s, 10% in 50 years). Not local "
    "soil amplification or regulatory building safety design values."
)
DEFAULT_HAZARD_DATA_DELIVERY = "local_imported_reference_dataset"


class HazardPointGeometry(BaseModel):
    """RFC 7946 GeoJSON Point geometry in EPSG:4326 [longitude, latitude]."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["Point"] = "Point"
    coordinates: list[float] = Field(
        ...,
        description="WGS84 coordinates of the GEM source node: [longitude, latitude]",
        min_length=2,
        max_length=2,
    )


class ScopeBounds(BaseModel):
    """Geographic bounding box defining the imported dataset coverage."""

    model_config = ConfigDict(extra="forbid")

    min_longitude: float
    min_latitude: float
    max_longitude: float
    max_latitude: float


class HazardDatasetMetadataResponse(BaseModel):
    """Comprehensive dataset provenance and scientific metadata."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    source: str = Field(..., description="Hazard dataset provider/model source")
    source_version: str = Field(..., description="Dataset model version")
    model_name: str = Field(..., description="Full descriptive model title")
    hazard_metric: str = Field(..., description="Seismic hazard metric (e.g. PGA)")
    unit: str = Field(..., description="Physical unit of the hazard metric (e.g. g)")
    return_period_years: int = Field(..., description="Nominal return period in years")
    exceedance_probability: float = Field(
        ..., description="Probability of exceedance within time horizon"
    )
    time_horizon_years: int = Field(..., description="Time horizon in years")
    reference_vs30_mps: float = Field(
        ..., description="Reference shear-wave velocity in m/s"
    )
    reference_ground: str = Field(
        ..., description="Reference ground/rock classification"
    )
    version_doi: str = Field(..., description="Version-specific Zenodo DOI")
    concept_doi: str = Field(..., description="Concept/family Zenodo DOI")
    license: str = Field(..., description="Dataset distribution license")
    attribution: str = Field(..., description="Official required attribution string")
    ingest_scope: str = Field(..., description="Regional ingestion scope identifier")
    scope: ScopeBounds = Field(..., description="Imported geographic scope bounds")
    point_count: int = Field(
        ..., description="Total persisted hazard grid nodes in dataset"
    )
    data_delivery: str = Field(
        default=DEFAULT_HAZARD_DATA_DELIVERY,
        description="Data delivery classification",
    )
    source_artifact: str = Field(
        ..., description="Upstream archive filename for reproducibility"
    )
    source_checksum_algorithm: str = Field(
        ..., description="Checksum algorithm used for archive verification"
    )
    source_checksum_value: str = Field(
        ..., description="Verified cryptographic checksum of source archive"
    )


class QueryCoordinates(BaseModel):
    """User-requested query coordinates."""

    model_config = ConfigDict(extra="forbid")

    longitude: float = Field(..., description="Requested longitude in EPSG:4326")
    latitude: float = Field(..., description="Requested latitude in EPSG:4326")


class HazardNearestMetadata(BaseModel):
    """Compact provenance and scientific disclaimers for nearest-node lookup."""

    model_config = ConfigDict(extra="forbid")

    query: QueryCoordinates = Field(..., description="Requested geographic coordinate")
    source: str = Field(default="GEM_GSHM")
    source_version: str = Field(default="2026.1")
    hazard_metric: str = Field(default="PGA")
    unit: str = Field(default="g")
    return_period_years: int = Field(default=475)
    reference_vs30_mps: float = Field(default=800.0)
    version_doi: str = Field(default="10.5281/zenodo.20735384")
    license: str = Field(default=DEFAULT_HAZARD_LICENSE)
    attribution: str = Field(default=DEFAULT_HAZARD_ATTRIBUTION)
    disclaimer: str = Field(default=DEFAULT_HAZARD_DISCLAIMER)


class HazardNearestFeatureProperties(BaseModel):
    """Properties describing the nearest modeled source node."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID = Field(..., description="Unique AFET360 hazard point UUID")
    source_record_id: int | None = Field(
        None, description="Upstream GEM source feature FID"
    )
    pga_g: float = Field(
        ..., description="Modeled Peak Ground Acceleration in g at source node"
    )
    distance_to_source_node_km: float = Field(
        ..., description="Exact geodesic distance from query coordinate in km"
    )
    semantics: Literal["nearest_source_node"] = Field(
        default="nearest_source_node",
        description="Explicit semantic classification of returned value",
    )


class HazardNearestFeature(BaseModel):
    """GeoJSON Feature representing the nearest GEM source node to a coordinate."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["Feature"] = "Feature"
    geometry: HazardPointGeometry = Field(
        ..., description="Point geometry of the GEM source node"
    )
    properties: HazardNearestFeatureProperties
    metadata: HazardNearestMetadata


class HazardPointProperties(BaseModel):
    """Properties for a discrete hazard point in a viewport/bbox response."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID = Field(..., description="Unique AFET360 hazard point UUID")
    pga_g: float = Field(
        ..., description="Modeled Peak Ground Acceleration in decimal g"
    )
    source_record_id: int | None = Field(
        None, description="Upstream source feature FID"
    )


class HazardPointFeature(BaseModel):
    """GeoJSON Feature for a discrete seismic hazard grid node."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["Feature"] = "Feature"
    geometry: HazardPointGeometry
    properties: HazardPointProperties


class HazardFeatureCollectionMetadata(BaseModel):
    """Metadata block accompanying viewport/bbox hazard point collections."""

    model_config = ConfigDict(extra="forbid")

    count: int = Field(..., description="Number of hazard features returned")
    bbox: list[float] = Field(
        ..., description="Requested bounding box [min_lon, min_lat, max_lon, max_lat]"
    )
    limit: int = Field(..., description="Pagination limit applied")
    offset: int = Field(..., description="Pagination offset applied")
    has_more: bool = Field(
        ..., description="Whether additional features exist matching bbox"
    )
    source: str = Field(default="GEM_GSHM")
    source_version: str = Field(default="2026.1")
    hazard_metric: str = Field(default="PGA")
    unit: str = Field(default="g")
    return_period_years: int = Field(default=475)
    reference_vs30_mps: float = Field(default=800.0)
    version_doi: str = Field(default="10.5281/zenodo.20735384")
    license: str = Field(default=DEFAULT_HAZARD_LICENSE)
    attribution: str = Field(default=DEFAULT_HAZARD_ATTRIBUTION)
    disclaimer: str = Field(default=DEFAULT_HAZARD_BBOX_DISCLAIMER)


class HazardFeatureCollection(BaseModel):
    """RFC 7946 GeoJSON FeatureCollection of discrete hazard grid nodes."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[HazardPointFeature] = Field(default_factory=list)
    metadata: HazardFeatureCollectionMetadata
