"""Unit and integration tests for public Assembly Area REST API endpoints."""

import socket
import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from geoalchemy2.elements import WKTElement
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.dependencies import get_db
from app.db.session import engine
from app.main import app
from app.models.assembly_area import AssemblyArea
from app.models.assembly_area_dataset import AssemblyAreaDataset

pytestmark = pytest.mark.integration


def is_postgres_available() -> bool:
    """Fast socket-level connectivity check for PostgreSQL."""
    try:
        with socket.create_connection(
            (settings.POSTGRES_HOST, settings.POSTGRES_PORT), timeout=0.5
        ):
            return True
    except OSError:
        return False


@pytest.fixture(autouse=True)
def skip_if_database_unavailable() -> None:
    if not is_postgres_available():
        pytest.skip("PostgreSQL/PostGIS container is not reachable.")


@pytest.fixture
def isolated_session() -> Generator[Session, None, None]:
    """Provide a database session within an outer transaction that rolls back."""
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


# ==============================================================================
# 1. DATASET METADATA ENDPOINT TESTS
# ==============================================================================


def test_get_assembly_area_dataset_metadata() -> None:
    """Verify GET /api/v1/assembly-areas/dataset returns provenance metadata."""
    response = client.get("/api/v1/assembly-areas/dataset")
    assert response.status_code == 200

    data = response.json()
    assert data["source"] == "OpenStreetMap"
    assert data["provider"] == "OpenStreetMap contributors"
    assert data["source_classification"] == "community_open_data"
    assert data["license"] == "ODbL 1.0"
    assert data["attribution"] == "© OpenStreetMap contributors"
    assert data["source_reference"] == "https://www.openstreetmap.org/copyright"
    assert data["snapshot_sha256"] == (
        "23b86cfc29f30a47ca49c4e0037c4bcf914066870d06d234d53b64be2a46c340"
    )
    assert data["feature_count"] == 678
    assert data["point_count"] == 650
    assert data["polygon_count"] == 28
    assert data["label_en"] == "community-mapped emergency assembly points"
    assert data["label_tr"] == "OSM'de işaretlenmiş acil durum toplanma noktaları"
    assert len(data["disclaimer"]) > 20

    # Ensure no internal/local file system paths leaked
    serialized = str(data)
    assert "assembly-cache" not in serialized
    assert "LOCALAPPDATA" not in serialized
    assert "osm_turkey_emergency_assembly_point" not in serialized
    assert "source_properties" not in serialized
    assert "extraction_query" not in serialized


# ==============================================================================
# 2. COLLECTION ENDPOINT TESTS (FULL & PAGINATED)
# ==============================================================================


def test_list_assembly_areas_default() -> None:
    """Verify GET /api/v1/assembly-areas returns all 678 features with default limit."""
    response = client.get("/api/v1/assembly-areas")
    assert response.status_code == 200

    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert "metadata" in data

    features = data["features"]
    assert len(features) == 678

    meta = data["metadata"]
    assert meta["returned_count"] == 678
    assert meta["truncated"] is False
    assert meta["source"] == "OpenStreetMap"
    assert meta["license"] == "ODbL 1.0"
    assert meta["attribution"] == "© OpenStreetMap contributors"
    assert meta["source_reference"] == "https://www.openstreetmap.org/copyright"
    assert meta["snapshot_sha256"] == (
        "23b86cfc29f30a47ca49c4e0037c4bcf914066870d06d234d53b64be2a46c340"
    )

    # Check feature count by geometry type
    point_features = [f for f in features if f["geometry"]["type"] == "Point"]
    poly_features = [f for f in features if f["geometry"]["type"] == "Polygon"]
    assert len(point_features) == 650
    assert len(poly_features) == 28

    # Verify RFC 7946 GeoJSON format: Point coordinates are [lon, lat]
    sample_pt = point_features[0]
    assert sample_pt["type"] == "Feature"
    assert "id" in sample_pt
    assert isinstance(sample_pt["geometry"]["coordinates"], list)
    assert len(sample_pt["geometry"]["coordinates"]) == 2
    lon, lat = sample_pt["geometry"]["coordinates"]
    assert -180.0 <= lon <= 180.0
    assert -90.0 <= lat <= 90.0

    # Verify Polygon coordinates structure: list of linear rings [[[lon, lat], ...]]
    sample_poly = poly_features[0]
    assert sample_poly["type"] == "Feature"
    assert "id" in sample_poly
    rings = sample_poly["geometry"]["coordinates"]
    assert isinstance(rings, list)
    assert len(rings) >= 1
    assert len(rings[0]) >= 4
    p_lon, p_lat = rings[0][0]
    assert -180.0 <= p_lon <= 180.0
    assert -90.0 <= p_lat <= 90.0
    # Closed ring: first and last vertices are identical
    assert rings[0][0] == rings[0][-1]

    # Verify property privacy and whitelisting
    allowed_prop_keys = {"source_feature_id", "name", "ref", "operator"}
    for f in features:
        props = f["properties"]
        assert set(props.keys()) == allowed_prop_keys
        assert props["source_feature_id"].startswith(("node/", "way/"))
        # Must NEVER leak internal columns or raw tags
        assert "source_properties" not in props
        assert "dataset_id" not in props
        assert "created_at" not in props
        assert "updated_at" not in props

    # Deterministic order check: source_feature_id ASC
    feature_ids = [f["properties"]["source_feature_id"] for f in features]
    assert feature_ids == sorted(feature_ids)


