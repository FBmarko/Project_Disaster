"""Service for validating, parsing, and idempotently importing OSM assembly points."""

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.integrations.osm.osm_constants import (
    OSM_ATTRIBUTION,
    OSM_ENDPOINT,
    OSM_EXTRACTION_QUERY,
    OSM_LICENSE,
    OSM_PROVIDER,
    OSM_SNAPSHOT_RETRIEVED_AT,
    OSM_SOURCE_CLASSIFICATION,
    OSM_SOURCE_DATA_TIMESTAMP,
    OSM_SOURCE_NAME,
    OSM_SOURCE_REFERENCE,
)
from app.integrations.osm.osm_reader import (
    read_and_validate_osm_snapshot,
    verify_snapshot_integrity,
)
from app.repositories.assembly_area import AssemblyAreaRepository

logger = logging.getLogger(__name__)


@dataclass
class AssemblyImportStatistics:
    """Detailed metrics from an emergency assembly area ingestion execution."""

    dataset_id: uuid.UUID | None = None
    source_rows: int = 0
    inserted: int = 0
    unchanged: int = 0
    conflicts: int = 0
    polygon_count: int = 0
    node_count: int = 0
    was_dataset_created: bool = False
    elapsed_seconds: float = 0.0

    @property
    def total_processed(self) -> int:
        return self.inserted + self.unchanged


class AssemblyImportService:
    """Service orchestrating atomic, idempotent OSM assembly point ingestion."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = AssemblyAreaRepository(session)

    def import_osm_snapshot(
        self,
        snapshot_path: Path,
        strict_checksum: bool = True,
        strict_contract: bool = True,
        batch_size: int = 500,
    ) -> AssemblyImportStatistics:
        """Validate, parse, and idempotently ingest an OSM assembly-point snapshot.

        Args:
            snapshot_path: Path to the JSON snapshot file.
            strict_checksum: Verify expected size and SHA-256 before parsing.
            strict_contract: Verify exact expected element counts (678 total).
            batch_size: Batch size for database insertion.

        Returns:
            AssemblyImportStatistics with counts and timing.

        Raises:
            ValueError: If checksum, contract, geometry, or drift validation fails.
        """
        t0 = time.time()

        # 1. Verify integrity and compute actual checksum
        if strict_checksum:
            actual_size, actual_sha256 = verify_snapshot_integrity(snapshot_path)
        else:
            actual_size = snapshot_path.stat().st_size
            import hashlib

            h = hashlib.sha256()
            with open(snapshot_path, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            actual_sha256 = h.hexdigest().lower()

        # 2. Parse snapshot elements and extract metadata
        parsed_points, source_metadata = read_and_validate_osm_snapshot(
            snapshot_path=snapshot_path,
            strict_checksum=strict_checksum,
            strict_contract=strict_contract,
        )

        total_features = len(parsed_points)
        node_count = sum(1 for p in parsed_points if p.geometry_type == "Point")
        way_count = sum(1 for p in parsed_points if p.geometry_type == "Polygon")

        # 3. Formulate dataset provenance payload
        retrieved_dt = datetime.fromisoformat(
            OSM_SNAPSHOT_RETRIEVED_AT.replace("Z", "+00:00")
        )
        data_dt = datetime.fromisoformat(
            OSM_SOURCE_DATA_TIMESTAMP.replace("Z", "+00:00")
        )

        dataset_payload: dict[str, Any] = {
            "source": OSM_SOURCE_NAME,
            "provider": OSM_PROVIDER,
            "source_classification": OSM_SOURCE_CLASSIFICATION,
            "license": OSM_LICENSE,
            "attribution": OSM_ATTRIBUTION,
            "source_reference": OSM_SOURCE_REFERENCE,
            "snapshot_retrieved_at": retrieved_dt,
            "source_data_timestamp": data_dt,
            "snapshot_sha256": actual_sha256,
            "snapshot_size_bytes": actual_size,
            "source_endpoint": OSM_ENDPOINT,
            "extraction_query": OSM_EXTRACTION_QUERY,
            "source_metadata": source_metadata,
        }

        # 4. Atomic dataset creation or provenance verification
        dataset, was_created = self.repository.get_or_create_dataset(dataset_payload)
        logger.info(
            "AssemblyAreaDataset '%s' (SHA: %s...): id=%s (created=%s)",
            dataset.source,
            actual_sha256[:12],
            dataset.id,
            was_created,
        )

        stats = AssemblyImportStatistics(
            dataset_id=dataset.id,
            source_rows=total_features,
            polygon_count=way_count,
            node_count=node_count,
            was_dataset_created=was_created,
        )

        # 5. Check existing features for idempotency and drift detection
        existing_features = self.repository.get_existing_features_map(dataset.id)
        has_existing = len(existing_features) > 0

        if not has_existing:
            logger.info(
                "Inserting %d assembly features in batches of %d...",
                total_features,
                batch_size,
            )
            for i in range(0, total_features, batch_size):
                batch = parsed_points[i : i + batch_size]
                inserted = self.repository.insert_areas_batch(dataset.id, batch)
                stats.inserted += inserted

            # Validate all stored polygons via PostGIS ST_IsValid and ST_IsSimple
            total_poly, valid_poly, simple_poly = (
                self.repository.validate_polygons_valid_and_simple(dataset.id)
            )
            logger.info(
                "PostGIS polygon validation verified: total=%d, valid=%d, simple=%d",
                total_poly,
                valid_poly,
                simple_poly,
            )

        else:
            logger.info(
                "Found %d existing features for dataset %s. "
                "Verifying idempotency and data drift...",
                len(existing_features),
                dataset.id,
            )
            if len(existing_features) != total_features:
                raise ValueError(
                    f"Count drift detected: existing database contains "
                    f"{len(existing_features)} features, but incoming snapshot "
                    f"contains {total_features}."
                )

            for pt in parsed_points:
                existing_rec = existing_features.get(pt.source_feature_id)
                if existing_rec is None:
                    raise ValueError(
                        f"Drift detected: feature {pt.source_feature_id} exists "
                        f"in snapshot but not in existing dataset."
                    )

                # Check attributes
                if existing_rec["name"] != pt.name:
                    raise ValueError(
                        f"Attribute drift in {pt.source_feature_id}: "
                        f"name '{existing_rec['name']}' vs incoming '{pt.name}'"
                    )
                if existing_rec["ref"] != pt.ref:
                    raise ValueError(
                        f"Attribute drift in {pt.source_feature_id}: "
                        f"ref '{existing_rec['ref']}' vs incoming '{pt.ref}'"
                    )
                if existing_rec["operator"] != pt.operator:
                    raise ValueError(
                        f"Attribute drift in {pt.source_feature_id}: "
                        f"operator '{existing_rec['operator']}' vs "
                        f"incoming '{pt.operator}'"
                    )
                if existing_rec["source_properties"] != pt.source_properties:
                    raise ValueError(
                        f"Attribute drift in {pt.source_feature_id}: "
                        f"source_properties difference."
                    )

                # Check geometry equality via PostGIS ST_Equals
                is_equal = self.repository.check_spatial_equality(
                    dataset.id, pt.source_feature_id, pt.wkt_geometry
                )
                if not is_equal:
                    raise ValueError(
                        f"Spatial drift detected for feature {pt.source_feature_id}: "
                        f"geometry does not match existing stored PostGIS geometry."
                    )

                stats.unchanged += 1

        stats.elapsed_seconds = time.time() - t0
        return stats
