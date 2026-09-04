import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Centralized attribution metadata for GEM GAF dataset
DEFAULT_FAULT_SOURCE = "GEM Global Active Faults Database (GAF-DB)"
DEFAULT_FAULT_LICENSE = "CC BY-SA 4.0"
DEFAULT_FAULT_ATTRIBUTION = (
    "Global Earthquake Model (GEM) Foundation (Styron & Pagani, 2020)"
)
DEFAULT_FAULT_DISCLAIMER = (
    "Development/staging dataset based on GEM GAF features intersecting the "
    "Natural Earth 1:50m generalized Türkiye polygon. "
    "Not official Turkish government / MTA fault data."
)


class GeoJSONMultiLineStringGeometry(BaseModel):
    """GeoJSON MultiLineString geometry object following RFC 7946."""

    type: Literal["MultiLineString"] = "MultiLineString"
    coordinates: list[list[list[float]]] = Field(
        ...,
        description="MultiLineString coordinates: [[[lon, lat], ...], ...]",
        examples=[[[[28.97, 41.01], [29.05, 41.05]]]],
    )


class FaultFeatureProperties(BaseModel):
    """Normalized public properties for a fault segment feature."""

    id: uuid.UUID = Field(..., description="Unique AFET360 internal UUID")
    source: str = Field(..., description="Dataset source identifier (e.g. GEM_GAF)")
    source_feature_id: str = Field(
        ..., description="Stable feature identifier from source catalog"
    )
    name: str | None = Field(
        default=None, description="Fault system or fault zone name if known"
    )
    segment_name: str | None = Field(
        default=None, description="Specific fault segment name if known"
    )
    fault_type: str | None = Field(
        default=None,
        description="Kinematic slip classification (e.g. Dextral, Normal)",
    )
    activity_status: str | None = Field(
        default=None, description="Activity status classification if verified"
    )
    distance_km: float | None = Field(
        default=None,
        description="Geodesic distance in km from query point (nearby queries)",
    )

    model_config = ConfigDict(from_attributes=True)


class FaultAttributionMetadata(BaseModel):
    """Attribution and provenance metadata for fault line responses."""

    count: int = Field(..., description="Number of features returned in this response")
    source: str = Field(
        default=DEFAULT_FAULT_SOURCE,
        description="Dataset source name",
    )
    license: str = Field(
        default=DEFAULT_FAULT_LICENSE,
        description="Dataset distribution license",
    )
    attribution: str = Field(
        default=DEFAULT_FAULT_ATTRIBUTION,
        description="Scientific citation and attribution requirements",
    )
    disclaimer: str = Field(
        default=DEFAULT_FAULT_DISCLAIMER,
        description="Data provenance and official status disclaimer",
    )


class FaultFeature(BaseModel):
    """A GeoJSON Feature representing an individual active fault segment."""

    type: Literal["Feature"] = "Feature"
    id: uuid.UUID = Field(..., description="Feature identifier matching properties.id")
    geometry: GeoJSONMultiLineStringGeometry
    properties: FaultFeatureProperties
    metadata: FaultAttributionMetadata | None = Field(
        default=None,
        description="Attribution metadata for single feature responses",
    )


class FaultFeatureCollection(BaseModel):
    """A GeoJSON FeatureCollection with attribution metadata."""

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[FaultFeature] = Field(
        ..., description="List of GeoJSON Feature objects"
    )
    metadata: FaultAttributionMetadata = Field(
        ..., description="Dataset attribution, licensing, and feature count metadata"
    )
