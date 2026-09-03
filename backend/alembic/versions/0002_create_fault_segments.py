"""create fault_segments table and spatial indexes

Revision ID: 0002_create_fault_segments
Revises: 0001_enable_postgis
Create Date: 2026-09-03 17:20:00.000000

"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_create_fault_segments"
down_revision: str | None = "0001_enable_postgis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create fault_segments table with PostGIS geometry, constraints, and indexes."""
    op.create_table(
        "fault_segments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_feature_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("segment_name", sa.String(length=200), nullable=True),
        sa.Column("fault_type", sa.String(length=100), nullable=True),
        sa.Column("activity_status", sa.String(length=100), nullable=True),
        sa.Column(
            "geometry",
            geoalchemy2.types.Geometry(
                geometry_type="MULTILINESTRING",
                srid=4326,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                spatial_index=False,
            ),
            nullable=False,
        ),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column(
            "source_properties",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fault_segments")),
        sa.UniqueConstraint(
            "source", "source_feature_id", name="uq_fault_segments_source_feature_id"
        ),
    )

    # Create PostGIS GiST spatial index
    op.create_index(
        "idx_fault_segments_geometry",
        "fault_segments",
        ["geometry"],
        unique=False,
        postgresql_using="gist",
    )

    # Relational search indexes
    op.create_index(
        "idx_fault_segments_source", "fault_segments", ["source"], unique=False
    )
    op.create_index(
        "idx_fault_segments_source_feature_id",
        "fault_segments",
        ["source_feature_id"],
        unique=False,
    )
    op.create_index("idx_fault_segments_name", "fault_segments", ["name"], unique=False)


def downgrade() -> None:
    """Drop indexes and fault_segments table."""
    op.drop_index("idx_fault_segments_name", table_name="fault_segments")
    op.drop_index("idx_fault_segments_source_feature_id", table_name="fault_segments")
    op.drop_index("idx_fault_segments_source", table_name="fault_segments")
    op.drop_index(
        "idx_fault_segments_geometry",
        table_name="fault_segments",
        postgresql_using="gist",
    )
    op.drop_table("fault_segments")
