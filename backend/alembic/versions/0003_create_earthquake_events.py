"""create earthquake_events table and spatial indexes

Revision ID: 0003_create_earthquake_events
Revises: 0002_create_fault_segments
Create Date: 2026-09-03 20:10:00.000000

"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_create_earthquake_events"
down_revision: str | None = "0002_create_fault_segments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create earthquake_events table with Point geometry, constraints, and indexes."""
    op.create_table(
        "earthquake_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_event_id", sa.String(length=100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("depth_km", sa.Float(), nullable=False),
        sa.Column("magnitude", sa.Float(), nullable=False),
        sa.Column("magnitude_type", sa.String(length=20), nullable=False),
        sa.Column("location_name", sa.String(length=255), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("province", sa.String(length=100), nullable=True),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("neighborhood", sa.String(length=100), nullable=True),
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
            "is_updated",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("last_update_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "source_properties",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_earthquake_events")),
        sa.UniqueConstraint(
            "source",
            "source_event_id",
            name="uq_earthquake_events_source_event_id",
        ),
    )

    # Spatial GiST index
    op.create_index(
        "idx_earthquake_events_geometry",
        "earthquake_events",
        ["geometry"],
        unique=False,
        postgresql_using="gist",
    )

    # Relational search & query optimization indexes
    op.create_index(
        "idx_earthquake_events_occurred_at",
        "earthquake_events",
        ["occurred_at"],
        unique=False,
    )
    op.create_index(
        "idx_earthquake_events_magnitude",
        "earthquake_events",
        ["magnitude"],
        unique=False,
    )
    op.create_index(
        "idx_earthquake_events_mag_occurred",
        "earthquake_events",
        ["magnitude", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "idx_earthquake_events_source_event_id",
        "earthquake_events",
        ["source_event_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop indexes and earthquake_events table."""
    op.drop_index(
        "idx_earthquake_events_source_event_id",
        table_name="earthquake_events",
    )
    op.drop_index(
        "idx_earthquake_events_mag_occurred",
        table_name="earthquake_events",
    )
    op.drop_index(
        "idx_earthquake_events_magnitude",
        table_name="earthquake_events",
    )
    op.drop_index(
        "idx_earthquake_events_occurred_at",
        table_name="earthquake_events",
    )
    op.drop_index(
        "idx_earthquake_events_geometry",
        table_name="earthquake_events",
        postgresql_using="gist",
    )
    op.drop_table("earthquake_events")
