import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HazardDataset(Base):
    """Normalized metadata describing an ingested seismic hazard dataset."""

    __tablename__ = "hazard_datasets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_version: Mapped[str] = mapped_column(String(20), nullable=False)
    model_name: Mapped[str] = mapped_column(String(150), nullable=False)
    hazard_metric: Mapped[str] = mapped_column(String(20), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    return_period_years: Mapped[int] = mapped_column(Integer, nullable=False)
    exceedance_probability: Mapped[float] = mapped_column(Float, nullable=False)
    time_horizon_years: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_vs30_mps: Mapped[float] = mapped_column(Float, nullable=False)
    reference_ground: Mapped[str] = mapped_column(String(50), nullable=False)
    version_doi: Mapped[str] = mapped_column(String(100), nullable=False)
    concept_doi: Mapped[str] = mapped_column(String(100), nullable=False)
    license: Mapped[str] = mapped_column(String(100), nullable=False)
    attribution: Mapped[str] = mapped_column(Text, nullable=False)
    source_artifact: Mapped[str] = mapped_column(String(100), nullable=False)
    source_artifact_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_checksum_algorithm: Mapped[str] = mapped_column(String(20), nullable=False)
    source_checksum_value: Mapped[str] = mapped_column(String(64), nullable=False)
    ingest_scope: Mapped[str] = mapped_column(String(50), nullable=False)
    scope_min_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    scope_min_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    scope_max_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    scope_max_latitude: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "source",
            "source_version",
            "hazard_metric",
            "return_period_years",
            "ingest_scope",
            name="uq_hazard_datasets_natural_key",
        ),
    )
