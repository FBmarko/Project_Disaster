import argparse
import hashlib
import logging
import sys
import urllib.request
import zipfile
from pathlib import Path

from app.db.session import SessionLocal
from app.integrations.gem.hazard_constants import (
    GEM_DOWNLOAD_URL,
    GEM_GPKG_FILENAME,
    GEM_GPKG_RELPATH,
    GEM_GPKG_SIZE_BYTES,
    GEM_SOURCE_NAME,
    GEM_SOURCE_VERSION,
    GEM_ZIP_FILENAME,
    GEM_ZIP_MD5,
    GEM_ZIP_SIZE_BYTES,
    TURKEY_CONTEXT_BBOX,
    TURKEY_CONTEXT_SCOPE,
)
from app.services.hazard_import import HazardImportService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("afet360.import_gem_hazard")

DEFAULT_HAZARD_CACHE_DIR = (
    Path(__file__).parent.parent.parent / "data" / "cache" / "hazard"
)


def download_and_extract_gshm(
    cache_dir: Path,
    url: str = GEM_DOWNLOAD_URL,
    expected_size: int = GEM_ZIP_SIZE_BYTES,
    expected_md5: str = GEM_ZIP_MD5,
    expected_gpkg_size: int = GEM_GPKG_SIZE_BYTES,
    timeout: float = 600.0,
) -> tuple[Path, Path | None]:
    """Download official GEM GSHM ZIP archive and extract the GeoPackage.

    Validates MD5 checksum and byte size. Reuses valid existing cached files.

    Returns:
        tuple of (resolved_gpkg_path, resolved_zip_path)
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    target_zip = cache_dir / GEM_ZIP_FILENAME
    target_gpkg = cache_dir / GEM_GPKG_FILENAME
    gpkg_nested = cache_dir / GEM_GPKG_RELPATH

    # Check if a valid extracted GeoPackage already exists
    for candidate in [gpkg_nested, target_gpkg]:
        if candidate.is_file() and candidate.stat().st_size == expected_gpkg_size:
            logger.info(
                "Found valid cached GeoPackage (%d bytes): %s",
                expected_gpkg_size,
                candidate,
            )
            return candidate, (target_zip if target_zip.is_file() else None)

    # Check if a valid ZIP archive already exists in cache
    need_download = True
    if target_zip.is_file():
        actual_zip_size = target_zip.stat().st_size
        if actual_zip_size == expected_size:
            logger.info("Verifying existing cached ZIP archive: %s ...", target_zip)
            hasher = hashlib.md5()
            with open(target_zip, "rb") as f_zip:
                while chunk := f_zip.read(1024 * 1024):
                    hasher.update(chunk)
            if hasher.hexdigest().lower() == expected_md5.lower():
                logger.info(
                    "Cached ZIP archive is valid (%s). Skipping download.", expected_md5
                )
                need_download = False
            else:
                logger.warning("Cached ZIP MD5 mismatch. Removing corrupt file.")
                target_zip.unlink(missing_ok=True)
        else:
            logger.warning(
                "Cached ZIP size mismatch (%d != %d). Removing partial/corrupt file.",
                actual_zip_size,
                expected_size,
            )
            target_zip.unlink(missing_ok=True)

    if need_download:
        part_zip = cache_dir / f"{GEM_ZIP_FILENAME}.part"
        if part_zip.is_file():
            part_zip.unlink(missing_ok=True)

        logger.info("Downloading official GEM GSHM archive from %s ...", url)
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "AFET360-Importer/0.1.0"},
        )
        hasher = hashlib.md5()
        downloaded = 0
        last_logged = 0

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                with open(part_zip, "wb") as f_out:
                    while True:
                        chunk = resp.read(1024 * 1024)
                        if not chunk:
                            break
                        hasher.update(chunk)
                        f_out.write(chunk)
                        downloaded += len(chunk)
                        if downloaded - last_logged >= 100 * 1024 * 1024:
                            pct = (
                                (downloaded / expected_size) * 100
                                if expected_size
                                else 0
                            )
                            logger.info(
                                "Downloaded %d / %d MB (%.1f%%)",
                                downloaded // (1024 * 1024),
                                expected_size // (1024 * 1024),
                                pct,
                            )
                            last_logged = downloaded
        except Exception as exc:
            part_zip.unlink(missing_ok=True)
            raise RuntimeError(
                f"Failed to download GEM GSHM archive from {url}: {exc}"
            ) from exc

        actual_md5 = hasher.hexdigest().lower()
        if downloaded != expected_size:
            part_zip.unlink(missing_ok=True)
            raise ValueError(
                f"Downloaded ZIP size mismatch: expected {expected_size} bytes, "
                f"got {downloaded} bytes."
            )
        if actual_md5 != expected_md5.lower():
            part_zip.unlink(missing_ok=True)
            raise ValueError(
                f"Downloaded ZIP MD5 checksum mismatch: expected {expected_md5}, "
                f"got {actual_md5}."
            )

        part_zip.replace(target_zip)
        logger.info("Successfully downloaded and verified ZIP: %s", target_zip)

    # Extract GeoPackage from validated ZIP
    logger.info("Extracting %s from %s ...", GEM_GPKG_FILENAME, target_zip)
    part_gpkg = cache_dir / f"{GEM_GPKG_FILENAME}.part"
    if part_gpkg.is_file():
        part_gpkg.unlink(missing_ok=True)

    try:
        with zipfile.ZipFile(target_zip, "r") as zf:
            matching = [
                n
                for n in zf.namelist()
                if n == GEM_GPKG_RELPATH or n.endswith(GEM_GPKG_FILENAME)
            ]
            if not matching:
                raise FileNotFoundError(f"Archive does not contain {GEM_GPKG_FILENAME}")
            member = matching[0]

            with zf.open(member) as zf_in, open(part_gpkg, "wb") as gpkg_out:
                while True:
                    chunk = zf_in.read(2 * 1024 * 1024)
                    if not chunk:
                        break
                    gpkg_out.write(chunk)
    except Exception as exc:
        part_gpkg.unlink(missing_ok=True)
        raise RuntimeError(
            f"Failed to extract GeoPackage from {target_zip}: {exc}"
        ) from exc

    extracted_size = part_gpkg.stat().st_size
    if extracted_size != expected_gpkg_size:
        part_gpkg.unlink(missing_ok=True)
        raise ValueError(
            f"Extracted GeoPackage size mismatch: expected {expected_gpkg_size} bytes, "
            f"got {extracted_size} bytes."
        )

    part_gpkg.replace(target_gpkg)
    logger.info("Successfully extracted and verified GeoPackage: %s", target_gpkg)
    return target_gpkg, target_zip


def run_hazard_import(
    cache_dir: str | None = None,
    gpkg_path: str | None = None,
    zip_path: str | None = None,
    download: bool = False,
    verify_zip: bool = True,
    batch_size: int = 5000,
) -> int:
    """Execute the GEM hazard dataset import workflow."""
    resolved_gpkg: Path | None = None
    resolved_zip: Path | None = None

    if download:
        cd = Path(cache_dir) if cache_dir else DEFAULT_HAZARD_CACHE_DIR
        try:
            resolved_gpkg, resolved_zip = download_and_extract_gshm(cd)
        except Exception as exc:
            logger.error("Download or extraction of GEM hazard data failed: %s", exc)
            return 1
    else:
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
                    "GeoPackage file not found in cache directory %s. "
                    "Checked: %s and %s",
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
                "Must specify either --download, or --cache-dir containing %s, "
                "or direct --gpkg-path.",
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
        "--download",
        action="store_true",
        help="Download official GEM GSHM archive from Zenodo and extract GeoPackage",
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
        download=args.download,
        verify_zip=not args.skip_zip_verify,
        batch_size=args.batch_size,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