def test_list_assembly_areas_limit_and_truncation() -> None:
    """Verify limit and truncation flag when limit is smaller than total features."""
    limit = 10
    response = client.get(f"/api/v1/assembly-areas?limit={limit}")
    assert response.status_code == 200

    data = response.json()
    assert len(data["features"]) == limit
    assert data["metadata"]["returned_count"] == limit
    assert data["metadata"]["truncated"] is True


def test_list_assembly_areas_invalid_limit() -> None:
    """Verify validation errors for out-of-range limit."""
    # limit < 1
    resp1 = client.get("/api/v1/assembly-areas?limit=0")
    assert resp1.status_code == 422

    # limit > 2000
    resp2 = client.get("/api/v1/assembly-areas?limit=2001")
    assert resp2.status_code == 422


# ==============================================================================
# 3. BOUNDING BOX SPATIAL FILTER TESTS
# ==============================================================================


def test_list_assembly_areas_bbox_string() -> None:
    """Verify spatial filtering with comma-separated bbox string."""
    # Bbox around central Istanbul
    bbox_str = "28.8,40.9,29.2,41.2"
    response = client.get(f"/api/v1/assembly-areas?bbox={bbox_str}")
    assert response.status_code == 200

    data = response.json()
    assert data["metadata"]["truncated"] is False
    assert 0 < data["metadata"]["returned_count"] < 678

    # All returned points must fall within bbox or intersect it
    for f in data["features"]:
        if f["geometry"]["type"] == "Point":
            lon, lat = f["geometry"]["coordinates"]
            assert 28.8 <= lon <= 29.2
            assert 40.9 <= lat <= 41.2


def test_list_assembly_areas_bbox_with_whitespace() -> None:
    """Verify spatial filtering with whitespace-padded bbox string."""
    response = client.get("/api/v1/assembly-areas?bbox=28.8, 40.9, 29.2, 41.2")
    assert response.status_code == 200
    data = response.json()
    assert 0 < data["metadata"]["returned_count"] < 678


def test_list_assembly_areas_bbox_polygon_intersection() -> None:
    """Verify that polygons intersecting the bbox are returned."""
    # Find a polygon way in Istanbul (way/226421064 is around lon 29.258, lat 41.034)
    response = client.get("/api/v1/assembly-areas?bbox=29.25,41.03,29.27,41.04")
    assert response.status_code == 200
    data = response.json()
    poly_ids = [
        f["properties"]["source_feature_id"]
        for f in data["features"]
        if f["geometry"]["type"] == "Polygon"
    ]
    assert "way/226421064" in poly_ids


