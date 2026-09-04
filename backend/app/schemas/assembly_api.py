"""Public GeoJSON schemas, metadata, and disclaimers for Assembly Area API."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_ASSEMBLY_SOURCE = "OpenStreetMap"
DEFAULT_ASSEMBLY_PROVIDER = "OpenStreetMap contributors"
DEFAULT_ASSEMBLY_CLASSIFICATION = "community_open_data"
DEFAULT_ASSEMBLY_LICENSE = "ODbL 1.0"
DEFAULT_ASSEMBLY_ATTRIBUTION = "© OpenStreetMap contributors"
DEFAULT_ASSEMBLY_SOURCE_REFERENCE = "https://www.openstreetmap.org/copyright"

DEFAULT_ASSEMBLY_DISCLAIMER = (
    "Community-mapped emergency assembly points from OpenStreetMap "
    "(community_open_data). This dataset is geographically incomplete, may include "
    "facility-specific muster points, is NOT official Turkish government / AFAD "
    "disaster gathering area data (Afet ve Acil Durum Toplanma Alanları), and carries "
    "no guarantees regarding structural safety, current accessibility, or safe "
    "evacuation routes. Absence of a location in this dataset does not imply the "
    "absence of an official disaster gathering area."
)

DEFAULT_LABEL_EN = "community-mapped emergency assembly points"
DEFAULT_LABEL_TR = "OSM'de işaretlenmiş acil durum toplanma noktaları"


class GeoJSONPoint(BaseModel):
    """RFC 7946 GeoJSON Point geometry in EPSG:4326 [longitude, latitude]."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["Point"] = "Point"
    coordinates: list[float] = Field(
        ...,
        description="WGS84 coordinates: [longitude, latitude]",
        min_length=2,
        max_length=2,
        examples=[[28.97, 41.01]],
    )


class GeoJSONPolygon(BaseModel):
    """RFC 7946 GeoJSON Polygon geometry in EPSG:4326."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["Polygon"] = "Polygon"
    coordinates: list[list[list[float]]] = Field(
        ...,
        description="Linear rings coordinates: [[[lon, lat], ...], ...]",
        examples=[
            [
                [
                    [28.95, 41.03],
                    [28.96, 41.03],
                    [28.96, 41.04],
                    [28.95, 41.04],
                    [28.95, 41.03],
                ]
            ]
        ],
    )


AssemblyGeometry = Annotated[GeoJSONPoint | GeoJSONPolygon, Field(discriminator="type")]


class AssemblyAreaProperties(BaseModel):
    """Normalized public properties for an emergency assembly area."""

    model_config = ConfigDict(extra="forbid")

    source_feature_id: str = Field(
        ...,
        description=(
            "Stable source identifier from OpenStreetMap (e.g. 'node/123', 'way/456')"
        ),
        examples=["node/4284118948"],
    )
    name: str | None = Field(
        default=None,
        description="Assembly area name if identified by contributors",
        examples=["Demokrasi Parkı Toplanma Alanı"],
    )
    ref: str | None = Field(
        default=None,
        description="Local reference code or designated number if tagged in OSM",
        examples=["5902-007-07"],
    )
    operator: str | None = Field(
        default=None,
        description=(
            "Managing or maintaining organization recorded in OSM "
            "(e.g. AFAD, municipality)"
        ),
        examples=["AFAD"],
    )


class AssemblyAreaNearbyProperties(AssemblyAreaProperties):
    """Public properties for an assembly area with geodesic distance calculation."""

    distance_km: float = Field(
        ...,
        ge=0.0,
        description=(
            "Exact geodesic proximity in kilometers from the query coordinate "
            "to the feature geometry"
        ),
        examples=[1.425],
    )


class AssemblyAreaFeature(BaseModel):
    """RFC 7946 GeoJSON Feature representing an assembly area."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["Feature"] = "Feature"
    id: str = Field(
        ...,
        description="AFET360 internal UUID string",
        examples=["0f2943fd-5947-450b-88e5-ca7e68036d9b"],
    )
    geometry: AssemblyGeometry = Field(
        ...,
        description="PostGIS source geometry (Point or Polygon)",
    )
    properties: AssemblyAreaProperties = Field(
        ...,
        description="Assembly area properties",
    )


