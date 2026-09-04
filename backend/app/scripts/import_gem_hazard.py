import argparse
import logging
import sys
from pathlib import Path

from app.db.session import SessionLocal
from app.integrations.gem.hazard_constants import (
    GEM_GPKG_FILENAME,
    GEM_GPKG_RELPATH,
    GEM_SOURCE_NAME,
    GEM_SOURCE_VERSION,
    GEM_ZIP_FILENAME,
    GEM_ZIP_MD5,
    TURKEY_CONTEXT_BBOX,
    TURKEY_CONTEXT_SCOPE,
)
from app.services.hazard_import import HazardImportService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("afet360.import_gem_hazard")


def run_hazard_import(
    cache_dir: str | None = None,
    gpkg_path: str | None = None,
    zip_path: str | None = None,
    verify_zip: bool = True,
    batch_size: int = 5000,
) -> int:
    """Execute the GEM hazard dataset import workflow."""
    resolved_gpkg: Path | None = None
    resolved_zip: Path | None = None

    if gpkg_path:
        resolved_gpkg = Path(gpkg_path)
    elif cache_dir:
        cd = Path(cache_dir)
        opt1 = cd / GEM_GPKG_RELPATH
        opt2 = cd / GEM_GPKG_FILENAME
        if opt1.is_file():
            resolved_gpkg = opt1
        elif opt2.is_file():
            resolved_gpkg = opt2
        else:
            logger.error(
                "GeoPackage file not found in cache directory %s. Checked: %s and %s",
                cd,
                opt1,
                opt2,
            )
            return 1

    if zip_path:
        resolved_zip = Path(zip_path)
    elif cache_dir:
        zp = Path(cache_dir) / GEM_ZIP_FILENAME
        if zp.is_file():
            resolved_zip = zp

    if not resolved_gpkg or not resolved_gpkg.is_file():
        logger.error(
            "Must specify either --cache-dir containing %s or direct --gpkg-path.",
            GEM_GPKG_FILENAME,
        )
        return 1

    logger.info("Target GeoPackage: %s", resolved_gpkg)
    if resolved_zip:
        logger.info("Target ZIP Archive: %s", resolved_zip)

    try:
        with SessionLocal() as session:
            service = HazardImportService(session)
            stats = service.import_gem_hazard_data(
                gpkg_path=resolved_gpkg,
                zip_path=resolved_zip,
                verify_archive=verify_zip and (resolved_zip is not None),
                bbox=TURKEY_CONTEXT_BBOX,
                batch_size=batch_size,
            )
            session.commit()

            db_total = service.repository.count_points_for_dataset(stats.dataset_id)

        throughput = (
            stats.source_rows / max(stats.elapsed_seconds, 0.001)
            if stats.elapsed_seconds > 0
            else 0
        )

        print("\n==========================================")
        print("      GEM GSHM HAZARD IMPORT SUMMARY")
        print("==========================================")
        print(f"Source                : {GEM_SOURCE_NAME}")
        print(f"Version               : {GEM_SOURCE_VERSION}")
        print(f"Scope                 : {TURKEY_CONTEXT_SCOPE}")
        print(f"Verified Checksum     : {GEM_ZIP_MD5} (MD5)")
        print(f"Total Source Rows     : {stats.source_rows:,}")
        print(f"Inserted              : {stats.inserted:,}")
        print(f"Unchanged             : {stats.unchanged:,}")
        print(f"Conflicts             : {stats.conflicts:,}")
        print(f"Database Total        : {db_total:,}")
        timing_info = f"{stats.elapsed_seconds:.2f}s ({throughput:,.0f} rows/s)"
        print(f"Elapsed Time          : {timing_info}")
        print("==========================================\n")
        return 0
    except Exception as e:
        logger.exception("Fatal error during GEM hazard import transaction: %s", e)
        return 2


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AFET360 GEM Global Seismic Hazard Map Ingestion Command",
    )
    parser.add_argument(
        "--cache-dir",
        "-c",
        type=str,
        help="Path to external cache directory containing ZIP and GeoPackage",
    )
    parser.add_argument(
        "--gpkg-path",
        "-g",
        type=str,
        help="Direct path to gem_gshm_v2026.1.gpkg",
    )
    parser.add_argument(
        "--zip-path",
        "-z",
        type=str,
        help="Direct path to gshm_v2026_1_vector.zip for checksum verification",
    )
    parser.add_argument(
        "--turkey-context",
        action="store_true",
        default=True,
        help="Import regional Türkiye-context bounding box [default: True]",
    )
    parser.add_argument(
        "--skip-zip-verify",
        action="store_true",
        help="Skip ZIP checksum verification if already verified",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Database insertion batch size [default: 5000]",
    )

    args = parser.parse_args()
    exit_code = run_hazard_import(
        cache_dir=args.cache_dir,
        gpkg_path=args.gpkg_path,
        zip_path=args.zip_path,
        verify_zip=not args.skip_zip_verify,
        batch_size=args.batch_size,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
