import uuid

from geoalchemy2.elements import WKTElement

from app.models.earthquake_hazard_point import EarthquakeHazardPoint
from app.models.hazard_dataset import HazardDataset


def test_hazard_dataset_model_instantiation() -> None:
    """Verify HazardDataset model attributes and default values."""
    ds = HazardDataset(
        source="GEM_GSHM",
        source_version="2026.1",
        model_name="GEM Global Seismic Hazard Map v2026.1",
        hazard_metric="PGA",
        unit="g",
        return_period_years=475,
        exceedance_probability=0.10,
        time_horizon_years=50,
        reference_vs30_mps=800.0,
        reference_ground="Reference Rock",
        version_doi="10.5281/zenodo.20735384",
        concept_doi="10.5281/zenodo.8409646",
        license="CC BY-NC-SA 4.0",
        attribution="GEM Attribution Text",
        source_artifact="gshm_v2026_1_vector.zip",
        source_artifact_size_bytes=935540326,
        source_checksum_algorithm="md5",
        source_checksum_value="7470e54534f4a4307a7310aa766ab11b",
        ingest_scope="turkey-context",
        scope_min_longitude=24.0,
        scope_min_latitude=34.0,
        scope_max_longitude=46.0,
        scope_max_latitude=44.0,
    )
    assert ds.source == "GEM_GSHM"
    assert ds.return_period_years == 475
    assert ds.hazard_metric == "PGA"
    assert ds.unit == "g"
    assert ds.reference_vs30_mps == 800.0
    assert ds.ingest_scope == "turkey-context"


def test_earthquake_hazard_point_model_instantiation() -> None:
    """Verify EarthquakeHazardPoint model attributes and WKT geometry."""
    dataset_id = uuid.uuid4()
    point = EarthquakeHazardPoint(
        dataset_id=dataset_id,
        source_record_id=12345,
        longitude=35.5,
        latitude=39.0,
        pga_g=0.25,
        geometry=WKTElement("POINT(35.5 39.0)", srid=4326),
    )
    assert point.dataset_id == dataset_id
    assert point.source_record_id == 12345
    assert point.longitude == 35.5
    assert point.latitude == 39.0
    assert point.pga_g == 0.25
    assert isinstance(point.geometry, WKTElement)


def test_hazard_dataset_table_args() -> None:
    """Verify unique constraint is defined on HazardDataset."""
    table_args = HazardDataset.__table_args__
    uq_names = [arg.name for arg in table_args if hasattr(arg, "name")]
    assert "uq_hazard_datasets_natural_key" in uq_names


def test_earthquake_hazard_point_table_args() -> None:
    """Verify constraints and GiST index are defined on EarthquakeHazardPoint."""
    table_args = EarthquakeHazardPoint.__table_args__
    names = [arg.name for arg in table_args if hasattr(arg, "name")]
    assert "uq_hazard_points_dataset_coords" in names
    assert "idx_earthquake_hazard_points_geometry" in names
    assert "chk_hazard_points_longitude" in names
    assert "chk_hazard_points_latitude" in names
