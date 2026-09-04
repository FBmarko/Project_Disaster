"""create assembly_area_datasets and assembly_areas tables with PostGIS index

Revision ID: 0005_create_assembly_tables
Revises: 0004_create_hazard_tables
Create Date: 2026-09-04 12:00:00.000000

"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_create_assembly_tables"
down_revision: str | None = "0004_create_hazard_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create assembly_area_datasets and assembly_areas tables."""
    # 1. Create assembly_area_datasets table
    op.create_table(
        "assembly_area_datasets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("source_classification", sa.String(length=50), nullable=False),
        sa.Column("license", sa.String(length=50), nullable=False),
        sa.Column("attribution", sa.Text(), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=False),
        sa.Column("snapshot_retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_data_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("snapshot_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("source_endpoint", sa.Text(), nullable=False),
        sa.Column("extraction_query", sa.Text(), nullable=False),
        sa.Column(
            "source_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assembly_area_datasets")),
        sa.UniqueConstraint(
            "source",
            "snapshot_sha256",
            name="uq_assembly_area_datasets_natural_key",
        ),
    )

    # 2. Create assembly_areas table
    op.create_table(
        "assembly_areas",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("dataset_id", sa.UUID(), nullable=False),
        sa.Column("source_feature_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=True),
        sa.Column("ref", sa.String(length=64), nullable=True),
        sa.Column("operator", sa.String(length=256), nullable=True),
        sa.Column(
            "geometry",
            geoalchemy2.types.Geometry(
                geometry_type="GEOMETRY",
                srid=4326,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                spatial_index=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "source_properties",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assembly_areas")),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["assembly_area_datasets.id"],
            name="fk_assembly_areas_dataset_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "dataset_id",
            "source_feature_id",
            name="uq_assembly_areas_dataset_feature",
        ),
    )

    # 3. Create spatial GiST index on geometry
    op.create_index(
        "idx_assembly_areas_geometry",
        "assembly_areas",
        ["geometry"],
        unique=False,
        postgresql_using="gist",
    )

    # 4. Create btree index on dataset_id
    op.create_index(
        "idx_assembly_areas_dataset_id",
        "assembly_areas",
        ["dataset_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop assembly_areas and assembly_area_datasets tables."""
    op.drop_index("idx_assembly_areas_dataset_id", table_name="assembly_areas")
    op.drop_index(
        "idx_assembly_areas_geometry",
        table_name="assembly_areas",
        postgresql_using="gist",
    )
    op.drop_table("assembly_areas")
    op.drop_table("assembly_area_datasets")
