"""Unit and integration tests for the public Earthquake Hazards REST API."""

import math
import re
import socket
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import engine
from app.main import app
from app.models.earthquake_hazard_point import EarthquakeHazardPoint
from app.models.hazard_dataset import HazardDataset
from app.repositories.earthquake_hazard import EarthquakeHazardRepository


def is_postgres_available() -> bool:
    """Fast socket-level connectivity check for PostgreSQL."""
    try:
        with socket.create_connection(
            (settings.POSTGRES_HOST, settings.POSTGRES_PORT), timeout=0.5
        ):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def skip_if_database_unavailable() -> None:
    if not is_postgres_available():
        pytest.skip("PostgreSQL/PostGIS container is not reachable.")


@pytest.fixture
def isolated_session() -> Generator[Session, None, None]:
    """Provide an isolated database session within a transaction that rolls back."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


client = TestClient(app)


def test_get_hazard_dataset_metadata() -> None:
    """Verify GET /api/v1/earthquake-hazards/dataset returns persisted metadata."""
    response = client.get("/api/v1/earthquake-hazards/dataset")
    assert response.status_code == 200
    data = response.json()

    assert data["source"] == "GEM_GSHM"
    assert data["source_version"] == "2026.1"
    assert "Global Seismic Hazard Map" in data["model_name"]
    assert data["hazard_metric"] == "PGA"
    assert data["unit"] == "g"
    assert data["return_period_years"] == 475
    assert math.isclose(data["exceedance_probability"], 0.10, abs_tol=1e-6)
    assert data["time_horizon_years"] == 50
    assert math.isclose(data["reference_vs30_mps"], 800.0, abs_tol=1e-6)
    assert data["reference_ground"] == "Reference Rock"
    assert data["version_doi"] == "10.5281/zenodo.20735384"
    assert data["concept_doi"] == "10.5281/zenodo.8409646"
    assert data["license"] == "CC BY-NC-SA 4.0"
    assert "Global Earthquake Model" in data["attribution"]
    assert data["ingest_scope"] == "turkey-context"
    assert data["scope"]["min_longitude"] == 24.0
    assert data["scope"]["min_latitude"] == 34.0
    assert data["scope"]["max_longitude"] == 46.0
    assert data["scope"]["max_latitude"] == 44.0
    assert data["point_count"] == 54291
    assert data["data_delivery"] == "local_imported_reference_dataset"
    assert data["source_artifact"] == "gshm_v2026_1_vector.zip"
    assert data["source_checksum_algorithm"] == "md5"
    assert data["source_checksum_value"] == "7470e54534f4a4307a7310aa766ab11b"


def test_nearest_hazard_valid_locations() -> None:
    """Verify GET /api/v1/earthquake-hazards/nearest for representative hubs."""
    test_cases = [
        ("Ankara", 39.93, 32.85),
        ("Istanbul", 41.00, 29.00),
        ("Izmir", 38.42, 27.14),
        ("Van", 38.50, 43.38),
        ("BoundaryMin", 34.01, 24.01),
        ("BoundaryMax", 43.99, 45.99),
    ]

    for name, lat, lon in test_cases:
        resp = client.get(f"/api/v1/earthquake-hazards/nearest?lat={lat}&lon={lon}")
        assert resp.status_code == 200, f"Failed for {name}: {resp.text}"
        body = resp.json()

        assert body["type"] == "Feature"
        assert body["geometry"]["type"] == "Point"
        node_lon, node_lat = body["geometry"]["coordinates"]
        assert 24.0 <= node_lon <= 46.0
        assert 34.0 <= node_lat <= 44.0

        props = body["properties"]
        assert props["semantics"] == "nearest_source_node"
        assert props["pga_g"] > 0.0
        assert props["distance_to_source_node_km"] >= 0.0

        meta = body["metadata"]
        assert math.isclose(meta["query"]["latitude"], lat, abs_tol=1e-6)
        assert math.isclose(meta["query"]["longitude"], lon, abs_tol=1e-6)
        assert meta["source"] == "GEM_GSHM"
        assert meta["hazard_metric"] == "PGA"
        assert meta["unit"] == "g"
        assert "reference rock" in meta["disclaimer"].lower()


def test_nearest_hazard_exact_node_match(
    isolated_session: Session,
) -> None:
    """Verify querying an exact source node returns zero distance and matching PGA."""
    repo = EarthquakeHazardRepository(isolated_session)
    dataset = repo.get_active_gem_dataset()
    assert dataset is not None

    point = (
        isolated_session.query(EarthquakeHazardPoint)
        .filter(EarthquakeHazardPoint.dataset_id == dataset.id)
        .first()
    )
    assert point is not None

    resp = client.get(
        f"/api/v1/earthquake-hazards/nearest?lat={point.latitude}&lon={point.longitude}"
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["properties"]["id"] == str(point.id)
    assert math.isclose(
        data["properties"]["distance_to_source_node_km"], 0.0, abs_tol=1e-4
    )
    assert math.isclose(data["properties"]["pga_g"], point.pga_g, abs_tol=1e-9)
    assert math.isclose(
        data["geometry"]["coordinates"][0], point.longitude, abs_tol=1e-7
    )
    assert math.isclose(
        data["geometry"]["coordinates"][1], point.latitude, abs_tol=1e-7
    )


def test_nearest_hazard_coordinate_scope_validation() -> None:
    """Verify 422 when coordinates fall outside imported Türkiye-context scope."""
    out_of_bounds = [
        (39.0, 23.9),  # lon below 24
        (39.0, 46.1),  # lon above 46
        (33.9, 35.0),  # lat below 34
        (44.1, 35.0),  # lat above 44
        (95.0, 30.0),  # lat out of world bounds
        (35.0, -190.0),  # lon out of world bounds
    ]

    for lat, lon in out_of_bounds:
        resp = client.get(f"/api/v1/earthquake-hazards/nearest?lat={lat}&lon={lon}")
        assert resp.status_code == 422, f"Expected 422 for ({lat}, {lon})"
        assert "outside" in resp.text.lower() or "between" in resp.text.lower()


def test_nearest_hazard_malformed_params() -> None:
    """Verify 422 for missing or non-numeric query parameters."""
    assert client.get("/api/v1/earthquake-hazards/nearest").status_code == 422
    assert (
        client.get("/api/v1/earthquake-hazards/nearest?lat=abc&lon=35.0").status_code
        == 422
    )
    assert (
        client.get("/api/v1/earthquake-hazards/nearest?lat=38.0&lon=xyz").status_code
        == 422
    )


def test_scientific_disclaimer_language_safety() -> None:
    """Verify that public disclaimers strictly avoid forbidden/misleading claims."""
    resp = client.get("/api/v1/earthquake-hazards/nearest?lat=39.93&lon=32.85")
    assert resp.status_code == 200
    disclaimer = resp.json()["metadata"]["disclaimer"].lower()

    # Forbidden claims (checked with word boundaries or phrases)
    prohibited_patterns = [
        r"exact site pga",
        r"\bsafe\b",
        r"\bunsafe\b",
        r"earthquake prediction",
        r"earthquake will",
        r"\bcaused by\b",
        r"high risk",
        r"low risk",
    ]
    for pattern in prohibited_patterns:
        match = re.search(pattern, disclaimer)
        assert match is None, (
            f"Prohibited pattern '{pattern}' matched in disclaimer: '{disclaimer}'"
        )

    # Required scientific terms
    assert "nearest" in disclaimer
    assert "reference rock" in disclaimer
    assert "vs30 = 800" in disclaimer or "800 m/s" in disclaimer


def test_nearest_correctness_vs_geography_baseline(
    isolated_session: Session,
) -> None:
    """Verify production 32-candidate KNN matches exact geography scan across sample."""
    repo = EarthquakeHazardRepository(isolated_session)
    dataset = repo.get_active_gem_dataset()
    assert dataset is not None

    test_points = [
        (26.0, 37.0),
        (28.5, 41.2),
        (30.0, 36.5),
        (32.8, 39.9),
        (35.2, 42.0),
        (38.0, 38.0),
        (40.5, 39.5),
        (43.0, 37.5),
        (44.8, 41.0),
        (24.5, 34.5),
    ]

    for lon, lat in test_points:
        # Production query
        prod_result = repo.find_nearest_hazard_point(
            dataset.id, lon, lat, candidate_count=32
        )
        assert prod_result is not None

        # Exact full geography baseline query
        base_sql = text("""
            SELECT id, pga_g,
                   ST_Distance(
                       geometry::geography,
                       ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                   ) / 1000.0 AS distance_km
            FROM earthquake_hazard_points
            WHERE dataset_id = :ds_id
            ORDER BY ST_Distance(
                geometry::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
            ), id
            LIMIT 1;
        """)
        base_result = (
            isolated_session.execute(
                base_sql, {"ds_id": dataset.id, "lon": lon, "lat": lat}
            )
            .mappings()
            .first()
        )
        assert base_result is not None

        # Point IDs must match 100%
        err_msg = (
            f"Mismatch at ({lon}, {lat}): "
            f"prod={prod_result['id']} vs base={base_result['id']}"
        )
        assert prod_result["id"] == base_result["id"], err_msg
        # Distance must be within 1mm (1e-6 km)
        assert math.isclose(
            prod_result["distance_km"],
            base_result["distance_km"],
            abs_tol=1e-6,
        )


def test_bbox_endpoint_valid_viewport() -> None:
    """Verify GET /api/v1/earthquake-hazards returns points inside requested bbox."""
    bbox_str = "28.8,40.9,29.2,41.2"
    resp = client.get(f"/api/v1/earthquake-hazards?bbox={bbox_str}&limit=50")
    assert resp.status_code == 200
    data = resp.json()

    assert data["type"] == "FeatureCollection"
    assert data["metadata"]["bbox"] == [28.8, 40.9, 29.2, 41.2]
    assert data["metadata"]["limit"] == 50
    assert data["metadata"]["offset"] == 0
    assert data["metadata"]["count"] == len(data["features"])

    for feat in data["features"]:
        assert feat["type"] == "Feature"
        assert feat["geometry"]["type"] == "Point"
        lon, lat = feat["geometry"]["coordinates"]
        assert 28.8 <= lon <= 29.2
        assert 40.9 <= lat <= 41.2
        assert feat["properties"]["pga_g"] > 0.0


def test_bbox_endpoint_pagination() -> None:
    """Verify pagination limit, offset, and stable ordering."""
    bbox_str = "27.0,40.0,30.0,41.5"  # Marmara region (~1049 points)

    # Page 1
    resp1 = client.get(f"/api/v1/earthquake-hazards?bbox={bbox_str}&limit=20&offset=0")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert len(data1["features"]) == 20
    assert data1["metadata"]["has_more"] is True

    # Page 2
    resp2 = client.get(f"/api/v1/earthquake-hazards?bbox={bbox_str}&limit=20&offset=20")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["features"]) == 20

    # IDs between page 1 and page 2 must be mutually exclusive
    ids_page1 = {f["properties"]["id"] for f in data1["features"]}
    ids_page2 = {f["properties"]["id"] for f in data2["features"]}
    assert ids_page1.isdisjoint(ids_page2)


def test_bbox_endpoint_validation_failures() -> None:
    """Verify 422 for malformed, inverted, or out-of-scope bounding boxes."""
    # Missing bbox
    assert client.get("/api/v1/earthquake-hazards").status_code == 422

    # Malformed (3 numbers instead of 4)
    assert (
        client.get("/api/v1/earthquake-hazards?bbox=28.0,40.0,30.0").status_code == 422
    )

    # Non-numeric
    assert client.get("/api/v1/earthquake-hazards?bbox=a,b,c,d").status_code == 422

    # Inverted min_lon >= max_lon
    assert (
        client.get("/api/v1/earthquake-hazards?bbox=30.0,40.0,28.0,41.0").status_code
        == 422
    )

    # Inverted min_lat >= max_lat
    assert (
        client.get("/api/v1/earthquake-hazards?bbox=28.0,42.0,30.0,40.0").status_code
        == 422
    )

    # Outside Türkiye-context scope
    assert (
        client.get("/api/v1/earthquake-hazards?bbox=10.0,35.0,20.0,40.0").status_code
        == 422
    )

    # Invalid limit (0 or > 2000)
    assert (
        client.get(
            "/api/v1/earthquake-hazards?bbox=28.0,40.0,30.0,41.0&limit=0"
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/api/v1/earthquake-hazards?bbox=28.0,40.0,30.0,41.0&limit=2500"
        ).status_code
        == 422
    )

    # Negative offset
    assert (
        client.get(
            "/api/v1/earthquake-hazards?bbox=28.0,40.0,30.0,41.0&offset=-5"
        ).status_code
        == 422
    )


def test_bbox_endpoint_empty_viewport() -> None:
    """Verify 200 with empty features when viewport contains no points."""
    # Narrow box between grid nodes
    bbox_str = "28.000,40.000,28.001,40.001"
    resp = client.get(f"/api/v1/earthquake-hazards?bbox={bbox_str}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["features"] == []
    assert data["metadata"]["count"] == 0
    assert data["metadata"]["has_more"] is False


def test_missing_dataset_service_unavailable() -> None:
    """Verify all 3 hazard endpoints return 503 when active dataset is missing."""
    from app.db.dependencies import get_db

    def override_get_db() -> Generator[Session, None, None]:
        connection = engine.connect()
        transaction = connection.begin()
        session = Session(bind=connection)
        try:
            session.execute(
                text(
                    "DELETE FROM earthquake_hazard_points; DELETE FROM hazard_datasets;"
                )
            )
            yield session
        finally:
            session.close()
            transaction.rollback()
            connection.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        # 1. Dataset metadata endpoint
        resp_ds = client.get("/api/v1/earthquake-hazards/dataset")
        assert resp_ds.status_code == 503
        assert resp_ds.json()["detail"] == (
            "Earthquake hazard dataset is currently unavailable."
        )

        # 2. Nearest endpoint
        resp_nr = client.get("/api/v1/earthquake-hazards/nearest?lat=39.93&lon=32.85")
        assert resp_nr.status_code == 503
        assert resp_nr.json()["detail"] == (
            "Earthquake hazard dataset is currently unavailable."
        )

        # 3. Bbox endpoint
        resp_bb = client.get("/api/v1/earthquake-hazards?bbox=28.0,40.0,30.0,42.0")
        assert resp_bb.status_code == 503
        assert resp_bb.json()["detail"] == (
            "Earthquake hazard dataset is currently unavailable."
        )
    finally:
        app.dependency_overrides.clear()


def test_nearest_hazard_tie_break_determinism(
    isolated_session: Session,
) -> None:
    """Verify deterministic tie-breaking by id when source nodes are equidistant."""
    import uuid

    from geoalchemy2.elements import WKTElement

    # Rotational symmetry around polar axis ensures exact equal spheroidal distance
    ds_id = uuid.uuid4()
    dataset = HazardDataset(
        id=ds_id,
        source="TEST_GSHM",
        source_version="1.0",
        model_name="Test Model",
        hazard_metric="PGA",
        unit="g",
        return_period_years=475,
        exceedance_probability=0.10,
        time_horizon_years=50,
        reference_vs30_mps=800.0,
        reference_ground="Reference Rock",
        version_doi="10.5281/test.1",
        concept_doi="10.5281/test.concept",
        license="CC BY-NC-SA 4.0",
        attribution="Test Attribution",
        source_artifact="test.zip",
        source_artifact_size_bytes=1000,
        source_checksum_algorithm="md5",
        source_checksum_value="abc",
        ingest_scope="test-scope",
        scope_min_longitude=24.0,
        scope_min_latitude=34.0,
        scope_max_longitude=46.0,
        scope_max_latitude=44.0,
    )
    isolated_session.add(dataset)
    isolated_session.flush()

    id_lower = uuid.UUID("00000000-0000-0000-0000-000000000001")
    id_higher = uuid.UUID("00000000-0000-0000-0000-000000000002")

    # Symmetric east/west points along parallel lat=38.0
    pt_east = EarthquakeHazardPoint(
        id=id_higher,
        dataset_id=ds_id,
        source_record_id=1,
        longitude=30.01,
        latitude=38.0,
        pga_g=0.25,
        geometry=WKTElement("POINT(30.01 38.0)", srid=4326),
    )
    pt_west = EarthquakeHazardPoint(
        id=id_lower,
        dataset_id=ds_id,
        source_record_id=2,
        longitude=29.99,
        latitude=38.0,
        pga_g=0.25,
        geometry=WKTElement("POINT(29.99 38.0)", srid=4326),
    )
    isolated_session.add_all([pt_east, pt_west])
    isolated_session.flush()

    repo = EarthquakeHazardRepository(isolated_session)

    # Query repeatedly at (30.0, 38.0)
    for _ in range(5):
        result = repo.find_nearest_hazard_point(
            ds_id, longitude=30.0, latitude=38.0, candidate_count=10
        )
        assert result is not None
        assert result["id"] == id_lower


def test_nearest_hazard_query_plan_uses_gist_index(
    isolated_session: Session,
) -> None:
    """Verify EXPLAIN plan for nearest query uses the GiST spatial index."""
    repo = EarthquakeHazardRepository(isolated_session)
    dataset = repo.get_active_gem_dataset()
    assert dataset is not None

    explain_sql = text("""
        EXPLAIN
        WITH candidates AS (
            SELECT id, source_record_id, longitude, latitude, pga_g, geometry
            FROM earthquake_hazard_points
            WHERE dataset_id = :dataset_id
            ORDER BY geometry <-> ST_SetSRID(
                ST_MakePoint(:longitude, :latitude), 4326
            )
            LIMIT :candidate_count
        )
        SELECT id, source_record_id, longitude, latitude, pga_g,
               ST_Distance(
                   geometry::geography,
                   ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography
               ) / 1000.0 AS distance_km
        FROM candidates
        ORDER BY distance_km, id
        LIMIT 1;
    """)
    rows = isolated_session.execute(
        explain_sql,
        {
            "dataset_id": dataset.id,
            "longitude": 32.85,
            "latitude": 39.93,
            "candidate_count": 32,
        },
    ).fetchall()
    plan_text = " ".join(r[0] for r in rows)
    assert "idx_earthquake_hazard_points_geometry" in plan_text
