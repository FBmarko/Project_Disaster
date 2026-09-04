"""Public GeoJSON schemas and attribution metadata for the Earthquake REST API."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Centralized AFAD Public Attribution Constants
DEFAULT_AFAD_SOURCE = (
    "T.C. İçişleri Bakanlığı Afet ve Acil Durum Yönetimi Başkanlığı (AFAD)"
)
DEFAULT_AFAD_DATASET = "AFAD Deprem Dairesi Başkanlığı Event Web Service"
DEFAULT_AFAD_ATTRIBUTION = "T.C. İçişleri Bakanlığı AFAD Deprem Dairesi Başkanlığı"
DEFAULT_AFAD_DISCLAIMER = (
    "Earthquake data is a locally synchronized snapshot from AFAD Event Web Service. "
    "Delivery is not guaranteed real-time."
)
DEFAULT_DATA_DELIVERY = "local_synchronized_snapshot"

# Mandatory Scientific Proximity Constants
SCIENTIFIC_PROXIMITY_DISCLAIMER = (
    "Spatial proximity to a mapped fault trace does not establish that the "
    "earthquake ruptured on or was caused by that fault."
)
ASSOCIATION_METHOD_SPATIAL_PROXIMITY = "spatial_proximity"

# GEM Fault Attribution Constants (for dual attribution when fault data participates)
DEFAULT_FAULT_SOURCE = "GEM Global Active Faults Database (GAF-DB)"
DEFAULT_FAULT_LICENSE = "CC BY-SA 4.0"
DEFAULT_FAULT_ATTRIBUTION = (
    "Global Earthquake Model (GEM) Foundation (Styron & Pagani, 2020)"
)
DEFAULT_FAULT_DISCLAIMER = (
    "Fault data based on GEM GAF features intersecting the Natural Earth 1:50m "
    "generalized Türkiye polygon. Not official Turkish government / MTA fault data."
)


class EarthquakePointGeometry(BaseModel):
    """RFC 7946 GeoJSON Point geometry in EPSG:4326 [longitude, latitude]."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["Point"] = "Point"
    coordinates: list[float] = Field(
        ...,
        description="WGS84 coordinates in RFC 7946 order: [longitude, latitude]",
        min_length=2,
        max_length=2,
    )


class EarthquakeFeatureProperties(BaseModel):
    """Public properties for an Earthquake GeoJSON Feature."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID = Field(..., description="Unique AFET360 event UUID")
    source: str = Field(..., description="Data source identifier (e.g. AFAD)")
    source_event_id: str = Field(..., description="Upstream event identity")
    occurred_at: datetime = Field(..., description="Event origin timestamp in UTC")
    depth_km: float = Field(..., description="Hypocenter depth in kilometers")
    magnitude: float = Field(..., description="Earthquake magnitude value")
    magnitude_type: str = Field(..., description="Magnitude scale (e.g. MW, ML, MD)")
    location_name: str | None = Field(
        None, description="Human-readable location description"
    )
    country: str | None = Field(None, description="Country name")
    province: str | None = Field(None, description="Administrative province")
    district: str | None = Field(None, description="Administrative district")
    neighborhood: str | None = Field(
        None, description="Administrative neighborhood / village"
    )

    # Spatial proximity fields (populated only when proximity query is active)
    distance_to_fault_km: float | None = Field(
        None,
        description="Geodesic distance to the mapped fault trace in kilometers",
    )
    nearest_fault_id: uuid.UUID | None = Field(
        None,
        description="AFET360 UUID of the nearest mapped fault segment",
    )
    nearest_fault_source_feature_id: str | None = Field(
        None,
        description="Catalog feature identity of the nearest mapped fault segment",
    )
    association_method: str | None = Field(
        None,
        description="Proximity association method (always 'spatial_proximity')",
    )
    proximity_disclaimer: str | None = Field(
        None,
        description="Scientific disclaimer clarifying non-causal nature of proximity",
    )


class EarthquakeApiMetadata(BaseModel):
    """Metadata block accompanying GeoJSON collections or single detail."""

    model_config = ConfigDict(extra="forbid")

    count: int = Field(..., description="Number of features returned in this response")
    source: str = Field(
        DEFAULT_AFAD_SOURCE, description="Authoritative earthquake source"
    )
    dataset: str = Field(DEFAULT_AFAD_DATASET, description="Source dataset description")
    attribution: str = Field(
        DEFAULT_AFAD_ATTRIBUTION, description="Required attribution text"
    )
    disclaimer: str = Field(
        DEFAULT_AFAD_DISCLAIMER, description="Data snapshot disclaimer"
    )
    data_delivery: str = Field(
        DEFAULT_DATA_DELIVERY, description="Delivery mode indication"
    )

    # Optional fault & proximity metadata (included for fault-associated queries)
    fault_id: uuid.UUID | None = Field(
        None, description="Target fault UUID if queried for a specific fault"
    )
    fault_source: str | None = Field(None, description="Fault dataset source")
    fault_source_feature_id: str | None = Field(
        None, description="Target fault catalog feature ID"
    )
    max_distance_km: float | None = Field(
        None, description="Maximum geographic radius threshold in km"
    )
    fault_attribution: str | None = Field(
        None, description="Attribution for fault dataset (GEM)"
    )
    fault_license: str | None = Field(
        None, description="License for fault dataset (CC BY-SA 4.0)"
    )
    scientific_disclaimer: str | None = Field(
        None,
        description="Scientific non-causality disclaimer for fault proximity",
    )


class EarthquakeFeature(BaseModel):
    """RFC 7946 GeoJSON Feature representing an earthquake event."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["Feature"] = "Feature"
    id: uuid.UUID = Field(..., description="Unique event UUID")
    geometry: EarthquakePointGeometry = Field(
        ..., description="Epicenter Point geometry"
    )
    properties: EarthquakeFeatureProperties = Field(
        ..., description="Normalized earthquake attributes"
    )
    metadata: EarthquakeApiMetadata | None = Field(
        None,
        description="Source and attribution metadata for single-feature detail",
    )


class EarthquakeFeatureCollection(BaseModel):
    """RFC 7946 GeoJSON FeatureCollection of earthquakes."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["FeatureCollection"] = "FeatureCollection"
    metadata: EarthquakeApiMetadata = Field(
        ..., description="Response metadata and source attribution"
    )
    features: list[EarthquakeFeature] = Field(
        ..., description="List of earthquake GeoJSON features"
    )
