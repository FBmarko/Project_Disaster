import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EarthquakeEvent(Base):
    """Persisted seismic event with epicenter Point geometry and AFAD metadata."""

    __tablename__ = "earthquake_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(50), default="AFAD", nullable=False)
    source_event_id: Mapped[str] = mapped_column(String(100), nullable=False)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    depth_km: Mapped[float] = mapped_column(Float, nullable=False)
    magnitude: Mapped[float] = mapped_column(Float, nullable=False)
    magnitude_type: Mapped[str] = mapped_column(String(20), nullable=False)

    location_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    province: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    neighborhood: Mapped[str | None] = mapped_column(String(100), nullable=True)

    geometry: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=False,
    )

    is_updated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_update_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    source_properties: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "source",
            "source_event_id",
            name="uq_earthquake_events_source_event_id",
        ),
        Index("idx_earthquake_events_geometry", "geometry", postgresql_using="gist"),
        Index("idx_earthquake_events_occurred_at", "occurred_at"),
        Index("idx_earthquake_events_magnitude", "magnitude"),
        Index("idx_earthquake_events_mag_occurred", "magnitude", "occurred_at"),
        Index("idx_earthquake_events_source_event_id", "source_event_id"),
    )
