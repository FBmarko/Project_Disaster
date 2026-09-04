"""CLI script for importing OSM emergency assembly areas from an approved snapshot."""

import argparse
import logging
import sys
from pathlib import Path

from app.db.session import SessionLocal
from app.integrations.osm.osm_constants import (
    OSM_ATTRIBUTION,
    OSM_EXPECTED_SHA256,
    OSM_EXPECTED_SIZE_BYTES,
    OSM_LICENSE,
    OSM_PROVIDER,
    OSM_SOURCE_CLASSIFICATION,
    OSM_SOURCE_NAME,
)
from app.services.assembly_import import AssemblyImportService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("afet360.import_osm_assembly_areas")


def run_assembly_import(snapshot_path_str: str) -> int:
    """Execute the OSM assembly area import workflow.

    Args:
        snapshot_path_str: Path to the approved snapshot JSON file.

    Returns:
        0 on success, non-zero exit code on failure.
    """
    snapshot_path = Path(snapshot_path_str).resolve()
    if not snapshot_path.is_file():
        logger.error("Snapshot file not found: %s", snapshot_path)
        return 1

    logger.info("Target OSM Snapshot: %s", snapshot_path)

    try:
        with SessionLocal() as session:
            service = AssemblyImportService(session)
            stats = service.import_osm_snapshot(
                snapshot_path=snapshot_path,
                strict_checksum=True,
                strict_contract=True,
                batch_size=500,
            )
            session.commit()

            db_total = service.repository.count_areas_for_dataset(stats.dataset_id)

        print("\n==================================================")
        print("      OSM EMERGENCY ASSEMBLY AREA IMPORT SUMMARY   ")
        print("==================================================")
        print(f"Source                : {OSM_SOURCE_NAME}")
        print(f"Provider              : {OSM_PROVIDER}")
        print(f"Classification        : {OSM_SOURCE_CLASSIFICATION}")
        print(f"License               : {OSM_LICENSE}")
        print(f"Attribution           : {OSM_ATTRIBUTION}")
        print(f"Verified Checksum     : {OSM_EXPECTED_SHA256} (SHA-256)")
        print(f"Verified Size         : {OSM_EXPECTED_SIZE_BYTES} bytes")
        print("--------------------------------------------------")
        print(f"Dataset ID            : {stats.dataset_id}")
        print(f"Dataset Created       : {stats.was_dataset_created}")
        print(f"Total Snapshot Rows   : {stats.source_rows}")
        print(f"  - Points (Nodes)    : {stats.node_count}")
        print(
            f"  - Polygons (Ways)   : {stats.polygon_count} "
            "(100% valid/simple PostGIS polygons)"
        )
        print(f"Newly Inserted Rows   : {stats.inserted}")
        print(f"Idempotent Unchanged  : {stats.unchanged}")
        print(f"Current DB Total      : {db_total}")
        print(f"Elapsed Time          : {stats.elapsed_seconds:.3f} s")
        print("==================================================\n")
        return 0

    except Exception as exc:
        logger.exception("Assembly area import failed closed: %s", exc)
        return 1


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description=(
            "Import OpenStreetMap Türkiye emergency assembly areas from "
            "an approved snapshot."
        )
    )
    parser.add_argument(
        "--snapshot",
        type=str,
        required=True,
        help="Path to the approved Overpass JSON snapshot file.",
    )
    args = parser.parse_args()
    sys.exit(run_assembly_import(args.snapshot))


if __name__ == "__main__":
    main()