class AssemblyAreaNearbyFeature(BaseModel):
    """RFC 7946 GeoJSON Feature representing a nearby assembly area with distance."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["Feature"] = "Feature"
    id: str = Field(
        ...,
        description="AFET360 internal UUID string",
        examples=["0f2943fd-5947-450b-88e5-ca7e68036d9b"],
    )
    geometry: AssemblyGeometry = Field(
        ...,
        description="PostGIS source geometry (Point or Polygon)",
    )
    properties: AssemblyAreaNearbyProperties = Field(
        ...,
        description="Assembly area properties with geodesic proximity",
    )


class AssemblyCollectionMetadata(BaseModel):
    """Attribution, provenance, and response metadata for assembly area collections."""

    model_config = ConfigDict(extra="forbid")

    returned_count: int = Field(
        ...,
        ge=0,
        description="Number of assembly area features returned in this response",
    )
    truncated: bool = Field(
        ...,
        description=(
            "Whether query results were truncated by the technical limit parameter"
        ),
    )
    source: str = Field(
        default=DEFAULT_ASSEMBLY_SOURCE,
        description="Data source identifier",
    )
    provider: str = Field(
        default=DEFAULT_ASSEMBLY_PROVIDER,
        description="Data provider / community contributor attribution",
    )
    source_classification: str = Field(
        default=DEFAULT_ASSEMBLY_CLASSIFICATION,
        description="Open data classification",
    )
    license: str = Field(
        default=DEFAULT_ASSEMBLY_LICENSE,
        description="Open Database License (ODbL 1.0)",
    )
    attribution: str = Field(
        default=DEFAULT_ASSEMBLY_ATTRIBUTION,
        description="Legal attribution string required by ODbL",
    )
    source_reference: str = Field(
        default=DEFAULT_ASSEMBLY_SOURCE_REFERENCE,
        description="Reference URL for data licensing and copyright",
    )
    snapshot_retrieved_at: datetime = Field(
        ...,
        description="UTC timestamp when snapshot was captured from Overpass API",
    )
    source_data_timestamp: datetime = Field(
        ...,
        description="UTC timestamp of upstream OpenStreetMap database state",
    )
    snapshot_sha256: str = Field(
        ...,
        description="Cryptographic SHA-256 checksum of the ingested snapshot artifact",
    )
    disclaimer: str = Field(
        default=DEFAULT_ASSEMBLY_DISCLAIMER,
        description="Neutral data-semantics and non-officiality disclaimer",
    )


class AssemblyAreaFeatureCollection(BaseModel):
    """RFC 7946 GeoJSON FeatureCollection of assembly areas with provenance."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[AssemblyAreaFeature] = Field(
        ...,
        description="Array of assembly area GeoJSON features",
    )
    metadata: AssemblyCollectionMetadata = Field(
        ...,
        description="Dataset provenance, licensing, and result metadata",
    )


class AssemblyAreaNearbyFeatureCollection(BaseModel):
    """RFC 7946 GeoJSON FeatureCollection of nearby areas with proximity distance."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[AssemblyAreaNearbyFeature] = Field(
        ...,
        description="Array of nearby assembly area features ordered by distance",
    )
    metadata: AssemblyCollectionMetadata = Field(
        ...,
        description="Dataset provenance, licensing, and result metadata",
    )


class AssemblyDatasetResponse(BaseModel):
    """Public provenance and metadata for active OpenStreetMap assembly dataset."""

    model_config = ConfigDict(extra="forbid")

    source: str = Field(
        default=DEFAULT_ASSEMBLY_SOURCE,
        description="Data source identifier",
    )
    provider: str = Field(
        default=DEFAULT_ASSEMBLY_PROVIDER,
        description="Data provider / community contributors",
    )
    source_classification: str = Field(
        default=DEFAULT_ASSEMBLY_CLASSIFICATION,
        description="Open data classification",
    )
    license: str = Field(
        default=DEFAULT_ASSEMBLY_LICENSE,
        description="License designation (ODbL 1.0)",
    )
    attribution: str = Field(
        default=DEFAULT_ASSEMBLY_ATTRIBUTION,
        description="Attribution notice required under ODbL 1.0",
    )
    source_reference: str = Field(
        default=DEFAULT_ASSEMBLY_SOURCE_REFERENCE,
        description="URL to license and copyright guidelines",
    )
    snapshot_retrieved_at: datetime = Field(
        ...,
        description="UTC timestamp when the snapshot was retrieved",
    )
    source_data_timestamp: datetime = Field(
        ...,
        description="UTC timestamp of the upstream OSM database state",
    )
    snapshot_sha256: str = Field(
        ...,
        description="SHA-256 checksum of the ingested snapshot",
    )
    feature_count: int = Field(
        ...,
        ge=0,
        description="Total number of emergency assembly areas in this dataset",
    )
    point_count: int = Field(
        ...,
        ge=0,
        description="Count of discrete Point geometry assembly features",
    )
    polygon_count: int = Field(
        ...,
        ge=0,
        description="Count of closed Polygon geometry assembly features",
    )
    label_en: str = Field(
        default=DEFAULT_LABEL_EN,
        description="Public English semantic descriptor",
    )
    label_tr: str = Field(
        default=DEFAULT_LABEL_TR,
        description="Public Turkish semantic descriptor",
    )
    disclaimer: str = Field(
        default=DEFAULT_ASSEMBLY_DISCLAIMER,
        description="Operational and legal non-officiality disclaimer",
    )
