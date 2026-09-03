import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import engine
from app.main import app

client = TestClient(app)
pytestmark = pytest.mark.integration


def test_get_fault_lines_collection_success() -> None:
    """Verify GET /api/v1/fault-lines returns GeoJSON FeatureCollection."""
    response = client.get("/api/v1/fault-lines?limit=10")
    assert response.status_code == 200

    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert "metadata" in data

    # Verify attribution metadata
    meta = data["metadata"]
    assert meta["count"] <= 10
    assert "GEM" in meta["source"]
    assert meta["license"] == "CC BY-SA 4.0"
    assert "Global Earthquake Model" in meta["attribution"]
    assert "Not official" in meta["disclaimer"]

    # Verify feature structure
    assert len(data["features"]) > 0
    first = data["features"][0]
    assert first["type"] == "Feature"
    assert "id" in first
    assert first["geometry"]["type"] == "MultiLineString"

    # RFC 7946 coordinate verification: [longitude, latitude]
    coords = first["geometry"]["coordinates"]
    assert len(coords) >= 1
    assert len(coords[0]) >= 2
    lon, lat = coords[0][0][0], coords[0][0][1]
    assert -180.0 <= lon <= 180.0
    assert -90.0 <= lat <= 90.0

    # Verify properties
    props = first["properties"]
    assert "id" in props
    assert props["source"] == "GEM_GAF"
    assert "source_feature_id" in props
    # Raw JSONB must NOT be exposed in public API
    assert "source_properties" not in props


def test_get_fault_lines_with_bbox_filter() -> None:
    """Verify bounding box spatial query filters features accurately."""
    # Sea of Marmara / Istanbul viewport
    response = client.get("/api/v1/fault-lines?bbox=28.0,40.0,30.0,41.5")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert data["metadata"]["count"] > 0
    assert data["metadata"]["count"] < 722  # Bounded subset of total 722 features


@pytest.mark.parametrize(
    "invalid_bbox",
    [
        "28.0,40.0,30.0",  # Only 3 components
        "28.0,40.0,30.0,41.0,50.0",  # 5 components
        "abc,40.0,30.0,41.0",  # Non-numeric
        "30.0,40.0,28.0,41.0",  # min_lon > max_lon
        "28.0,42.0,30.0,40.0",  # min_lat > max_lat
        "200.0,40.0,210.0,41.0",  # Longitude > 180
        "28.0,-100.0,30.0,-95.0",  # Latitude < -90
    ],
)
def test_get_fault_lines_invalid_bbox_returns_422(invalid_bbox: str) -> None:
    """Verify invalid bbox strings return HTTP 422 with descriptive validation error."""
    response = client.get(f"/api/v1/fault-lines?bbox={invalid_bbox}")
    assert response.status_code == 422
    assert "detail" in response.json()


def test_get_fault_lines_with_fault_type_filter() -> None:
    """Verify filtering by normalized fault kinematic slip type."""
    response = client.get("/api/v1/fault-lines?fault_type=Dextral&limit=50")
    assert response.status_code == 200
    data = response.json()
    for feat in data["features"]:
        assert feat["properties"]["fault_type"] == "Dextral"


