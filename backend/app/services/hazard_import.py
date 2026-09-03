import logging
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.integrations.gem.hazard_constants import (
    GEM_ATTRIBUTION,
    GEM_CONCEPT_DOI,
    GEM_HAZARD_METRIC,
    GEM_LICENSE,
    GEM_MODEL_NAME,
    GEM_REFERENCE_GROUND,
    GEM_REFERENCE_VS30_MPS,
    GEM_RETURN_PERIOD_YEARS,
    GEM_SOURCE_NAME,
    GEM_SOURCE_VERSION,
    GEM_TIME_HORIZON_YEARS,
    GEM_UNIT,
    GEM_VERSION_DOI,
    GEM_ZIP_FILENAME,
    GEM_ZIP_MD5,
    GEM_ZIP_SIZE_BYTES,
    TURKEY_CONTEXT_BBOX,
    TURKEY_CONTEXT_SCOPE,
)
from app.integrations.gem.hazard_reader import (
    GemHazardRecord,
    stream_turkey_hazard_records,
    verify_geopackage_metadata,
    verify_zip_artifact,
)
from app.repositories.earthquake_hazard import EarthquakeHazardRepository

logger = logging.getLogger(__name__)


@dataclass
class HazardImportStatistics:
    """Statistics detailing the results of a seismic hazard ingestion run."""

    source_rows: int = 0
    inserted: int = 0
    unchanged: int = 0
    conflicts: int = 0
    dataset_id: Any = None
    elapsed_seconds: float = 0.0

    @property
    def total_processed(self) -> int:
        return self.inserted + self.unchanged


class HazardImportService:
    """Service for validation, extraction, and idempotent GEM hazard import."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = EarthquakeHazardRepository(session)

    def import_gem_hazard_data(
        self,
        gpkg_path: Path,
        zip_path: Path | None = None,
        verify_archive: bool = False,
        bbox: tuple[float, float, float, float] = TURKEY_CONTEXT_BBOX,
        batch_size: int = 5000,
        check_full_size: bool = True,
    ) -> HazardImportStatistics:
        """Validate source and idempotently import seismic hazard points.

        Args:
            gpkg_path: Path to extracted GeoPackage file.
            zip_path: Optional path to source ZIP archive.
            verify_archive: Whether to verify ZIP size and MD5 before import.
            bbox: Bounding box tuple (min_lon, min_lat, max_lon, max_lat).
            batch_size: Batch size for database streaming insertion.
            check_full_size: Whether to verify GeoPackage exact byte size.

        Returns:
            HazardImportStatistics object with result counts and timing.
        """
        t0 = time.time()

        # 1. Verify ZIP archive if requested
        if verify_archive and zip_path:
            logger.info("Validating source ZIP archive %s...", zip_path)
            verify_zip_artifact(zip_path)

        # 2. Verify GeoPackage schema, layer, and RTree
        logger.info("Validating source GeoPackage metadata at %s...", gpkg_path)
        verify_geopackage_metadata(gpkg_path, check_full_size=check_full_size)

        # 3. Fetch or create HazardDataset metadata record
        dataset_payload = {
            "source": GEM_SOURCE_NAME,
            "source_version": GEM_SOURCE_VERSION,
            "model_name": GEM_MODEL_NAME,
            "hazard_metric": GEM_HAZARD_METRIC,
            "unit": GEM_UNIT,
            "return_period_years": GEM_RETURN_PERIOD_YEARS,
            "exceedance_probability": 0.10,
            "time_horizon_years": GEM_TIME_HORIZON_YEARS,
            "reference_vs30_mps": GEM_REFERENCE_VS30_MPS,
            "reference_ground": GEM_REFERENCE_GROUND,
            "version_doi": GEM_VERSION_DOI,
            "concept_doi": GEM_CONCEPT_DOI,
            "license": GEM_LICENSE,
            "attribution": GEM_ATTRIBUTION,
            "source_artifact": GEM_ZIP_FILENAME,
            "source_artifact_size_bytes": GEM_ZIP_SIZE_BYTES,
            "source_checksum_algorithm": "md5",
            "source_checksum_value": GEM_ZIP_MD5,
            "ingest_scope": TURKEY_CONTEXT_SCOPE,
            "scope_min_longitude": bbox[0],
            "scope_min_latitude": bbox[1],
            "scope_max_longitude": bbox[2],
            "scope_max_latitude": bbox[3],
        }

        dataset, was_created = self.repository.get_or_create_dataset(dataset_payload)
        logger.info(
            "HazardDataset '%s' v%s (%s): id=%s (created=%s)",
            dataset.source,
            dataset.source_version,
            dataset.ingest_scope,
            dataset.id,
            was_created,
        )

        stats = HazardImportStatistics(dataset_id=dataset.id)

        # 4. Fetch existing points lookup for idempotency and conflict detection
        existing_points = self.repository.get_existing_points_map(dataset.id)
        has_existing = len(existing_points) > 0
        if has_existing:
            logger.info(
                "Found %d existing points for dataset %s. Verifying idempotency...",
                len(existing_points),
                dataset.id,
            )

        # 5. Stream and insert records in bounded batches
        stream = stream_turkey_hazard_records(
            gpkg_path, bbox=bbox, batch_size=batch_size
        )
        for batch in stream:
            if not has_existing:
                inserted = self.repository.insert_points_batch(dataset.id, batch)
                stats.inserted += inserted
                stats.source_rows += len(batch)
            else:
                to_insert: list[GemHazardRecord] = []
                for rec in batch:
                    stats.source_rows += 1
                    coord_key = (
                        round(rec.longitude, 7),
                        round(rec.latitude, 7),
                    )
                    if coord_key in existing_points:
                        existing_pga, existing_fid = existing_points[coord_key]
                        pga_matches = math.isclose(
                            existing_pga, rec.pga_g, abs_tol=1e-12, rel_tol=0.0
                        )
                        fid_matches = existing_fid is None or existing_fid == rec.fid

                        if pga_matches and fid_matches:
                            stats.unchanged += 1
                        else:
                            stats.conflicts += 1
                            reasons = []
                            if not pga_matches:
                                reasons.append(
                                    f"pga stored={existing_pga} vs incoming={rec.pga_g}"
                                )
                            if not fid_matches:
                                reasons.append(
                                    f"fid stored={existing_fid} vs incoming={rec.fid}"
                                )
                            err = (
                                f"Conflict at ({rec.longitude}, {rec.latitude}) "
                                f"in dataset {dataset.id}: {', '.join(reasons)}"
                            )
                            raise ValueError(err)
                    else:
                        to_insert.append(rec)

                if to_insert:
                    inserted = self.repository.insert_points_batch(
                        dataset.id, to_insert
                    )
                    stats.inserted += inserted
                    for inserted_rec in to_insert:
                        key = (
                            round(inserted_rec.longitude, 7),
                            round(inserted_rec.latitude, 7),
                        )
                        existing_points[key] = (
                            inserted_rec.pga_g,
                            inserted_rec.fid,
                        )

        self.session.flush()

        t1 = time.time()
        stats.elapsed_seconds = t1 - t0
        logger.info(
            "GEM hazard import completed in %.2fs: %d source, %d inserted, "
            "%d unchanged, %d conflicts",
            stats.elapsed_seconds,
            stats.source_rows,
            stats.inserted,
            stats.unchanged,
            stats.conflicts,
        )

        return stats
