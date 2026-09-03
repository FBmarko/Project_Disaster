import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EarthquakeEventBase(BaseModel):
    """Base schema for seismic event attributes."""

    source: str = Field(default="AFAD", description="Source organization identifier")
    source_event_id: str = Field(
        ..., description="Upstream primary event ID (e.g. 543428)"
    )
    occurred_at: datetime = Field(
        ..., description="Timezone-aware UTC timestamp of event occurrence"
    )
    depth_km: float = Field(..., description="Hypocenter depth in kilometers")
    magnitude: float = Field(..., description="Seismic magnitude measurement")
    magnitude_type: str = Field(
        ..., description="Magnitude scale type (e.g. MW, ML, MD)"
    )
    location_name: str | None = Field(
        default=None, description="Descriptive geographic location"
    )
    country: str | None = Field(default=None, description="Country name if reported")
    province: str | None = Field(default=None, description="Province name if reported")
    district: str | None = Field(default=None, description="District name if reported")
    neighborhood: str | None = Field(
        default=None, description="Neighborhood name if reported"
    )
    longitude: float = Field(..., description="Epicenter WGS84 longitude (-180 to 180)")
    latitude: float = Field(..., description="Epicenter WGS84 latitude (-90 to 90)")
    is_updated: bool = Field(
        default=False, description="Whether event was updated upstream"
    )
    last_update_at: datetime | None = Field(
        default=None, description="Timestamp of last upstream revision"
    )
    source_properties: dict[str, Any] = Field(
        default_factory=dict, description="Raw source payload metadata"
    )


class EarthquakeEventCreate(EarthquakeEventBase):
    """Schema for creating or updating an earthquake event entity."""

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if not (-90.0 <= v <= 90.0):
            raise ValueError(f"Latitude must be between -90 and 90, got {v}")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if not (-180.0 <= v <= 180.0):
            raise ValueError(f"Longitude must be between -180 and 180, got {v}")
        return v

    @field_validator("depth_km")
    @classmethod
    def validate_depth(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError(f"Depth cannot be negative, got {v}")
        return v

    @field_validator("magnitude")
    @classmethod
    def validate_magnitude(cls, v: float) -> float:
        if not (-2.0 <= v <= 10.0):
            raise ValueError(
                f"Magnitude out of realistic range (-2.0 to 10.0), got {v}"
            )
        return v


class EarthquakeEventRead(EarthquakeEventBase):
    """Schema for reading a persisted earthquake event entity."""

    id: uuid.UUID
    fetched_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
