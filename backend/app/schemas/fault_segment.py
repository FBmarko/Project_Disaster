import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FaultSegmentBase(BaseModel):
    """Base schema representing normalized geological fault attributes."""

    source: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Identifier of dataset source e.g. GEM_GAF",
    )
    source_feature_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Stable feature ID from source catalog",
    )
    name: str | None = Field(
        default=None, max_length=200, description="Fault system or zone name"
    )
    segment_name: str | None = Field(
        default=None, max_length=200, description="Specific segment name"
    )
    fault_type: str | None = Field(
        default=None,
        max_length=100,
        description="Kinematic type e.g. Strike-Slip, Normal",
    )
    activity_status: str | None = Field(
        default=None, max_length=100, description="Activity classification"
    )
    source_reference: str | None = Field(
        default=None, max_length=255, description="Attribution or citation string"
    )
    source_properties: dict[str, Any] = Field(
        default_factory=dict, description="Raw source attributes preserved"
    )


class FaultSegmentCreate(FaultSegmentBase):
    """Schema for validating fault segment data before database persistence."""

    coordinates: list[list[list[float]]] = Field(
        ...,
        description="MultiLineString coords EPSG:4326: [[[lon, lat], ...], ...]",
    )

    @field_validator("coordinates")
    @classmethod
    def validate_multilinestring_coordinates(
        cls, v: list[list[list[float]]]
    ) -> list[list[list[float]]]:
        if not v:
            raise ValueError("MultiLineString must contain at least one line")
        for line_idx, line in enumerate(v):
            if len(line) < 2:
                raise ValueError(
                    f"Line {line_idx} must contain at least 2 coordinate points"
                )
            for pt_idx, pt in enumerate(line):
                if len(pt) < 2:
                    raise ValueError(
                        f"Point {pt_idx} in line {line_idx} needs 2 values [lon, lat]"
                    )
                lon, lat = pt[0], pt[1]
                if not (-180.0 <= lon <= 180.0):
                    raise ValueError(
                        f"Longitude {lon} at line {line_idx}, pt {pt_idx} out of range"
                    )
                if not (-90.0 <= lat <= 90.0):
                    raise ValueError(
                        f"Latitude {lat} at line {line_idx}, pt {pt_idx} out of range"
                    )
        return v


class FaultSegmentRead(FaultSegmentBase):
    """Internal read schema for a persisted FaultSegment."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
