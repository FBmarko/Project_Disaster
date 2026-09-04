import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from geoalchemy2 import Geometry
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.assembly_area_dataset import AssemblyAreaDataset


class AssemblyArea(Base):
    """Emergency gathering space mapped from community or official open data."""

    __tablename__ = "assembly_areas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assembly_area_datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_feature_id: Mapped[str] = mapped_column(String(64), nullable=False)

    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    operator: Mapped[str | None] = mapped_column(String(256), nullable=True)

    geometry: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=False),
        nullable=False,
    )

    source_properties: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
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

    dataset: Mapped["AssemblyAreaDataset"] = relationship(
        "AssemblyAreaDataset",
        back_populates="assembly_areas",
    )

    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "source_feature_id",
            name="uq_assembly_areas_dataset_feature",
        ),
        Index(
            "idx_assembly_areas_geometry",
            "geometry",
            postgresql_using="gist",
        ),
        Index("idx_assembly_areas_dataset_id", "dataset_id"),
    )
