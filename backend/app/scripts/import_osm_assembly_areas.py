"""CLI script for importing OSM emergency assembly areas."""

import argparse
import hashlib
import json
import logging
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from app.db.session import SessionLocal
from app.integrations.osm.osm_constants import (
    OSM_ATTRIBUTION,
    OSM_ENDPOINT,
    OSM_EXPECTED_SHA256,
    OSM_EXPECTED_SIZE_BYTES,
    OSM_EXTRACTION_QUERY,
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

DEFAULT_ASSEMBLY_CACHE_DIR = (
    Path(__file__).parent.parent.parent / "data" / "cache" / "assembly"
)


def fetch_osm_assembly_snapshot(
    dest_path: Path,
    endpoint: str = OSM_ENDPOINT,
    query: str = OSM_EXTRACTION_QUERY,
    timeout: float = 120.0,
) -> tuple[Path, int, str]:
    """Fetch live OSM emergency assembly points from Overpass API.

    Streams response to a temporary (.part) file, verifies JSON elements,
    computes SHA-256 and size, and atomically promotes the file.

    Returns:
        tuple of (promoted_snapshot_path, byte_size, sha256_hex)
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    part_path = dest_path.parent / f"{dest_path.name}.part"
    if part_path.is_file():
        part_path.unlink(missing_ok=True)

    logger.info("Querying Overpass API at %s ...", endpoint)
    encoded_query = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=encoded_query,
        headers={
            "User-Agent": (
                "AFET360-Importer/0.1.0 (University disaster preparedness project)"
            ),
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        },
    )

    hasher = hashlib.sha256()
    size = 0
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            with open(part_path, "wb") as f_out:
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    hasher.update(chunk)
                    f_out.write(chunk)
                    size += len(chunk)
    except Exception as exc:
        part_path.unlink(missing_ok=True)
        raise RuntimeError(
            f"Failed to query Overpass API at {endpoint}: {exc}"
        ) from exc

    # Verify JSON structure before promoting
    try:
        with open(part_path, encoding="utf-8") as f_in:
            data = json.load(f_in)
        if not isinstance(data, dict) or not isinstance(data.get("elements"), list):
            raise ValueError(
                "Overpass response is not a valid OSM JSON payload with 'elements'"
            )
    except Exception as exc:
        part_path.unlink(missing_ok=True)
        raise ValueError(f"Failed to validate Overpass JSON response: {exc}") from exc

    part_path.replace(dest_path)
    sha256_hex = hasher.hexdigest().lower()
    logger.info(
        "Successfully fetched OSM snapshot (%d bytes, sha256=%s): %s",
        size,
        sha256_hex,
        dest_path,
    )
    return dest_path, size, sha256_hex


def run_assembly_import(
    snapshot_path_str: str | None = None,
    download: bool = False,
    cache_dir: str | None = None,
) -> int:
    """Execute the OSM assembly area import workflow.

    Args:
        snapshot_path_str: Optional path to an approved snapshot JSON file.
        download: If True, queries Overpass API to fetch live snapshot.
        cache_dir: Optional cache directory for downloaded snapshot.

    Returns:
        0 on success, non-zero exit code on failure.
    """
    snapshot_path: Path
    strict_checksum: bool
    strict_contract: bool
    actual_size: int = 0
    actual_sha256: str = ""

    if download:
        cd = Path(cache_dir) if cache_dir else DEFAULT_ASSEMBLY_CACHE_DIR
        target_path = cd / "osm_turkey_emergency_assembly_point_latest.json"
        try:
            snapshot_path, actual_size, actual_sha256 = fetch_osm_assembly_snapshot(
                target_path
            )
            strict_checksum = False
            strict_contract = False
        except Exception as exc:
            logger.error("Download of OSM assembly points failed: %s", exc)
            return 1
    else:
        if not snapshot_path_str:
            logger.error("Must specify either --snapshot <path> or --download.")
            return 1
        snapshot_path = Path(snapshot_path_str).resolve()
        if not snapshot_path.is_file():
            logger.error("Snapshot file not found: %s", snapshot_path)
            return 1
        strict_checksum = True
        strict_contract = True

    logger.info("Target OSM Snapshot: %s", snapshot_path)

    try:
        with SessionLocal() as session:
            service = AssemblyImportService(session)
            stats = service.import_osm_snapshot(
                snapshot_path=snapshot_path,
                strict_checksum=strict_checksum,
                strict_contract=strict_contract,
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
        if strict_checksum:
            print(f"Verified Checksum     : {OSM_EXPECTED_SHA256} (SHA-256)")
            print(f"Verified Size         : {OSM_EXPECTED_SIZE_BYTES} bytes")
        else:
            print(f"Captured Checksum     : {actual_sha256} (SHA-256)")
            print(f"Captured Size         : {actual_size} bytes")
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
            "an approved snapshot or via live fetch."
        )
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--snapshot",
        type=str,
        help="Path to the approved Overpass JSON snapshot file.",
    )
    group.add_argument(
        "--download",
        action="store_true",
        help="Download latest OSM emergency assembly points from Overpass API.",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        help="Directory to store snapshot [default: backend/data/cache/assembly]",
    )
    args = parser.parse_args()
    sys.exit(
        run_assembly_import(
            snapshot_path_str=args.snapshot,
            download=args.download,
            cache_dir=args.cache_dir,
        )
    )


if __name__ == "__main__":
    main()
