"""AFET360 Dataset Provisioning and Status Inspection CLI.

Provides a unified, non-destructive operator workflow to:
1. Inspect the readiness of required non-migration datasets (read-only).
2. Explicitly provision static datasets (faults, GSHM hazard, assembly areas)
   using authoritative existing import services.

Note: AFAD earthquake event synchronization is dynamic and network-dependent;
it is maintained separately via `app.scripts.sync_afad_earthquakes`.
"""

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.earthquake_event import EarthquakeEvent
from app.models.earthquake_hazard_point import EarthquakeHazardPoint
from app.models.fault_segment import FaultSegment
from app.repositories.assembly_area import AssemblyAreaRepository
from app.repositories.earthquake_hazard import EarthquakeHazardRepository
from app.scripts.import_gem_faults import run_import as run_faults_import
from app.scripts.import_gem_hazard import run_hazard_import
from app.scripts.import_osm_assembly_areas import run_assembly_import

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("afet360.provision_datasets")


def inspect_dataset_readiness(session: Session) -> dict[str, Any]:
    """Perform read-only inspection of all database datasets.

    Evaluates dataset presence, metadata identity, geometry validity, and row counts.
    Readiness is based on semantic validity (>0 valid records, metadata integrity)
    rather than hardcoding temporary historical observation counts.

    Returns:
        Structured dictionary containing per-dataset status and overall readiness.
    """
    # 1. Fault Segments (Static)
    fault_count = session.execute(select(func.count(FaultSegment.id))).scalar() or 0
    fault_valid_geom_count = (
        session.execute(
            select(func.count())
            .select_from(FaultSegment)
            .where(func.ST_IsValid(FaultSegment.geometry))
        ).scalar()
        or 0
    )
    fault_srid_count = (
        session.execute(
            select(func.count())
            .select_from(FaultSegment)
            .where(func.ST_SRID(FaultSegment.geometry) == 4326)
        ).scalar()
        or 0
    )
    fault_sources = (
        session.execute(select(FaultSegment.source).distinct()).scalars().all()
    )

    fault_ready = bool(
        fault_count > 0
        and fault_valid_geom_count == fault_count
        and fault_srid_count == fault_count
        and "GEM_GAF" in fault_sources
    )

    faults_status = {
        "dataset_type": "static",
        "ready": fault_ready,
        "count": fault_count,
        "valid_geometry_count": fault_valid_geom_count,
        "srid_4326_count": fault_srid_count,
        "sources": fault_sources,
    }

    # 2. GEM Global Seismic Hazard Map (Static)
    hazard_repo = EarthquakeHazardRepository(session)
    active_gshm = hazard_repo.get_active_gem_dataset()

    if active_gshm is not None:
        gshm_points_count = hazard_repo.count_points_for_dataset(active_gshm.id)
        pga_stats = session.execute(
            select(
                func.min(EarthquakeHazardPoint.pga_g),
                func.max(EarthquakeHazardPoint.pga_g),
            ).where(EarthquakeHazardPoint.dataset_id == active_gshm.id)
        ).fetchone()
        min_pga = pga_stats[0] if pga_stats else None
        max_pga = pga_stats[1] if pga_stats else None

        gshm_ready = bool(
            gshm_points_count > 0
            and min_pga is not None
            and min_pga > 0
            and max_pga is not None
            and max_pga > min_pga
        )

        gshm_status = {
            "dataset_type": "static",
            "ready": gshm_ready,
            "dataset_id": str(active_gshm.id),
            "source": active_gshm.source,
            "source_version": active_gshm.source_version,
            "hazard_metric": active_gshm.hazard_metric,
            "unit": active_gshm.unit,
            "return_period_years": active_gshm.return_period_years,
            "exceedance_probability": active_gshm.exceedance_probability,
            "reference_vs30_mps": active_gshm.reference_vs30_mps,
            "license": active_gshm.license,
            "points_count": gshm_points_count,
            "min_pga_g": float(min_pga) if min_pga is not None else None,
            "max_pga_g": float(max_pga) if max_pga is not None else None,
        }
    else:
        gshm_status = {
            "dataset_type": "static",
            "ready": False,
            "dataset_id": None,
            "source": "GEM_GSHM",
            "source_version": "2026.1",
            "points_count": 0,
            "note": "No active GEM GSHM dataset record found.",
        }

    # 3. Emergency Assembly Areas (Static)
    assembly_repo = AssemblyAreaRepository(session)
    active_assembly = assembly_repo.get_current_osm_dataset()

    if active_assembly is not None:
        total_areas, pts_count, polys_count = (
            assembly_repo.get_geometry_counts_for_dataset(active_assembly.id)
        )
        assembly_ready = bool(
            total_areas > 0 and (pts_count + polys_count) == total_areas
        )

        assembly_status = {
            "dataset_type": "static",
            "ready": assembly_ready,
            "dataset_id": str(active_assembly.id),
            "source": active_assembly.source,
            "provider": active_assembly.provider,
            "license": active_assembly.license,
            "snapshot_sha256": active_assembly.snapshot_sha256,
            "snapshot_size_bytes": active_assembly.snapshot_size_bytes,
            "total_areas": total_areas,
            "point_features": pts_count,
            "polygon_features": polys_count,
        }
    else:
        assembly_status = {
            "dataset_type": "static",
            "ready": False,
            "dataset_id": None,
            "source": "OpenStreetMap",
            "total_areas": 0,
            "note": "No active OpenStreetMap assembly dataset record found.",
        }

    # 4. Earthquake Events (Dynamic Catalog)
    eq_count = session.execute(select(func.count(EarthquakeEvent.id))).scalar() or 0
    time_bounds = session.execute(
        select(
            func.min(EarthquakeEvent.occurred_at),
            func.max(EarthquakeEvent.occurred_at),
        )
    ).fetchone()
    earliest_eq = time_bounds[0] if time_bounds else None
    latest_eq = time_bounds[1] if time_bounds else None
    eq_sources = (
        session.execute(select(EarthquakeEvent.source).distinct()).scalars().all()
    )

    earthquakes_ready = bool(eq_count > 0)

    earthquakes_status = {
        "dataset_type": "dynamic",
        "ready": earthquakes_ready,
        "count": eq_count,
        "earliest_event": earliest_eq.isoformat() if earliest_eq else None,
        "latest_event": latest_eq.isoformat() if latest_eq else None,
        "sources": eq_sources,
        "note": (
            "Dynamic rolling catalog. Row count reflects current local snapshot "
            "and is updated via app.scripts.sync_afad_earthquakes."
        ),
    }

    all_static_ready = (
        faults_status["ready"] and gshm_status["ready"] and assembly_status["ready"]
    )
    overall_ready = all_static_ready and earthquakes_ready

    return {
        "inspected_at": datetime.now(UTC).isoformat(),
        "overall_ready": overall_ready,
        "all_static_ready": all_static_ready,
        "datasets": {
            "faults": faults_status,
            "gshm_hazard": gshm_status,
            "assembly_areas": assembly_status,
            "earthquakes": earthquakes_status,
        },
    }


