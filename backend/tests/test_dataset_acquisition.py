"""Deterministic offline unit tests for dataset acquisition workflows."""

import hashlib
import io
import json
import urllib.error
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.integrations.gem.hazard_constants import (
    GEM_DOWNLOAD_URL,
    GEM_GPKG_FILENAME,
    GEM_GPKG_RELPATH,
    GEM_ZIP_FILENAME,
)
from app.integrations.osm.osm_constants import OSM_ENDPOINT, OSM_EXTRACTION_QUERY
from app.scripts.import_gem_hazard import download_and_extract_gshm
from app.scripts.import_osm_assembly_areas import fetch_osm_assembly_snapshot
from app.scripts.provision_datasets import run_provision_static

# =====================================================================
# GSHM Acquisition Tests (Offline & Deterministic)
# =====================================================================


def test_download_and_extract_gshm_reuses_valid_cached_gpkg(tmp_path: Path) -> None:
    """Verify that an existing valid GeoPackage is reused immediately."""
    cache_dir = tmp_path / "hazard_cache"
    cache_dir.mkdir()
    fake_gpkg = cache_dir / GEM_GPKG_FILENAME
    fake_gpkg.write_bytes(b"G" * 1000)

    gpkg_path, zip_path = download_and_extract_gshm(
        cache_dir=cache_dir,
        expected_gpkg_size=1000,
        expected_size=500,
        expected_md5="abc",
    )
    assert gpkg_path == fake_gpkg
    assert zip_path is None


def test_download_and_extract_gshm_reuses_valid_cached_zip(tmp_path: Path) -> None:
    """Verify that an existing valid ZIP archive is extracted without re-downloading."""
    cache_dir = tmp_path / "hazard_cache"
    cache_dir.mkdir()

    # Create a real small ZIP containing the GeoPackage
    gpkg_content = b"GEOPACKAGE_DATA_12345"
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(GEM_GPKG_RELPATH, gpkg_content)
    zip_bytes = zip_buffer.getvalue()

    zip_size = len(zip_bytes)
    zip_md5 = hashlib.md5(zip_bytes).hexdigest()
    gpkg_size = len(gpkg_content)

    cached_zip = cache_dir / GEM_ZIP_FILENAME
    cached_zip.write_bytes(zip_bytes)

    # Should not invoke urllib
    with patch("urllib.request.urlopen") as mock_urlopen:
        gpkg_path, res_zip = download_and_extract_gshm(
            cache_dir=cache_dir,
            expected_size=zip_size,
            expected_md5=zip_md5,
            expected_gpkg_size=gpkg_size,
        )
        assert mock_urlopen.call_count == 0

    assert gpkg_path.is_file()
    assert gpkg_path.read_bytes() == gpkg_content
    assert res_zip == cached_zip


def test_download_and_extract_gshm_streams_and_verifies_checksum(
    tmp_path: Path,
) -> None:
    """Verify streaming download into .part and atomic rename upon valid checksum."""
    cache_dir = tmp_path / "hazard_cache"

    gpkg_content = b"STREAMED_GPKG_CONTENT_999"
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(GEM_GPKG_RELPATH, gpkg_content)
    zip_bytes = zip_buffer.getvalue()

    zip_size = len(zip_bytes)
    zip_md5 = hashlib.md5(zip_bytes).hexdigest()
    gpkg_size = len(gpkg_content)

    mock_resp = io.BytesIO(zip_bytes)

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        gpkg_path, res_zip = download_and_extract_gshm(
            cache_dir=cache_dir,
            url=GEM_DOWNLOAD_URL,
            expected_size=zip_size,
            expected_md5=zip_md5,
            expected_gpkg_size=gpkg_size,
        )
        assert mock_urlopen.call_count == 1

    assert gpkg_path.is_file()
    assert gpkg_path.read_bytes() == gpkg_content
    assert res_zip is not None and res_zip.is_file()
    # Ensure temporary .part files were cleaned up
    assert not (cache_dir / f"{GEM_ZIP_FILENAME}.part").exists()
    assert not (cache_dir / f"{GEM_GPKG_FILENAME}.part").exists()


def test_download_and_extract_gshm_rejects_corrupt_checksum(
    tmp_path: Path,
) -> None:
    """Verify checksum mismatch aborts, cleans .part, and does not promote."""
    cache_dir = tmp_path / "hazard_cache"
    corrupt_data = b"CORRUPT_BYTES"

    mock_resp = io.BytesIO(corrupt_data)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        with pytest.raises(ValueError, match="MD5 checksum mismatch|size mismatch"):
            download_and_extract_gshm(
                cache_dir=cache_dir,
                expected_size=len(corrupt_data),
                expected_md5="expected_different_md5",
                expected_gpkg_size=100,
            )

    # Corrupt target files must not exist
    assert not (cache_dir / GEM_ZIP_FILENAME).exists()
    assert not (cache_dir / f"{GEM_ZIP_FILENAME}.part").exists()
    assert not (cache_dir / GEM_GPKG_FILENAME).exists()


def test_download_and_extract_gshm_handles_network_error(tmp_path: Path) -> None:
    """Verify network error raises RuntimeError and leaves cache directory clean."""
    cache_dir = tmp_path / "hazard_cache"

    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError("Connection reset"),
    ):
        with pytest.raises(RuntimeError, match="Failed to download GEM GSHM"):
            download_and_extract_gshm(
                cache_dir=cache_dir,
                expected_size=100,
                expected_md5="abc",
                expected_gpkg_size=50,
            )

    assert not (cache_dir / GEM_ZIP_FILENAME).exists()
    assert not (cache_dir / f"{GEM_ZIP_FILENAME}.part").exists()