def test_get_fault_lines_limit_enforcement() -> None:
    """Verify result limits are enforced strictly."""
    response = client.get("/api/v1/fault-lines?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["features"]) == 5
    assert data["metadata"]["count"] == 5

    # Out of bounds limits return 422
    assert client.get("/api/v1/fault-lines?limit=0").status_code == 422
    assert client.get("/api/v1/fault-lines?limit=2001").status_code == 422


def test_get_single_fault_line_by_id_success() -> None:
    """Verify GET /api/v1/fault-lines/{id} returns a single Feature."""
    list_res = client.get("/api/v1/fault-lines?limit=1")
    assert list_res.status_code == 200
    target_id = list_res.json()["features"][0]["id"]

    res = client.get(f"/api/v1/fault-lines/{target_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "Feature"
    assert data["id"] == target_id
    assert data["geometry"]["type"] == "MultiLineString"
    assert data["metadata"] is not None
    assert "GEM" in data["metadata"]["source"]


def test_get_single_fault_line_not_found() -> None:
    """Verify non-existent UUID returns HTTP 404."""
    unknown_uuid = str(uuid.uuid4())
    res = client.get(f"/api/v1/fault-lines/{unknown_uuid}")
    assert res.status_code == 404
    assert res.json()["detail"] == f"Fault line with id '{unknown_uuid}' not found"


def test_get_single_fault_line_invalid_uuid() -> None:
    """Verify malformed UUID string returns HTTP 422."""
    res = client.get("/api/v1/fault-lines/invalid-uuid-string")
    assert res.status_code == 422


def test_get_nearby_fault_lines_success() -> None:
    """Verify GET /api/v1/fault-lines/nearby returns proximity-sorted faults."""
    # Query location: Central Istanbul / Bosporus (41.0082°N, 28.9784°E)
    res = client.get(
        "/api/v1/fault-lines/nearby?latitude=41.0082&longitude=28.9784&radius_km=60.0&limit=5"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0

    distances = []
    for feat in data["features"]:
        dist = feat["properties"]["distance_km"]
        assert dist is not None
        assert 0.0 <= dist <= 60.0
        distances.append(dist)

    # Verify ascending proximity ordering
    assert distances == sorted(distances)


def test_nearby_route_precedence_over_id_route() -> None:
    """Regression test ensuring /nearby is matched by nearby router."""
    # When query params are missing on /nearby, it must return 422 for params, not UUID
    res = client.get("/api/v1/fault-lines/nearby")
    assert res.status_code == 422
    # Detail must indicate missing required query parameters
    error_fields = [e["loc"][-1] for e in res.json().get("detail", [])]
    assert "latitude" in error_fields
    assert "longitude" in error_fields
    assert "radius_km" in error_fields


@pytest.mark.parametrize(
    "query_str,expected_err_field",
    [
        ("latitude=41.0&longitude=29.0", "radius_km"),  # Missing radius
        ("latitude=41.0&longitude=29.0&radius_km=0", "radius_km"),  # radius <= 0
        ("latitude=41.0&longitude=29.0&radius_km=-10", "radius_km"),  # radius < 0
        ("latitude=41.0&longitude=29.0&radius_km=501", "radius_km"),  # radius > 500
        ("latitude=95.0&longitude=29.0&radius_km=50", "latitude"),  # lat > 90
        ("latitude=-95.0&longitude=29.0&radius_km=50", "latitude"),  # lat < -90
        ("latitude=41.0&longitude=185.0&radius_km=50", "longitude"),  # lon > 180
        ("latitude=41.0&longitude=-185.0&radius_km=50", "longitude"),  # lon < -180
    ],
)
def test_nearby_parameter_validation_422(
    query_str: str, expected_err_field: str
) -> None:
    """Verify nearby parameter constraints enforce strict safety validation."""
    res = client.get(f"/api/v1/fault-lines/nearby?{query_str}")
    assert res.status_code == 422
    error_fields = [e["loc"][-1] for e in res.json().get("detail", [])]
    assert expected_err_field in error_fields


def test_api_read_operations_leave_database_clean() -> None:
    """Verify that read-only API invocations do not modify persistent database rows."""
    with engine.connect() as conn:
        before = conn.execute(text("SELECT count(*) FROM fault_segments")).scalar()

    # Invoke all endpoints
    client.get("/api/v1/fault-lines?limit=10")
    client.get("/api/v1/fault-lines?bbox=28.0,40.0,30.0,42.0")
    client.get("/api/v1/fault-lines/nearby?latitude=41.0&longitude=29.0&radius_km=50")

    with engine.connect() as conn:
        after = conn.execute(text("SELECT count(*) FROM fault_segments")).scalar()

    assert before == after
    assert before == 722