def format_status_text(report: dict[str, Any]) -> str:
    """Format readiness report into human-readable console text."""
    overall_str = "READY" if report["overall_ready"] else "NOT READY"
    static_str = "ALL READY" if report["all_static_ready"] else "INCOMPLETE"
    lines = [
        "=" * 64,
        "              AFET360 DATASET READINESS STATUS",
        "=" * 64,
        f"Inspected At      : {report['inspected_at']}",
        f"Overall Readiness : {overall_str}",
        f"Static Datasets   : {static_str}",
        "-" * 64,
    ]

    # 1. Faults
    f = report["datasets"]["faults"]
    f_badge = "[READY]" if f.get("ready") else "[NOT READY]"
    sources_str = ", ".join(f.get("sources", [])) if f.get("sources") else "None"
    lines.extend(
        [
            f"1. Active Faults (Static) {f_badge}",
            f"   Sources        : {sources_str}",
            f"   Total Features : {f.get('count', 0):,}",
            f"   Valid PostGIS  : {f.get('valid_geometry_count', 0):,}",
            f"   SRID 4326      : {f.get('srid_4326_count', 0):,}",
            "-" * 64,
        ]
    )

    # 2. GSHM Hazard
    h = report["datasets"]["gshm_hazard"]
    h_badge = "[READY]" if h.get("ready") else "[NOT READY]"
    gshm_src = f"{h.get('source', 'GEM_GSHM')} {h.get('source_version', '')}".strip()
    prob = h.get("exceedance_probability")
    prob_str = f"{prob * 100:.1f}% / 50 yr" if prob is not None else "N/A"
    metric_str = f"{h.get('hazard_metric', 'PGA')} ({h.get('unit', 'g')})"
    rp_str = f"{h.get('return_period_years', 'N/A')} yr ({prob_str})"
    pga_range = f"{h.get('min_pga_g', 'N/A')} - {h.get('max_pga_g', 'N/A')}"
    lines.extend(
        [
            f"2. GEM GSHM Seismic Hazard (Static) {h_badge}",
            f"   Source/Version : {gshm_src}",
            f"   Dataset ID     : {h.get('dataset_id', 'None')}",
            f"   Hazard Metric  : {metric_str}",
            f"   Return Period  : {rp_str}",
            f"   Ref Site Vs30  : {h.get('reference_vs30_mps', 'N/A')} m/s (rock)",
            f"   Hazard Points  : {h.get('points_count', 0):,}",
            f"   PGA Range (g)  : {pga_range}",
            "-" * 64,
        ]
    )

    # 3. Assembly Areas
    a = report["datasets"]["assembly_areas"]
    a_badge = "[READY]" if a.get("ready") else "[NOT READY]"
    osm_prov = f"{a.get('source', 'OSM')} / {a.get('provider', 'N/A')}"
    lines.extend(
        [
            f"3. Emergency Assembly Areas (Static) {a_badge}",
            f"   Source/Provider: {osm_prov}",
            f"   Dataset ID     : {a.get('dataset_id', 'None')}",
            f"   License        : {a.get('license', 'ODbL 1.0')}",
            f"   Total Areas    : {a.get('total_areas', 0):,}",
            f"   Point Nodes    : {a.get('point_features', 0):,}",
            f"   Polygon Ways   : {a.get('polygon_features', 0):,}",
            "-" * 64,
        ]
    )

    # 4. Earthquakes
    e = report["datasets"]["earthquakes"]
    e_badge = "[READY]" if e.get("ready") else "[NOT READY]"
    eq_sources_str = ", ".join(e.get("sources", [])) if e.get("sources") else "None"
    cov_span = f"{e.get('earliest_event', 'N/A')} -> {e.get('latest_event', 'N/A')}"
    lines.extend(
        [
            f"4. Earthquake Catalog (Dynamic) {e_badge}",
            f"   Sources        : {eq_sources_str}",
            f"   Total Events   : {e.get('count', 0):,}",
            f"   Coverage Span  : {cov_span}",
            f"   Note           : {e.get('note', 'Dynamic rolling catalog.')}",
            "=" * 64,
        ]
    )
    return "\n".join(lines)


