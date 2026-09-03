"""create hazard_datasets and earthquake_hazard_points tables with PostGIS index

Revision ID: 0004_create_hazard_tables
Revises: 0003_create_earthquake_events
Create Date: 2026-09-04 00:00:00.000000

"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_create_hazard_tables"
down_revision: str | None = "0003_create_earthquake_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create hazard_datasets and earthquake_hazard_points tables."""
    # 1. Create hazard_datasets table
    op.create_table(
        "hazard_datasets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_version", sa.String(length=20), nullable=False),
        sa.Column("model_name", sa.String(length=150), nullable=False),
        sa.Column("hazard_metric", sa.String(length=20), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("return_period_years", sa.Integer(), nullable=False),
        sa.Column("exceedance_probability", sa.Float(), nullable=False),
        sa.Column("time_horizon_years", sa.Integer(), nullable=False),
        sa.Column("reference_vs30_mps", sa.Float(), nullable=False),
        sa.Column("reference_ground", sa.String(length=50), nullable=False),
        sa.Column("version_doi", sa.String(length=100), nullable=False),
        sa.Column("concept_doi", sa.String(length=100), nullable=False),
        sa.Column("license", sa.String(length=100), nullable=False),
        sa.Column("attribution", sa.Text(), nullable=False),
        sa.Column("source_artifact", sa.String(length=100), nullable=False),
        sa.Column("source_artifact_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("source_checksum_algorithm", sa.String(length=20), nullable=False),
        sa.Column("source_checksum_value", sa.String(length=64), nullable=False),
        sa.Column("ingest_scope", sa.String(length=50), nullable=False),
        sa.Column("scope_min_longitude", sa.Float(), nullable=False),
        sa.Column("scope_min_latitude", sa.Float(), nullable=False),
        sa.Column("scope_max_longitude", sa.Float(), nullable=False),
        sa.Column("scope_max_latitude", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hazard_datasets")),
        sa.UniqueConstraint(
            "source",
            "source_version",
            "hazard_metric",
            "return_period_years",
            "ingest_scope",
            name="uq_hazard_datasets_natural_key",
        ),
    )

    # 2. Create earthquake_hazard_points table
    op.create_table(
        "earthquake_hazard_points",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("dataset_id", sa.UUID(), nullable=False),
        sa.Column("source_record_id", sa.BigInteger(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("pga_g", sa.Float(), nullable=False),
        sa.Column(
            "geometry",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                spatial_index=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_earthquake_hazard_points")),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["hazard_datasets.id"],
            name="fk_earthquake_hazard_points_dataset_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "dataset_id",
            "longitude",
            "latitude",
            name="uq_hazard_points_dataset_coords",
        ),
        sa.CheckConstraint(
            "longitude >= -180.0 AND longitude <= 180.0",
            name="chk_hazard_points_longitude",
        ),
        sa.CheckConstraint(
            "latitude >= -90.0 AND latitude <= 90.0",
            name="chk_hazard_points_latitude",
        ),
    )

    # 3. Create spatial GiST index and relational index
    op.create_index(
        "idx_earthquake_hazard_points_geometry",
        "earthquake_hazard_points",
        ["geometry"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        "idx_earthquake_hazard_points_dataset_id",
        "earthquake_hazard_points",
        ["dataset_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop earthquake_hazard_points and hazard_datasets tables."""
    op.drop_index(
        "idx_earthquake_hazard_points_dataset_id",
        table_name="earthquake_hazard_points",
    )
    op.drop_index(
        "idx_earthquake_hazard_points_geometry",
        table_name="earthquake_hazard_points",
        postgresql_using="gist",
    )
    op.drop_table("earthquake_hazard_points")
    op.drop_table("hazard_datasets")
