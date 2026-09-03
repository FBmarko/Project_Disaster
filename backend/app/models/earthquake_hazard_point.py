import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EarthquakeHazardPoint(Base):
    """Discrete point in a seismic hazard grid representing modeled ground motion."""

    __tablename__ = "earthquake_hazard_points"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hazard_datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_record_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    pga_g: Mapped[float] = mapped_column(Float, nullable=False)

    geometry: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "longitude",
            "latitude",
            name="uq_hazard_points_dataset_coords",
        ),
        Index(
            "idx_earthquake_hazard_points_geometry",
            "geometry",
            postgresql_using="gist",
        ),
        Index("idx_earthquake_hazard_points_dataset_id", "dataset_id"),
        CheckConstraint(
            "longitude >= -180.0 AND longitude <= 180.0",
            name="chk_hazard_points_longitude",
        ),
        CheckConstraint(
            "latitude >= -90.0 AND latitude <= 90.0",
            name="chk_hazard_points_latitude",
        ),
    )
