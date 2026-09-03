"""Safe reader and validator for official GEM GSHM GeoPackage artifacts."""

import hashlib
import logging
import sqlite3
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

from app.integrations.gem.hazard_constants import (
    GEM_GPKG_SIZE_BYTES,
    GEM_ZIP_MD5,
    GEM_ZIP_SIZE_BYTES,
    TURKEY_CONTEXT_BBOX,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GemHazardRecord:
    """Validated raw point record from GEM GSHM GeoPackage."""

    fid: int
    longitude: float
    latitude: float
    pga_g: float


def verify_zip_artifact(zip_path: Path) -> None:
    """Verify local GEM GSHM ZIP archive size and MD5 checksum.

    Note: MD5 is used solely for artifact integrity matching against Zenodo metadata.
    """
    if not zip_path.is_file():
        raise FileNotFoundError(f"Source ZIP archive does not exist: {zip_path}")

    actual_size = zip_path.stat().st_size
    if actual_size != GEM_ZIP_SIZE_BYTES:
        err = (
            f"Source ZIP size mismatch: expected {GEM_ZIP_SIZE_BYTES} bytes, "
            f"got {actual_size}"
        )
        raise ValueError(err)

    logger.info("Verifying MD5 checksum of %s...", zip_path.name)
    hasher = hashlib.md5()
    with open(zip_path, "rb") as f:
        while chunk := f.read(4 * 1024 * 1024):
            hasher.update(chunk)

    actual_md5 = hasher.hexdigest()
    if actual_md5 != GEM_ZIP_MD5:
        err = (
            f"Source ZIP MD5 checksum mismatch: expected {GEM_ZIP_MD5}, "
            f"got {actual_md5}"
        )
        raise ValueError(err)
    logger.info("Source ZIP MD5 checksum verified successfully: %s", actual_md5)


def verify_geopackage_metadata(gpkg_path: Path, check_full_size: bool = True) -> None:
    """Verify GeoPackage schema, layer, CRS, and RTree index in read-only mode."""
    if not gpkg_path.is_file():
        raise FileNotFoundError(f"Source GeoPackage does not exist: {gpkg_path}")

    if check_full_size:
        actual_size = gpkg_path.stat().st_size
        if actual_size != GEM_GPKG_SIZE_BYTES:
            err = (
                f"Source GeoPackage size mismatch: expected {GEM_GPKG_SIZE_BYTES} "
                f"bytes, got {actual_size}"
            )
            raise ValueError(err)

    uri = f"file:{gpkg_path.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        cur = conn.cursor()

        # 1. Verify gpkg_contents has layer v2026 with SRS 4326
        contents_query = (
            "SELECT table_name, data_type, srs_id FROM gpkg_contents "
            "WHERE table_name = 'v2026'"
        )
        cur.execute(contents_query)
        row = cur.fetchone()
        if not row or row[0] != "v2026" or row[2] != 4326:
            err = (
                f"GeoPackage contents missing expected layer 'v2026' "
                f"in EPSG:4326: {row}"
            )
            raise ValueError(err)

        # 2. Verify gpkg_geometry_columns has POINT geometry
        geom_query = (
            "SELECT column_name, geometry_type_name, srs_id "
            "FROM gpkg_geometry_columns WHERE table_name = 'v2026'"
        )
        cur.execute(geom_query)
        geom_row = cur.fetchone()
        if (
            not geom_row
            or geom_row[0] != "geom"
            or geom_row[1] != "POINT"
            or geom_row[2] != 4326
        ):
            raise ValueError(
                f"GeoPackage geometry column invalid for 'v2026': {geom_row}"
            )

        # 3. Verify columns exist on v2026
        cur.execute('PRAGMA table_info("v2026")')
        cols = {r[1] for r in cur.fetchall()}
        required_cols = {"fid", "geom", "lon", "lat", "pga"}
        if not required_cols.issubset(cols):
            missing = required_cols - cols
            raise ValueError(f"GeoPackage table 'v2026' missing columns: {missing}")

        # 4. Verify RTree virtual table exists
        rtree_check = (
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name = 'rtree_v2026_geom'"
        )
        cur.execute(rtree_check)
        if not cur.fetchone():
            raise ValueError(
                "GeoPackage missing required RTree index table 'rtree_v2026_geom'"
            )

        logger.info(
            "GeoPackage schema and spatial indexing verified for 'v2026' layer."
        )
    finally:
        conn.close()


def stream_turkey_hazard_records(
    gpkg_path: Path,
    bbox: tuple[float, float, float, float] = TURKEY_CONTEXT_BBOX,
    batch_size: int = 5000,
) -> Generator[list[GemHazardRecord], None, None]:
    """Stream validated records within bbox using GeoPackage RTree index."""
    min_lon, min_lat, max_lon, max_lat = bbox

    uri = f"file:{gpkg_path.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        cur = conn.cursor()

        # Check if rtree_v2026_geom exists, otherwise fallback to bbox predicate
        rtree_check = (
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name = 'rtree_v2026_geom'"
        )
        cur.execute(rtree_check)
        has_rtree = cur.fetchone() is not None

        if has_rtree:
            query = """
                SELECT fid, lon, lat, pga FROM v2026
                WHERE fid IN (
                    SELECT id FROM rtree_v2026_geom
                    WHERE minx <= ? AND maxx >= ? AND miny <= ? AND maxy >= ?
                )
            """
            params = (max_lon, min_lon, max_lat, min_lat)
        else:
            query = """
                SELECT fid, lon, lat, pga FROM v2026
                WHERE lon >= ? AND lon <= ? AND lat >= ? AND lat <= ?
            """
            params = (min_lon, max_lon, min_lat, max_lat)

        cur.execute(query, params)

        while True:
            rows = cur.fetchmany(batch_size)
            if not rows:
                break

            records: list[GemHazardRecord] = []
            for fid, lon, lat, pga in rows:
                if fid is None or lon is None or lat is None or pga is None:
                    err = (
                        f"Encountered NULL attribute in row fid={fid}: "
                        f"lon={lon}, lat={lat}, pga={pga}"
                    )
                    raise ValueError(err)
                if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
                    err = (
                        f"Point out of requested bounding box: "
                        f"({lon}, {lat}) for fid={fid}"
                    )
                    raise ValueError(err)
                if pga < 0:
                    raise ValueError(f"Negative PGA encountered: {pga} for fid={fid}")

                records.append(
                    GemHazardRecord(
                        fid=int(fid),
                        longitude=float(lon),
                        latitude=float(lat),
                        pga_g=float(pga),
                    )
                )

            yield records
    finally:
        conn.close()
