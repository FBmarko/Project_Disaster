"""Unit tests for AssemblyArea SQLAlchemy models and schema structure."""

import uuid
from datetime import UTC, datetime

from geoalchemy2.elements import WKTElement

from app.main import app
from app.models.assembly_area import AssemblyArea
from app.models.assembly_area_dataset import AssemblyAreaDataset


def test_assembly_area_dataset_model_instantiation() -> None:
    """Verify AssemblyAreaDataset model attributes and default values."""
    ds = AssemblyAreaDataset(
        source="OpenStreetMap",
        provider="OpenStreetMap contributors",
        source_classification="community_open_data",
        license="ODbL 1.0",
        attribution="© OpenStreetMap contributors",
        source_reference="https://www.openstreetmap.org/copyright",
        snapshot_retrieved_at=datetime.now(UTC),
        source_data_timestamp=datetime.now(UTC),
        snapshot_sha256="23b86cfc29f30a47ca49c4e0037c4bcf914066870d06d234d53b64be2a46c340",
        snapshot_size_bytes=179012,
        source_endpoint="https://overpass-api.de/api/interpreter",
        extraction_query="[out:json]; node['emergency'='assembly_point'];",
        source_metadata={"feature_count": 678},
    )
    assert ds.source == "OpenStreetMap"
    assert ds.provider == "OpenStreetMap contributors"
    assert ds.license == "ODbL 1.0"
    assert ds.snapshot_size_bytes == 179012
    assert ds.snapshot_sha256.startswith("23b86cfc")


def test_assembly_area_model_instantiation() -> None:
    """Verify AssemblyArea model attributes, geometry, and source properties."""
    dataset_id = uuid.uuid4()
    area = AssemblyArea(
        dataset_id=dataset_id,
        source_feature_id="node/4284118948",
        name="Demokrasi Parkı Toplanma Alanı",
        ref="5902-007-07",
        operator="AFAD",
        geometry=WKTElement("POINT(28.97 41.01)", srid=4326),
        source_properties={"emergency": "assembly_point", "leisure": "park"},
    )
    assert area.dataset_id == dataset_id
    assert area.source_feature_id == "node/4284118948"
    assert area.name == "Demokrasi Parkı Toplanma Alanı"
    assert area.ref == "5902-007-07"
    assert area.operator == "AFAD"
    assert isinstance(area.geometry, WKTElement)
    assert area.source_properties == {"emergency": "assembly_point", "leisure": "park"}


def test_assembly_area_dataset_table_args() -> None:
    """Verify natural identity unique constraint on AssemblyAreaDataset."""
    table_args = AssemblyAreaDataset.__table_args__
    uq_names = [arg.name for arg in table_args if hasattr(arg, "name")]
    assert "uq_assembly_area_datasets_natural_key" in uq_names


def test_assembly_area_table_args() -> None:
    """Verify unique constraint and indexes on AssemblyArea."""
    table_args = AssemblyArea.__table_args__
    names = [arg.name for arg in table_args if hasattr(arg, "name")]
    assert "uq_assembly_areas_dataset_feature" in names
    assert "idx_assembly_areas_geometry" in names
    assert "idx_assembly_areas_dataset_id" in names


def test_assembly_area_columns_created_at_and_updated_at() -> None:
    """Verify that assembly_areas contains created_at and updated_at columns.

    Both must be timezone-aware timestamps and NOT NULL.
    """
    cols = AssemblyArea.__table__.columns
    assert "created_at" in cols
    assert "updated_at" in cols

    created_at_col = cols["created_at"]
    assert created_at_col.nullable is False
    assert getattr(created_at_col.type, "timezone", False) is True
    assert created_at_col.server_default is not None

    updated_at_col = cols["updated_at"]
    assert updated_at_col.nullable is False
    assert getattr(updated_at_col.type, "timezone", False) is True
    assert updated_at_col.server_default is not None
    assert updated_at_col.onupdate is not None


def test_assembly_api_routes_exposed() -> None:
    """OpenAPI schema must strictly contain 14 paths and exactly 3 assembly routes."""
    openapi_paths = list(app.openapi()["paths"].keys())
    assert len(openapi_paths) == 14
    assembly_paths = [p for p in openapi_paths if "assembly" in p.lower()]
    assert len(assembly_paths) == 3
    assert "/api/v1/assembly-areas/dataset" in assembly_paths
    assert "/api/v1/assembly-areas/nearby" in assembly_paths
    assert "/api/v1/assembly-areas" in assembly_paths