def run_status(as_json: bool = False, check_exit: bool = False) -> int:
    """Execute read-only dataset status inspection.

    Args:
        as_json: If True, outputs JSON to stdout.
        check_exit: If True, exits non-zero if static datasets are not ready.

    Returns:
        0 on success, 1 if check_exit is requested and static datasets are unready.
    """
    with SessionLocal() as session:
        report = inspect_dataset_readiness(session)

    if as_json:
        print(json.dumps(report, indent=2))
    else:
        print(format_status_text(report))

    if check_exit and not report["all_static_ready"]:
        return 1
    return 0


def run_provision_static(
    faults_file: str | None = None,
    download_faults: bool = False,
    faults_scope: str = "turkey-only",
    gshm_gpkg: str | None = None,
    gshm_cache_dir: str | None = None,
    gshm_zip: str | None = None,
    download_hazard: bool = False,
    skip_gshm_zip_verify: bool = False,
    assembly_snapshot: str | None = None,
    download_assembly: bool = False,
    download_all: bool = False,
) -> int:
    """Execute operator provisioning for specified static datasets.

    Validates file existence upfront, delegates to authoritative importers,
    and reports per-dataset outcome.

    Returns:
        0 on full success, non-zero exit code if any import fails or inputs are invalid.
    """
    if download_all:
        download_faults = True
        download_hazard = True
        download_assembly = True

    has_faults = bool(faults_file or download_faults)
    has_gshm = bool(gshm_gpkg or gshm_cache_dir or download_hazard)
    has_assembly = bool(assembly_snapshot or download_assembly)

    if not (has_faults or has_gshm or has_assembly):
        logger.error(
            "No static datasets specified for provisioning.\n"
            "Provide at least one of:\n"
            "  --faults-file <path> OR --download-faults\n"
            "  --gshm-gpkg <path> OR --gshm-cache-dir <dir> OR --download-hazard\n"
            "  --assembly-snapshot <path> OR --download-assembly\n"
            "  OR --download-all"
        )
        return 1

    # Validate local files exist before starting any long operations
    if faults_file and not Path(faults_file).is_file():
        logger.error("Specified faults file not found: %s", faults_file)
        return 1

    if gshm_gpkg and not Path(gshm_gpkg).is_file():
        logger.error("Specified GSHM GeoPackage not found: %s", gshm_gpkg)
        return 1

    if gshm_cache_dir and not Path(gshm_cache_dir).is_dir():
        logger.error("Specified GSHM cache directory not found: %s", gshm_cache_dir)
        return 1

    if gshm_zip and not Path(gshm_zip).is_file():
        logger.error("Specified GSHM ZIP archive not found: %s", gshm_zip)
        return 1

    if assembly_snapshot and not Path(assembly_snapshot).is_file():
        logger.error(
            "Specified OSM assembly snapshot file not found: %s", assembly_snapshot
        )
        return 1

    results: dict[str, str] = {}

    # 1. Provision Faults
    if has_faults:
        logger.info(">>> Provisioning GEM Active Faults (scope=%s)...", faults_scope)
        code = run_faults_import(
            file_path=faults_file,
            download=download_faults,
            scope=faults_scope,
        )
        if code != 0:
            logger.error("Faults import failed with exit code %d", code)
            results["faults"] = f"FAILED (exit code {code})"
            return code
        results["faults"] = "SUCCESS"

    # 2. Provision GSHM Hazard
    if has_gshm:
        logger.info(">>> Provisioning GEM GSHM Seismic Hazard Dataset...")
        code = run_hazard_import(
            cache_dir=gshm_cache_dir,
            gpkg_path=gshm_gpkg,
            zip_path=gshm_zip,
            download=download_hazard,
            verify_zip=not skip_gshm_zip_verify,
        )
        if code != 0:
            logger.error("GSHM hazard import failed with exit code %d", code)
            results["gshm_hazard"] = f"FAILED (exit code {code})"
            return code
        results["gshm_hazard"] = "SUCCESS"

    # 3. Provision Assembly Areas
    if has_assembly:
        logger.info(">>> Provisioning OSM Emergency Assembly Areas...")
        code = run_assembly_import(
            snapshot_path_str=assembly_snapshot,
            download=download_assembly,
        )
        if code != 0:
            logger.error("Assembly areas import failed with exit code %d", code)
            results["assembly_areas"] = f"FAILED (exit code {code})"
            return code
        results["assembly_areas"] = "SUCCESS"

    print("\n==========================================")
    print("   STATIC DATASET PROVISIONING COMPLETE   ")
    print("==========================================")
    for ds_name, outcome in results.items():
        print(f"  {ds_name:<20}: {outcome}")
    print("==========================================\n")

    # Run read-only status verification to display updated state
    return run_status(as_json=False, check_exit=False)