def test_list_assembly_areas_empty_bbox() -> None:
    """Verify bbox covering an ocean area returns empty feature collection."""
    response = client.get("/api/v1/assembly-areas?bbox=-50.0,-20.0,-49.0,-19.0")
    assert response.status_code == 200
    data = response.json()
    assert data["features"] == []
    assert data["metadata"]["returned_count"] == 0
    assert data["metadata"]["truncated"] is False


def test_list_assembly_areas_bbox_validation_errors() -> None:
    """Verify 422 HTTP responses for invalid bbox inputs."""
    # Malformed string: not 4 numbers
    resp = client.get("/api/v1/assembly-areas?bbox=28.0,41.0,29.0")
    assert resp.status_code == 422

    # Non-numeric parts
    resp = client.get("/api/v1/assembly-areas?bbox=abc,41.0,29.0,42.0")
    assert resp.status_code == 422

    # min_lon >= max_lon
    resp = client.get("/api/v1/assembly-areas?bbox=30.0,40.0,28.0,41.0")
    assert resp.status_code == 422
    assert "min_lon must be strictly less than max_lon" in resp.json()["detail"]

    # min_lat >= max_lat
    resp = client.get("/api/v1/assembly-areas?bbox=28.0,42.0,30.0,40.0")
    assert resp.status_code == 422
    assert "min_lat must be strictly less than max_lat" in resp.json()["detail"]

    # Longitude out of [-180, 180]
    resp = client.get("/api/v1/assembly-areas?bbox=-190.0,40.0,28.0,41.0")
    assert resp.status_code == 422

    # Latitude out of [-90, 90]
    resp = client.get("/api/v1/assembly-areas?bbox=28.0,40.0,29.0,95.0")
    assert resp.status_code == 422


# ==============================================================================
# 4. NEARBY PROXIMITY ENDPOINT TESTS
# ==============================================================================


def test_get_nearby_assembly_areas_point_zero_distance() -> None:
    """Verify nearby query at exact point location yields distance_km == 0.0."""
    # First fetch one point feature to get exact coordinate
    all_resp = client.get("/api/v1/assembly-areas?limit=1")
    first_feat = all_resp.json()["features"][0]
    expected_id = first_feat["properties"]["source_feature_id"]
    lon, lat = first_feat["geometry"]["coordinates"]

    response = client.get(
        f"/api/v1/assembly-areas/nearby?lat={lat}&lon={lon}&radius_km=1.0"
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data["features"]) >= 1
    top_feature = data["features"][0]
    assert top_feature["properties"]["source_feature_id"] == expected_id
    assert top_feature["properties"]["distance_km"] == 0.0

    # Verify nearby properties structure
    allowed_nearby_props = {
        "source_feature_id",
        "name",
        "ref",
        "operator",
        "distance_km",
    }
    assert set(top_feature["properties"].keys()) == allowed_nearby_props


def test_get_nearby_assembly_areas_polygon_interior_distance() -> None:
    """Verify nearby query inside a polygon yields distance_km == 0.0."""
    # way/226421064 is in Sancaktepe, Istanbul
    # Interior coordinate: lon = 29.25787556, lat = 41.0341148
    interior_lon = 29.25787556
    interior_lat = 41.0341148

    response = client.get(
        f"/api/v1/assembly-areas/nearby?lat={interior_lat}&lon={interior_lon}&radius_km=2.0"
    )
    assert response.status_code == 200

    data = response.json()
    poly_matches = [
        f
        for f in data["features"]
        if f["properties"]["source_feature_id"] == "way/226421064"
    ]
    assert len(poly_matches) == 1
    poly_feature = poly_matches[0]
    assert poly_feature["properties"]["distance_km"] == 0.0
    assert poly_feature["geometry"]["type"] == "Polygon"


def test_get_nearby_assembly_areas_polygon_outside_within_radius() -> None:
    """Verify nearby query outside a polygon returns positive boundary distance."""
    # Point ~387m east of way/226421064
    out_lon = 29.263
    out_lat = 41.034

    response = client.get(
        f"/api/v1/assembly-areas/nearby?lat={out_lat}&lon={out_lon}&radius_km=1.0"
    )
    assert response.status_code == 200

    data = response.json()
    poly_matches = [
        f
        for f in data["features"]
        if f["properties"]["source_feature_id"] == "way/226421064"
    ]
    assert len(poly_matches) == 1
    poly_feature = poly_matches[0]
    # Distance should be positive and less than radius
    assert 0.0 < poly_feature["properties"]["distance_km"] < 1.0
    assert poly_feature["properties"]["distance_km"] == 0.387