# =====================================================================
# OSM Acquisition Tests (Offline & Deterministic)
# =====================================================================


def test_fetch_osm_assembly_snapshot_success(tmp_path: Path) -> None:
    """Verify Overpass API query execution, validation, and hash calculation."""
    dest_path = tmp_path / "osm_cache" / "assembly.json"
    valid_payload = json.dumps(
        {
            "version": 0.6,
            "generator": "Overpass API",
            "elements": [
                {
                    "type": "node",
                    "id": 1001,
                    "lat": 39.9,
                    "lon": 32.8,
                    "tags": {"emergency": "assembly_point", "name": "Test Point"},
                }
            ],
        }
    ).encode("utf-8")

    expected_sha256 = hashlib.sha256(valid_payload).hexdigest()
    expected_size = len(valid_payload)

    mock_resp = io.BytesIO(valid_payload)

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        promoted, size, sha256_hex = fetch_osm_assembly_snapshot(
            dest_path=dest_path,
            endpoint=OSM_ENDPOINT,
            query=OSM_EXTRACTION_QUERY,
        )
        assert mock_urlopen.call_count == 1
        req = mock_urlopen.call_args[0][0]
        # Verify query was posted
        assert req.full_url == OSM_ENDPOINT
        assert b"ISO3166-1" in req.data

    assert promoted == dest_path
    assert promoted.is_file()
    assert size == expected_size
    assert sha256_hex == expected_sha256
    assert not (tmp_path / "osm_cache" / "assembly.json.part").exists()


def test_fetch_osm_assembly_snapshot_rejects_malformed_json(tmp_path: Path) -> None:
    """Verify that non-JSON or invalid schema Overpass responses are rejected."""
    dest_path = tmp_path / "osm_cache" / "assembly.json"
    malformed_payload = b"<html><head><title>Rate Limit Exceeded</title></head></html>"

    mock_resp = io.BytesIO(malformed_payload)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        with pytest.raises(ValueError, match="Failed to validate Overpass JSON"):
            fetch_osm_assembly_snapshot(dest_path=dest_path)

    assert not dest_path.exists()
    assert not (tmp_path / "osm_cache" / "assembly.json.part").exists()


def test_fetch_osm_assembly_snapshot_handles_network_error(tmp_path: Path) -> None:
    """Verify network error raises RuntimeError and cleans up part file."""
    dest_path = tmp_path / "osm_cache" / "assembly.json"

    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.HTTPError(
            url=OSM_ENDPOINT, code=504, msg="Gateway Timeout", hdrs=None, fp=None
        ),
    ):
        with pytest.raises(RuntimeError, match="Failed to query Overpass API"):
            fetch_osm_assembly_snapshot(dest_path=dest_path)

    assert not dest_path.exists()
    assert not (tmp_path / "osm_cache" / "assembly.json.part").exists()


# =====================================================================
# Unified Provisioning CLI Integration Tests
# =====================================================================


def test_provision_static_download_hazard_delegates() -> None:
    """Verify --download-hazard delegates to run_hazard_import with download=True."""
    with (
        patch(
            "app.scripts.provision_datasets.run_hazard_import", return_value=0
        ) as mock_hazard,
        patch(
            "app.scripts.provision_datasets.run_status", return_value=0
        ) as mock_status,
    ):
        code = run_provision_static(download_hazard=True)
        assert code == 0
        mock_hazard.assert_called_once_with(
            cache_dir=None,
            gpkg_path=None,
            zip_path=None,
            download=True,
            verify_zip=True,
        )
        mock_status.assert_called_once()


def test_provision_static_download_assembly_delegates() -> None:
    """Verify --download-assembly calls run_assembly_import(download=True)."""
    with (
        patch(
            "app.scripts.provision_datasets.run_assembly_import", return_value=0
        ) as mock_assembly,
        patch(
            "app.scripts.provision_datasets.run_status", return_value=0
        ) as mock_status,
    ):
        code = run_provision_static(download_assembly=True)
        assert code == 0
        mock_assembly.assert_called_once_with(
            snapshot_path_str=None,
            download=True,
        )
        mock_status.assert_called_once()


def test_provision_static_download_all_delegates() -> None:
    """Verify --download-all triggers download on all static datasets."""
    with (
        patch(
            "app.scripts.provision_datasets.run_faults_import", return_value=0
        ) as mock_faults,
        patch(
            "app.scripts.provision_datasets.run_hazard_import", return_value=0
        ) as mock_hazard,
        patch(
            "app.scripts.provision_datasets.run_assembly_import", return_value=0
        ) as mock_assembly,
        patch(
            "app.scripts.provision_datasets.run_status", return_value=0
        ) as mock_status,
    ):
        code = run_provision_static(download_all=True)
        assert code == 0
        mock_faults.assert_called_once_with(
            file_path=None,
            download=True,
            scope="turkey-only",
        )
        mock_hazard.assert_called_once_with(
            cache_dir=None,
            gpkg_path=None,
            zip_path=None,
            download=True,
            verify_zip=True,
        )
        mock_assembly.assert_called_once_with(
            snapshot_path_str=None,
            download=True,
        )
        mock_status.assert_called_once()
