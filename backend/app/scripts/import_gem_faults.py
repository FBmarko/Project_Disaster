import argparse
import json
import logging
import sys
import time
import urllib.request
from pathlib import Path

from app.db.session import SessionLocal
from app.integrations.gem.mapping import TURKEY_CONTEXT_BBOX
from app.services.fault_import import FaultImportService

OFFICIAL_GEM_RAW_URL = (
    "https://raw.githubusercontent.com/GEMScienceTools/gem-global-active-faults"
    "/master/geojson/gem_active_faults.geojson"
)

BOUNDARY_FILE_PATH = (
    Path(__file__).parent.parent.parent / "data" / "turkey_boundary.geojson"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("afet360.import_gem_faults")


def load_turkey_boundary_geometry() -> dict:
    """Load the Natural Earth 1:50m generalized Türkiye country boundary polygon."""
    if not BOUNDARY_FILE_PATH.exists():
        raise FileNotFoundError(
            f"Türkiye boundary file not found at: {BOUNDARY_FILE_PATH}"
        )
    with open(BOUNDARY_FILE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    features = data.get("features", [])
    if not features or "geometry" not in features[0]:
        raise ValueError("Invalid boundary GeoJSON: missing geometry in feature")
    return features[0]["geometry"]


def run_import(
    file_path: str | None = None,
    download: bool = False,
    scope: str = "turkey-only",
    batch_size: int = 250,
) -> int:
    """Execute the GEM fault import workflow with explicit geographic scope."""
    if file_path:
        path = Path(file_path)
        if not path.exists():
            logger.error("Source file does not exist: %s", path)
            return 1
        logger.info("Reading GEM active faults from local file: %s", path)
        try:
            with open(path, encoding="utf-8") as f:
                geojson_data = json.load(f)
        except Exception as e:
            logger.error("Failed to parse JSON file %s: %s", path, e)
            return 1
    elif download:
        logger.info(
            "Downloading GEM active faults from official repository: %s",
            OFFICIAL_GEM_RAW_URL,
        )
        last_err = None
        geojson_data = None
        for attempt in range(1, 4):
            try:
                logger.info("Attempt %d/3 to download GEM active faults...", attempt)
                req = urllib.request.Request(
                    OFFICIAL_GEM_RAW_URL,
                    headers={"User-Agent": "AFET360-Importer/0.1.0"},
                )
                with urllib.request.urlopen(req, timeout=60) as resp:
                    geojson_data = json.loads(resp.read().decode("utf-8"))
                break
            except Exception as e:
                last_err = e
                logger.warning("Download attempt %d failed: %s", attempt, e)
                time.sleep(2 * attempt)

        if geojson_data is None:
            logger.error(
                "Failed to download GEM GeoJSON after 3 attempts: %s", last_err
            )
            return 1
    else:
        logger.error("Must specify either --file <path> or --download.")
        return 1

    # Configure geographic scope
    bbox = None
    boundary_geom = None

    if scope == "turkey-only":
        bbox = TURKEY_CONTEXT_BBOX
        try:
            boundary_geom = load_turkey_boundary_geometry()
            logger.info(
                "Loaded Türkiye boundary geometry for spatial intersection filtering."
            )
        except Exception as e:
            logger.error("Could not load Türkiye boundary geometry: %s", e)
            return 1
    elif scope == "turkey-context":
        bbox = TURKEY_CONTEXT_BBOX
        logger.info("Applying regional tectonic bounding box: %s", bbox)
    else:
        logger.info("No geographic filtering applied (importing all features).")

    logger.info(
        "Beginning import (scope=%s, batch_size=%d)...",
        scope,
        batch_size,
    )

    try:
        with SessionLocal() as session:
            service = FaultImportService(session)
            stats = service.import_gem_geojson(
                geojson_data,
                bbox=bbox,
                boundary_geometry=boundary_geom,
                batch_size=batch_size,
            )
            session.commit()

        print("\n==========================================")
        print("      GEM FAULT IMPORT SUMMARY")
        print("==========================================")
        print(f"Scope                 : {scope}")
        print(f"Total Source Features : {stats.total_source_features}")
        print(f"Inserted              : {stats.inserted}")
        print(f"Updated               : {stats.updated}")
        print(f"Unchanged             : {stats.unchanged}")
        print(f"Skipped (filtered out): {stats.skipped}")
        print(f"Failed (validation)   : {stats.failed}")
        print("==========================================\n")
        return 0
    except Exception as e:
        logger.exception("Fatal error during fault import transaction: %s", e)
        return 2


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AFET360 GEM Global Active Faults Import Command",
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--file",
        "-f",
        type=str,
        help="Path to local GEM GeoJSON file",
    )
    source_group.add_argument(
        "--download",
        "-d",
        action="store_true",
        help="Download official GEM GeoJSON directly from GitHub",
    )

    scope_group = parser.add_mutually_exclusive_group()
    scope_group.add_argument(
        "--turkey-only",
        action="store_const",
        dest="scope",
        const="turkey-only",
        default="turkey-only",
        help="Filter faults intersecting Natural Earth 1:50m boundary [default]",
    )
    scope_group.add_argument(
        "--turkey-context",
        action="store_const",
        dest="scope",
        const="turkey-context",
        help="Filter faults in regional tectonic context bbox (24-46°E, 34-44°N)",
    )
    scope_group.add_argument(
        "--all",
        action="store_const",
        dest="scope",
        const="all",
        help="Import all worldwide features without geographic filtering",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=250,
        help="Database upsert batch size [default: 250]",
    )

    args = parser.parse_args()
    exit_code = run_import(
        file_path=args.file,
        download=args.download,
        scope=args.scope,
        batch_size=args.batch_size,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