def test_get_nearby_assembly_areas_polygon_outside_radius_excluded() -> None:
    """Verify polygon outside search radius is excluded from results."""
    # Point ~20+ km away from way/226421064
    out_lon = 29.0
    out_lat = 41.0

    response = client.get(
        f"/api/v1/assembly-areas/nearby?lat={out_lat}&lon={out_lon}&radius_km=5.0"
    )
    assert response.status_code == 200

    data = response.json()
    poly_matches = [
        f
        for f in data["features"]
        if f["properties"]["source_feature_id"] == "way/226421064"
    ]
    assert len(poly_matches) == 0


def test_get_nearby_assembly_areas_ordering_and_radius() -> None:
    """Verify nearby features are ordered by distance_km and source_feature_id."""
    # Kadıköy, Istanbul coordinate
    lat, lon = 40.99, 29.03
    response = client.get(
        f"/api/v1/assembly-areas/nearby?lat={lat}&lon={lon}&radius_km=10.0&limit=30"
    )
    assert response.status_code == 200

    data = response.json()
    features = data["features"]
    assert len(features) > 1

    distances = [f["properties"]["distance_km"] for f in features]
    assert distances == sorted(distances)
    for d in distances:
        assert 0.0 <= d <= 10.0


def test_get_nearby_assembly_areas_empty_radius() -> None:
    """Verify empty result set when no assembly areas are within radius."""
    # Remote ocean coordinate
    response = client.get(
        "/api/v1/assembly-areas/nearby?lat=0.0&lon=0.0&radius_km=10.0"
    )
    assert response.status_code == 200

    data = response.json()
    assert data["features"] == []
    assert data["metadata"]["returned_count"] == 0
    assert data["metadata"]["truncated"] is False


def test_get_nearby_assembly_areas_truncation() -> None:
    """Verify truncation flag when limit is smaller than count in radius."""
    lat, lon = 41.01, 28.97
    response = client.get(
        f"/api/v1/assembly-areas/nearby?lat={lat}&lon={lon}&radius_km=20.0&limit=3"
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data["features"]) == 3
    assert data["metadata"]["returned_count"] == 3
    assert data["metadata"]["truncated"] is True


def test_get_nearby_assembly_areas_validation_errors() -> None:
    """Verify 422 HTTP responses for invalid nearby parameters."""
    # Missing parameters
    assert client.get("/api/v1/assembly-areas/nearby").status_code == 422
    assert client.get("/api/v1/assembly-areas/nearby?lat=41.0").status_code == 422

    # Latitude out of bounds
    assert (
        client.get(
            "/api/v1/assembly-areas/nearby?lat=91.0&lon=29.0&radius_km=5"
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/api/v1/assembly-areas/nearby?lat=-91.0&lon=29.0&radius_km=5"
        ).status_code
        == 422
    )

    # Longitude out of bounds
    assert (
        client.get(
            "/api/v1/assembly-areas/nearby?lat=41.0&lon=181.0&radius_km=5"
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/api/v1/assembly-areas/nearby?lat=41.0&lon=-181.0&radius_km=5"
        ).status_code
        == 422
    )

    # radius_km <= 0
    assert (
        client.get(
            "/api/v1/assembly-areas/nearby?lat=41.0&lon=29.0&radius_km=0"
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/api/v1/assembly-areas/nearby?lat=41.0&lon=29.0&radius_km=-5"
        ).status_code
        == 422
    )

    # radius_km > 200
    assert (
        client.get(
            "/api/v1/assembly-areas/nearby?lat=41.0&lon=29.0&radius_km=201"
        ).status_code
        == 422
    )

    # limit < 1
    assert (
        client.get(
            "/api/v1/assembly-areas/nearby?lat=41.0&lon=29.0&radius_km=5&limit=0"
        ).status_code
        == 422
    )

    # limit > 100
    assert (
        client.get(
            "/api/v1/assembly-areas/nearby?lat=41.0&lon=29.0&radius_km=5&limit=101"
        ).status_code
        == 422
    )


