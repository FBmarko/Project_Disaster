"""enable postgis extension

Revision ID: 0001_enable_postgis
Revises:
Create Date: 2026-09-03 15:30:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_enable_postgis"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enable the PostGIS extension if it does not already exist."""
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")


def downgrade() -> None:
    """Safely drop the PostGIS extension with RESTRICT.

    Using RESTRICT ensures that the extension will only be dropped if no
    dependent database objects (e.g. geometry columns, spatial indices) exist,
    preventing accidental data loss in populated environments.
    """
    op.execute("DROP EXTENSION IF EXISTS postgis RESTRICT;")
