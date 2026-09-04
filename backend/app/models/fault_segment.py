import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Index, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FaultSegment(Base):
    """Mapped geological fault segment geometry and normalized attributes."""

    __tablename__ = "fault_segments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_feature_id: Mapped[str] = mapped_column(String(100), nullable=False)

    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    segment_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    fault_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    activity_status: Mapped[str | None] = mapped_column(String(100), nullable=True)

    geometry: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="MULTILINESTRING", srid=4326, spatial_index=False),
        nullable=False,
    )

    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_properties: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
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
            "source", "source_feature_id", name="uq_fault_segments_source_feature_id"
        ),
        Index("idx_fault_segments_geometry", "geometry", postgresql_using="gist"),
        Index("idx_fault_segments_source", "source"),
        Index("idx_fault_segments_source_feature_id", "source_feature_id"),
        Index("idx_fault_segments_name", "name"),
    )