# ==============================================================================
# 5. DATASET DETERMINISTIC RESOLUTION, TIE-BREAKING & 503 SERVICE UNAVAILABLE
# ==============================================================================


def test_missing_dataset_returns_503(isolated_session: Session) -> None:
    """Verify all 3 endpoints return HTTP 503 when no active dataset exists."""
    # Delete datasets within isolated transaction
    isolated_session.execute(text("DELETE FROM assembly_areas;"))
    isolated_session.execute(text("DELETE FROM assembly_area_datasets;"))
    isolated_session.flush()

    # Override get_db dependency to use our isolated rolled-back session
    app.dependency_overrides[get_db] = lambda: isolated_session
    try:
        r_dataset = client.get("/api/v1/assembly-areas/dataset")
        assert r_dataset.status_code == 503
        assert (
            r_dataset.json()["detail"]
            == "Assembly area dataset is currently unavailable."
        )

        r_collection = client.get("/api/v1/assembly-areas")
        assert r_collection.status_code == 503
        assert (
            r_collection.json()["detail"]
            == "Assembly area dataset is currently unavailable."
        )

        r_nearby = client.get(
            "/api/v1/assembly-areas/nearby?lat=41.0&lon=29.0&radius_km=5"
        )
        assert r_nearby.status_code == 503
        assert (
            r_nearby.json()["detail"]
            == "Assembly area dataset is currently unavailable."
        )
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_deterministic_dataset_tie_breaking(isolated_session: Session) -> None:
    """Verify deterministic dataset resolution with multiple dataset records.

    Order: source_data_timestamp DESC, snapshot_retrieved_at DESC, created_at, id.
    """
    now = datetime.now(UTC)
    older_ts = now - timedelta(days=5)
    newer_ts = now - timedelta(days=1)

    # Clear any existing rows within the rolled-back test transaction
    isolated_session.execute(text("DELETE FROM assembly_areas;"))
    isolated_session.execute(text("DELETE FROM assembly_area_datasets;"))
    isolated_session.flush()

    ds_older = AssemblyAreaDataset(
        source="OpenStreetMap",
        provider="OpenStreetMap contributors",
        source_classification="community_open_data",
        license="ODbL 1.0",
        attribution="© OpenStreetMap contributors",
        source_reference="https://www.openstreetmap.org/copyright",
        snapshot_retrieved_at=older_ts,
        source_data_timestamp=older_ts,
        snapshot_sha256="0000000000000000000000000000000000000000000000000000000000000001",
        snapshot_size_bytes=1000,
        source_endpoint="https://overpass-api.de/api/interpreter",
        extraction_query="test",
        source_metadata={},
    )
    ds_newer = AssemblyAreaDataset(
        source="OpenStreetMap",
        provider="OpenStreetMap contributors",
        source_classification="community_open_data",
        license="ODbL 1.0",
        attribution="© OpenStreetMap contributors",
        source_reference="https://www.openstreetmap.org/copyright",
        snapshot_retrieved_at=newer_ts,
        source_data_timestamp=newer_ts,
        snapshot_sha256="0000000000000000000000000000000000000000000000000000000000000002",
        snapshot_size_bytes=2000,
        source_endpoint="https://overpass-api.de/api/interpreter",
        extraction_query="test",
        source_metadata={},
    )
    isolated_session.add_all([ds_older, ds_newer])
    isolated_session.flush()

    area_newer = AssemblyArea(
        dataset_id=ds_newer.id,
        source_feature_id="node/9999999999",
        name="Newest Dataset Area",
        ref="TEST-01",
        operator="AFAD",
        geometry=WKTElement("POINT(29.0 41.0)", srid=4326),
        source_properties={"emergency": "assembly_point"},
    )
    isolated_session.add(area_newer)
    isolated_session.flush()

    app.dependency_overrides[get_db] = lambda: isolated_session
    try:
        r_dataset = client.get("/api/v1/assembly-areas/dataset")
        assert r_dataset.status_code == 200
        assert r_dataset.json()["snapshot_sha256"] == (
            "0000000000000000000000000000000000000000000000000000000000000002"
        )
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_deterministic_dataset_tie_breaking_snapshot_retrieved_at(
    isolated_session: Session,
) -> None:
    """Verify newer snapshot_retrieved_at wins when source_data_timestamp ties."""
    now = datetime.now(UTC)
    same_source_ts = now - timedelta(days=2)
    older_retrieved = now - timedelta(hours=5)
    newer_retrieved = now - timedelta(hours=1)

    isolated_session.execute(text("DELETE FROM assembly_areas;"))
    isolated_session.execute(text("DELETE FROM assembly_area_datasets;"))
    isolated_session.flush()

    ds_older = AssemblyAreaDataset(
        source="OpenStreetMap",
        provider="OpenStreetMap contributors",
        source_classification="community_open_data",
        license="ODbL 1.0",
        attribution="© OpenStreetMap contributors",
        source_reference="https://www.openstreetmap.org/copyright",
        snapshot_retrieved_at=older_retrieved,
        source_data_timestamp=same_source_ts,
        snapshot_sha256=(
            "0000000000000000000000000000000000000000000000000000000000000010"
        ),
        snapshot_size_bytes=1000,
        source_endpoint="https://overpass-api.de/api/interpreter",
        extraction_query="test",
        source_metadata={},
    )
    ds_newer = AssemblyAreaDataset(
        source="OpenStreetMap",
        provider="OpenStreetMap contributors",
        source_classification="community_open_data",
        license="ODbL 1.0",
        attribution="© OpenStreetMap contributors",
        source_reference="https://www.openstreetmap.org/copyright",
        snapshot_retrieved_at=newer_retrieved,
        source_data_timestamp=same_source_ts,
        snapshot_sha256=(
            "0000000000000000000000000000000000000000000000000000000000000020"
        ),
        snapshot_size_bytes=2000,
        source_endpoint="https://overpass-api.de/api/interpreter",
        extraction_query="test",
        source_metadata={},
    )
    isolated_session.add_all([ds_older, ds_newer])
    isolated_session.flush()

    app.dependency_overrides[get_db] = lambda: isolated_session
    try:
        r_dataset = client.get("/api/v1/assembly-areas/dataset")
        assert r_dataset.status_code == 200
        assert r_dataset.json()["snapshot_sha256"] == (
            "0000000000000000000000000000000000000000000000000000000000000020"
        )
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_deterministic_dataset_tie_breaking_created_at(
    isolated_session: Session,
) -> None:
    """Verify newer created_at wins when both timestamps tie."""
    now = datetime.now(UTC)
    same_ts = now - timedelta(days=2)

    isolated_session.execute(text("DELETE FROM assembly_areas;"))
    isolated_session.execute(text("DELETE FROM assembly_area_datasets;"))
    isolated_session.flush()

    ds_older = AssemblyAreaDataset(
        source="OpenStreetMap",
        provider="OpenStreetMap contributors",
        source_classification="community_open_data",
        license="ODbL 1.0",
        attribution="© OpenStreetMap contributors",
        source_reference="https://www.openstreetmap.org/copyright",
        snapshot_retrieved_at=same_ts,
        source_data_timestamp=same_ts,
        created_at=now - timedelta(minutes=30),
        snapshot_sha256=(
            "0000000000000000000000000000000000000000000000000000000000000100"
        ),
        snapshot_size_bytes=1000,
        source_endpoint="https://overpass-api.de/api/interpreter",
        extraction_query="test",
        source_metadata={},
    )
    ds_newer = AssemblyAreaDataset(
        source="OpenStreetMap",
        provider="OpenStreetMap contributors",
        source_classification="community_open_data",
        license="ODbL 1.0",
        attribution="© OpenStreetMap contributors",
        source_reference="https://www.openstreetmap.org/copyright",
        snapshot_retrieved_at=same_ts,
        source_data_timestamp=same_ts,
        created_at=now - timedelta(minutes=10),
        snapshot_sha256=(
            "0000000000000000000000000000000000000000000000000000000000000200"
        ),
        snapshot_size_bytes=2000,
        source_endpoint="https://overpass-api.de/api/interpreter",
        extraction_query="test",
        source_metadata={},
    )
    isolated_session.add_all([ds_older, ds_newer])
    isolated_session.flush()

    app.dependency_overrides[get_db] = lambda: isolated_session
    try:
        r_dataset = client.get("/api/v1/assembly-areas/dataset")
        assert r_dataset.status_code == 200
        assert r_dataset.json()["snapshot_sha256"] == (
            "0000000000000000000000000000000000000000000000000000000000000200"
        )
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_deterministic_dataset_tie_breaking_id(
    isolated_session: Session,
) -> None:
    """Verify id DESC ordering wins when all timestamps tie."""
    now = datetime.now(UTC)
    same_ts = now - timedelta(days=2)

    isolated_session.execute(text("DELETE FROM assembly_areas;"))
    isolated_session.execute(text("DELETE FROM assembly_area_datasets;"))
    isolated_session.flush()

    ds_lower_id = AssemblyAreaDataset(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        source="OpenStreetMap",
        provider="OpenStreetMap contributors",
        source_classification="community_open_data",
        license="ODbL 1.0",
        attribution="© OpenStreetMap contributors",
        source_reference="https://www.openstreetmap.org/copyright",
        snapshot_retrieved_at=same_ts,
        source_data_timestamp=same_ts,
        created_at=now,
        snapshot_sha256=(
            "0000000000000000000000000000000000000000000000000000000000001000"
        ),
        snapshot_size_bytes=1000,
        source_endpoint="https://overpass-api.de/api/interpreter",
        extraction_query="test",
        source_metadata={},
    )
    ds_higher_id = AssemblyAreaDataset(
        id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        source="OpenStreetMap",
        provider="OpenStreetMap contributors",
        source_classification="community_open_data",
        license="ODbL 1.0",
        attribution="© OpenStreetMap contributors",
        source_reference="https://www.openstreetmap.org/copyright",
        snapshot_retrieved_at=same_ts,
        source_data_timestamp=same_ts,
        created_at=now,
        snapshot_sha256=(
            "0000000000000000000000000000000000000000000000000000000000002000"
        ),
        snapshot_size_bytes=2000,
        source_endpoint="https://overpass-api.de/api/interpreter",
        extraction_query="test",
        source_metadata={},
    )
    isolated_session.add_all([ds_lower_id, ds_higher_id])
    isolated_session.flush()

    app.dependency_overrides[get_db] = lambda: isolated_session
    try:
        r_dataset = client.get("/api/v1/assembly-areas/dataset")
        assert r_dataset.status_code == 200
        # id DESC means 00000000-0000-0000-0000-000000000002 wins
        assert r_dataset.json()["snapshot_sha256"] == (
            "0000000000000000000000000000000000000000000000000000000000002000"
        )
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_dataset_isolation(isolated_session: Session) -> None:
    """Verify that features belonging to older/inactive datasets are not returned."""
    # Create an inactive dataset with older timestamp
    older_ts = datetime.now(UTC) - timedelta(days=30)
    ds_inactive = AssemblyAreaDataset(
        source="OpenStreetMap",
        provider="OpenStreetMap contributors",
        source_classification="community_open_data",
        license="ODbL 1.0",
        attribution="© OpenStreetMap contributors",
        source_reference="https://www.openstreetmap.org/copyright",
        snapshot_retrieved_at=older_ts,
        source_data_timestamp=older_ts,
        snapshot_sha256="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        snapshot_size_bytes=500,
        source_endpoint="https://overpass-api.de/api/interpreter",
        extraction_query="test",
        source_metadata={},
    )
    isolated_session.add(ds_inactive)
    isolated_session.flush()

    # Add an area to this inactive dataset
    area_inactive = AssemblyArea(
        dataset_id=ds_inactive.id,
        source_feature_id="node/1111111111",
        name="Inactive Dataset Area",
        ref="OLD-01",
        operator="None",
        geometry=WKTElement("POINT(29.0 41.0)", srid=4326),
        source_properties={"emergency": "assembly_point"},
    )
    isolated_session.add(area_inactive)
    isolated_session.flush()

    app.dependency_overrides[get_db] = lambda: isolated_session
    try:
        # Collection should NOT contain node/1111111111
        r_col = client.get("/api/v1/assembly-areas")
        assert r_col.status_code == 200
        source_ids = [
            f["properties"]["source_feature_id"] for f in r_col.json()["features"]
        ]
        assert "node/1111111111" not in source_ids

        # Nearby query should NOT contain node/1111111111
        r_near = client.get(
            "/api/v1/assembly-areas/nearby?lat=41.0&lon=29.0&radius_km=10"
        )
        assert r_near.status_code == 200
        near_ids = [
            f["properties"]["source_feature_id"] for f in r_near.json()["features"]
        ]
        assert "node/1111111111" not in near_ids
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_nearby_false_negative_east_west_regression(
    isolated_session: Session,
) -> None:
    """Verify east/west proximity is not accidentally clipped by degree prefilters.

    At 41°N, 1° lon ~84 km. A point ~9.0 km East (lon 29.107, lat 41.0) is
    within radius 10 km, but would be clipped if prefiltered with radius/111.32
    (~0.0898° lon = ~7.55 km). PostGIS exact geography verifies distance < 10 km.
    """
    # Delete existing rows within isolated rolled-back session
    isolated_session.execute(text("DELETE FROM assembly_areas;"))
    isolated_session.execute(text("DELETE FROM assembly_area_datasets;"))
    isolated_session.flush()

    now = datetime.now(UTC)
    ds = AssemblyAreaDataset(
        source="OpenStreetMap",
        provider="OpenStreetMap contributors",
        source_classification="community_open_data",
        license="ODbL 1.0",
        attribution="© OpenStreetMap contributors",
        source_reference="https://www.openstreetmap.org/copyright",
        snapshot_retrieved_at=now,
        source_data_timestamp=now,
        snapshot_sha256=(
            "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        ),
        snapshot_size_bytes=1000,
        source_endpoint="https://overpass-api.de/api/interpreter",
        extraction_query="test",
        source_metadata={},
    )
    isolated_session.add(ds)
    isolated_session.flush()

    # Point at (29.107, 41.0) ~9.002 km east of (29.0, 41.0)
    test_pt_wkt = "POINT(29.107 41.0)"
    area = AssemblyArea(
        dataset_id=ds.id,
        source_feature_id="node/8888888888",
        name="East West Test Area",
        ref="EW-01",
        operator="Test",
        geometry=WKTElement(test_pt_wkt, srid=4326),
        source_properties={"emergency": "assembly_point"},
    )
    isolated_session.add(area)
    isolated_session.flush()

    # Verify with PostGIS that geography distance is indeed < 10 km
    dist_sql = text("""
        SELECT ST_Distance(
            ST_SetSRID(ST_MakePoint(29.0, 41.0), 4326)::geography,
            ST_SetSRID(ST_MakePoint(29.107, 41.0), 4326)::geography
        ) / 1000.0 AS dist_km;
    """)
    actual_dist_km = isolated_session.execute(dist_sql).scalar()
    assert actual_dist_km is not None
    assert 8.5 < actual_dist_km < 9.5
    assert actual_dist_km < 10.0

    app.dependency_overrides[get_db] = lambda: isolated_session
    try:
        response = client.get(
            "/api/v1/assembly-areas/nearby?lat=41.0&lon=29.0&radius_km=10.0"
        )
        assert response.status_code == 200
        data = response.json()
        matching_ids = [f["properties"]["source_feature_id"] for f in data["features"]]
        # Must NOT be clipped by lossy prefilter
        assert "node/8888888888" in matching_ids
        feat = data["features"][matching_ids.index("node/8888888888")]
        assert feat["properties"]["distance_km"] == round(actual_dist_km, 3)
    finally:
        app.dependency_overrides.pop(get_db, None)