def main() -> None:
    """CLI parser and router."""
    parser = argparse.ArgumentParser(
        description="AFET360 Dataset Provisioning and Readiness Inspection CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # Subcommand: status
    status_parser = subparsers.add_parser(
        "status",
        help="Inspect current dataset readiness in the database (read-only)",
    )
    status_parser.add_argument(
        "--json",
        action="store_true",
        help="Output inspection results in JSON format",
    )
    status_parser.add_argument(
        "--check",
        action="store_true",
        help="Exit with non-zero code if any static dataset is unready",
    )

    # Subcommand: provision-static
    prov_parser = subparsers.add_parser(
        "provision-static",
        help="Explicitly provision static datasets (faults, GSHM, assembly)",
    )
    prov_parser.add_argument(
        "--download-all",
        action="store_true",
        help="Download and provision all static datasets (faults, hazard, assembly)",
    )
    # Faults group
    f_group = prov_parser.add_mutually_exclusive_group(required=False)
    f_group.add_argument(
        "--faults-file",
        type=str,
        help="Path to local GEM active faults GeoJSON file",
    )
    f_group.add_argument(
        "--download-faults",
        action="store_true",
        help="Download official GEM active faults GeoJSON from GitHub",
    )
    prov_parser.add_argument(
        "--faults-scope",
        choices=["turkey-only", "turkey-context", "all"],
        default="turkey-only",
        help="Geographic scope for fault spatial filtering [default: turkey-only]",
    )

    # GSHM group
    prov_parser.add_argument(
        "--download-hazard",
        action="store_true",
        help="Download official GEM GSHM archive from Zenodo and extract GeoPackage",
    )
    prov_parser.add_argument(
        "--gshm-gpkg",
        type=str,
        help="Direct path to GEM GSHM GeoPackage (gem_gshm_v2026.1.gpkg)",
    )
    prov_parser.add_argument(
        "--gshm-cache-dir",
        type=str,
        help="Path to directory containing GSHM GeoPackage and/or ZIP archive",
    )
    prov_parser.add_argument(
        "--gshm-zip",
        type=str,
        help="Path to gshm_v2026_1_vector.zip for checksum verification",
    )
    prov_parser.add_argument(
        "--skip-gshm-zip-verify",
        action="store_true",
        help="Skip MD5 checksum verification of the GSHM ZIP archive",
    )

    # Assembly group
    prov_parser.add_argument(
        "--download-assembly",
        action="store_true",
        help="Download latest OSM emergency assembly points from Overpass API",
    )
    prov_parser.add_argument(
        "--assembly-snapshot",
        type=str,
        help="Path to approved Overpass JSON snapshot for assembly areas",
    )

    args = parser.parse_args()

    if args.subcommand == "status":
        sys.exit(run_status(as_json=args.json, check_exit=args.check))
    elif args.subcommand == "provision-static":
        sys.exit(
            run_provision_static(
                faults_file=args.faults_file,
                download_faults=args.download_faults,
                faults_scope=args.faults_scope,
                gshm_gpkg=args.gshm_gpkg,
                gshm_cache_dir=args.gshm_cache_dir,
                gshm_zip=args.gshm_zip,
                download_hazard=args.download_hazard,
                skip_gshm_zip_verify=args.skip_gshm_zip_verify,
                assembly_snapshot=args.assembly_snapshot,
                download_assembly=args.download_assembly,
                download_all=args.download_all,
            )
        )


if __name__ == "__main__":
    main()
