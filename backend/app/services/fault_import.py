import json
import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations.gem.parser import parse_gem_feature_collection
from app.repositories.fault_segment import FaultSegmentRepository
from app.schemas.fault_segment import FaultSegmentCreate

logger = logging.getLogger(__name__)


@dataclass
class ImportStatistics:
    """Tracks statistics for a fault data import operation."""

    total_source_features: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    failed: int = 0

    @property
    def processed_count(self) -> int:
        return self.inserted + self.updated + self.unchanged


class FaultImportService:
    """Service orchestrating the import and normalization of active fault datasets."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = FaultSegmentRepository(session)

    def filter_by_boundary_intersection(
        self,
        records: list[FaultSegmentCreate],
        boundary_geometry: dict[str, Any],
    ) -> list[FaultSegmentCreate]:
        """Filter records to those intersecting the boundary polygon."""
        if not records:
            return []

        lines_json = json.dumps(
            [{"type": "MultiLineString", "coordinates": r.coordinates} for r in records]
        )
        boundary_json = json.dumps(boundary_geometry)

        stmt = text("""
            SELECT lines.idx
            FROM (
                SELECT (val.ord - 1) AS idx,
                       ST_SetSRID(ST_GeomFromGeoJSON(val.elem), 4326) AS geom
                FROM json_array_elements_text(:lines_json)
                WITH ORDINALITY AS val(elem, ord)
            ) lines
            WHERE ST_Intersects(
                lines.geom,
                ST_SetSRID(ST_GeomFromGeoJSON(:boundary_json), 4326)
            )
        """)
        intersecting_indices = set(
            self.session.scalars(
                stmt,
                {"lines_json": lines_json, "boundary_json": boundary_json},
            ).all()
        )

        return [r for idx, r in enumerate(records) if idx in intersecting_indices]

    def import_gem_geojson(
        self,
        geojson_data: dict[str, Any],
        bbox: tuple[float, float, float, float] | None = None,
        boundary_geometry: dict[str, Any] | None = None,
        batch_size: int = 250,
    ) -> ImportStatistics:
        """Parse, validate, and idempotently upsert GEM active fault records in batches.

        Args:
            geojson_data: Raw GeoJSON FeatureCollection dictionary.
            bbox: Optional bounding box filter (min_lon, min_lat, max_lon, max_lat).
            boundary_geometry: Optional boundary polygon for spatial intersection.
            batch_size: Number of records to upsert per database flush.

        Returns:
            ImportStatistics detailing the result counts.
        """
        features = geojson_data.get("features", [])
        total_source = len(features) if isinstance(features, list) else 0

        logger.info("Starting GEM fault import for %d source features...", total_source)

        valid_records, skipped, failed = parse_gem_feature_collection(
            geojson_data, bbox=bbox
        )

        # Apply boundary spatial intersection if requested
        if boundary_geometry is not None:
            pre_boundary_count = len(valid_records)
            valid_records = self.filter_by_boundary_intersection(
                valid_records, boundary_geometry
            )
            boundary_skipped = pre_boundary_count - len(valid_records)
            skipped += boundary_skipped
            logger.info(
                "Retained %d features via boundary intersection (%d skipped)",
                len(valid_records),
                boundary_skipped,
            )

        stats = ImportStatistics(
            total_source_features=total_source,
            skipped=skipped,
            failed=failed,
        )

        # Batch upsert valid records within a transaction savepoint
        with self.session.begin_nested():
            for i in range(0, len(valid_records), batch_size):
                batch = valid_records[i : i + batch_size]
                inserted, updated, unchanged = self.repository.upsert_batch(batch)
                stats.inserted += inserted
                stats.updated += updated
                stats.unchanged += unchanged
                self.session.flush()

        logger.info(
            "GEM fault import finished: %d inserted, %d updated, %d unchanged, "
            "%d skipped, %d failed",
            stats.inserted,
            stats.updated,
            stats.unchanged,
            stats.skipped,
            stats.failed,
        )

        return stats
