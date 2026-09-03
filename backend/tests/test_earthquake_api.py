"""Integration test suite for public Earthquake REST API and fault proximity."""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import engine
from app.main import app
from app.models.earthquake_event import EarthquakeEvent
from app.models.fault_segment import FaultSegment
from app.repositories.earthquake_event import EarthquakeEventRepository
from app.schemas.earthquake_api import (
    ASSOCIATION_METHOD_SPATIAL_PROXIMITY,
    DEFAULT_AFAD_SOURCE,
    DEFAULT_FAULT_SOURCE,
    SCIENTIFIC_PROXIMITY_DISCLAIMER,
)

client = TestClient(app)
pytestmark = pytest.mark.integration

SAMPLE_FAULT_ID = "7e4faae8-4da3-43fc-9063-2581b719ceba"


def test_get_earthquakes_collection_success() -> None:
    """Verify GET /api/v1/earthquakes returns GeoJSON FeatureCollection."""
    response = client.get("/api/v1/earthquakes?limit=10")
    assert response.status_code == 200

    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert "metadata" in data

    meta = data["metadata"]
    assert meta["count"] <= 10
    assert meta["source"] == DEFAULT_AFAD_SOURCE
    assert meta["data_delivery"] == "local_synchronized_snapshot"
    assert "AFAD" in meta["attribution"]

    assert len(data["features"]) > 0
    first = data["features"][0]
    assert first["type"] == "Feature"
    assert "id" in first
    assert first["geometry"]["type"] == "Point"

    # RFC 7946 coordinate verification: [longitude, latitude]
    coords = first["geometry"]["coordinates"]
    assert len(coords) == 2
    lon, lat = coords[0], coords[1]
    assert -180.0 <= lon <= 180.0
    assert -90.0 <= lat <= 90.0

    props = first["properties"]
    assert props["source"] == "AFAD"
    assert "source_event_id" in props
    assert "occurred_at" in props
    assert "magnitude" in props
    assert "magnitude_type" in props
    assert "depth_km" in props

    # Internal ingestion fields must NOT be publicly exposed
    assert "source_properties" not in props
    assert "fetched_at" not in props
    assert "created_at" not in props
    assert "updated_at" not in props


def test_get_earthquakes_magnitude_filtering() -> None:
    """Verify magnitude filter validation and behavior."""
    # Min magnitude filter
    r1 = client.get("/api/v1/earthquakes?min_magnitude=6.0")
    assert r1.status_code == 200
    for f in r1.json()["features"]:
        assert f["properties"]["magnitude"] >= 6.0

    # Max magnitude filter
    r2 = client.get("/api/v1/earthquakes?max_magnitude=5.2")
    assert r2.status_code == 200
    for f in r2.json()["features"]:
        assert f["properties"]["magnitude"] <= 5.2

    # Invalid range min > max returns 422
    r_err = client.get("/api/v1/earthquakes?min_magnitude=6.0&max_magnitude=5.0")
    assert r_err.status_code == 422


def test_get_earthquakes_temporal_filtering() -> None:
    """Verify temporal filters and timezone-awareness validation."""
    # Valid timezone-aware range
    r = client.get(
        "/api/v1/earthquakes?start_time=2023-01-01T00:00:00Z&end_time=2024-01-01T00:00:00Z"
    )
    assert r.status_code == 200

    # Invalid range: start > end returns 422
    r_err = client.get(
        "/api/v1/earthquakes?start_time=2024-01-01T00:00:00Z&end_time=2023-01-01T00:00:00Z"
    )
    assert r_err.status_code == 422

    # Naive datetime (without timezone offset or Z) returns 422
    r_naive = client.get("/api/v1/earthquakes?start_time=2023-01-01T00:00:00")
    assert r_naive.status_code == 422


def test_get_earthquakes_bbox_filtering() -> None:
    """Verify spatial bounding box filtering returns inside and excludes outside."""
    # Kahramanmaraş epicentral zone
    r_inside = client.get("/api/v1/earthquakes?bbox=36.0,36.5,38.5,38.5")
    assert r_inside.status_code == 200
    inside_features = r_inside.json()["features"]
    assert len(inside_features) > 0
    for f in inside_features:
        lon, lat = f["geometry"]["coordinates"]
        assert 36.0 <= lon <= 38.5
        assert 36.5 <= lat <= 38.5

    # Remote bounding box where no quakes occurred in dataset
    r_outside = client.get("/api/v1/earthquakes?bbox=25.0,41.5,26.0,42.0")
    assert r_outside.status_code == 200
    assert r_outside.json()["metadata"]["count"] == 0


@pytest.mark.parametrize(
    "invalid_bbox",
    [
        "28.0,40.0,30.0",  # 3 elements
        "28.0,40.0,30.0,41.0,50.0",  # 5 elements
        "abc,40.0,30.0,41.0",  # non-numeric
        "30.0,40.0,28.0,41.0",  # min_lon > max_lon
        "28.0,42.0,30.0,40.0",  # min_lat > max_lat
        "200.0,40.0,210.0,41.0",  # out of longitude bounds
        "28.0,-100.0,30.0,-95.0",  # out of latitude bounds
    ],
)
def test_get_earthquakes_invalid_bbox_returns_422(invalid_bbox: str) -> None:
    """Verify invalid bbox representations are rejected with HTTP 422."""
    response = client.get(f"/api/v1/earthquakes?bbox={invalid_bbox}")
    assert response.status_code == 422


def test_get_earthquakes_limit_enforcement() -> None:
    """Verify limit parameter bounded enforcement."""
    r_limit = client.get("/api/v1/earthquakes?limit=3")
    assert r_limit.status_code == 200
    assert len(r_limit.json()["features"]) == 3
    assert r_limit.json()["metadata"]["count"] == 3

    assert client.get("/api/v1/earthquakes?limit=0").status_code == 422
    assert client.get("/api/v1/earthquakes?limit=1001").status_code == 422


def test_recent_major_route_precedence_over_id_route() -> None:
    """Ensure GET /earthquakes/recent-major is not matched by /{event_id}."""
    response = client.get("/api/v1/earthquakes/recent-major")
    assert response.status_code == 200
    assert response.json()["type"] == "FeatureCollection"


def test_get_recent_major_default_behavior() -> None:
    """Verify recent major earthquakes default recency and magnitude threshold."""
    response = client.get("/api/v1/earthquakes/recent-major")
    assert response.status_code == 200

    data = response.json()
    assert data["type"] == "FeatureCollection"
    for f in data["features"]:
        assert f["properties"]["magnitude"] >= 5.0
        # When max_distance_km is not provided, no proximity is fabricated
        assert f["properties"]["distance_to_fault_km"] is None
        assert f["properties"]["nearest_fault_id"] is None
        assert f["properties"]["association_method"] is None

    # Temporal sorting: newest first
    dates = [f["properties"]["occurred_at"] for f in data["features"]]
    assert dates == sorted(dates, reverse=True)

    # Days validation bounds
    assert client.get("/api/v1/earthquakes/recent-major?days=0").status_code == 422
    assert client.get("/api/v1/earthquakes/recent-major?days=3651").status_code == 422


def test_get_recent_major_with_proximity_filter() -> None:
    """Verify optional max_distance_km filters events and enriches nearest fault."""
    response = client.get(
        "/api/v1/earthquakes/recent-major?days=1500&max_distance_km=50.0&limit=50"
    )
    assert response.status_code == 200

    data = response.json()
    meta = data["metadata"]
    assert meta["max_distance_km"] == 50.0
    assert meta["fault_attribution"] is not None
    assert meta["fault_license"] == "CC BY-SA 4.0"
    assert meta["scientific_disclaimer"] == SCIENTIFIC_PROXIMITY_DISCLAIMER

    for f in data["features"]:
        props = f["properties"]
        assert props["distance_to_fault_km"] is not None
        assert props["distance_to_fault_km"] <= 50.0
        assert props["nearest_fault_id"] is not None
        assert props["nearest_fault_source_feature_id"] is not None
        assert props["association_method"] == ASSOCIATION_METHOD_SPATIAL_PROXIMITY
        assert props["proximity_disclaimer"] == SCIENTIFIC_PROXIMITY_DISCLAIMER

    # Proximity parameter bounds validation
    assert (
        client.get("/api/v1/earthquakes/recent-major?max_distance_km=0").status_code
        == 422
    )
    assert (
        client.get("/api/v1/earthquakes/recent-major?max_distance_km=-5").status_code
        == 422
    )
    assert (
        client.get("/api/v1/earthquakes/recent-major?max_distance_km=501").status_code
        == 422
    )


def test_get_single_earthquake_detail() -> None:
    """Verify GET /api/v1/earthquakes/{event_id} success and error behaviors."""
    # Find a valid event UUID
    list_res = client.get("/api/v1/earthquakes?limit=1")
    event_id = list_res.json()["features"][0]["id"]

    # Success
    r_ok = client.get(f"/api/v1/earthquakes/{event_id}")
    assert r_ok.status_code == 200
    data = r_ok.json()
    assert data["type"] == "Feature"
    assert data["id"] == event_id
    assert data["geometry"]["type"] == "Point"
    assert data["metadata"]["source"] == DEFAULT_AFAD_SOURCE

    # Unknown UUID
    random_uuid = str(uuid.uuid4())
    r_404 = client.get(f"/api/v1/earthquakes/{random_uuid}")
    assert r_404.status_code == 404

    # Malformed UUID
    r_422 = client.get("/api/v1/earthquakes/not-a-valid-uuid")
    assert r_422.status_code == 422


def test_get_fault_earthquakes_proximity_success() -> None:
    """Verify GET /api/v1/fault-lines/{fault_id}/earthquakes endpoint."""
    response = client.get(
        f"/api/v1/fault-lines/{SAMPLE_FAULT_ID}/earthquakes?max_distance_km=50"
    )
    assert response.status_code == 200

    data = response.json()
    assert data["type"] == "FeatureCollection"
    meta = data["metadata"]
    assert meta["fault_id"] == SAMPLE_FAULT_ID
    assert meta["fault_source"] == DEFAULT_FAULT_SOURCE
    assert meta["max_distance_km"] == 50.0
    assert meta["scientific_disclaimer"] == SCIENTIFIC_PROXIMITY_DISCLAIMER
    assert meta["attribution"] is not None
    assert meta["fault_attribution"] is not None

    features = data["features"]
    assert len(features) > 0
    for f in features:
        props = f["properties"]
        assert props["distance_to_fault_km"] is not None
        assert props["distance_to_fault_km"] <= 50.0
        assert props["nearest_fault_id"] == SAMPLE_FAULT_ID
        assert props["association_method"] == ASSOCIATION_METHOD_SPATIAL_PROXIMITY
        assert props["proximity_disclaimer"] == SCIENTIFIC_PROXIMITY_DISCLAIMER


def test_get_fault_earthquakes_sorting() -> None:
    """Verify order_by parameter on fault-specific earthquakes endpoint."""
    # Distance ordering
    r_dist = client.get(
        f"/api/v1/fault-lines/{SAMPLE_FAULT_ID}/earthquakes?max_distance_km=50&order_by=distance"
    )
    assert r_dist.status_code == 200
    distances = [
        f["properties"]["distance_to_fault_km"] for f in r_dist.json()["features"]
    ]
    assert distances == sorted(distances)

    # Invalid order_by
    r_bad = client.get(
        f"/api/v1/fault-lines/{SAMPLE_FAULT_ID}/earthquakes?max_distance_km=50&order_by=invalid"
    )
    assert r_bad.status_code == 422


def test_get_fault_earthquakes_validations() -> None:
    """Verify parameter requirements and error handling on fault earthquakes route."""
    # Missing required max_distance_km
    r_missing = client.get(f"/api/v1/fault-lines/{SAMPLE_FAULT_ID}/earthquakes")
    assert r_missing.status_code == 422

    # Negative / zero radius
    assert (
        client.get(
            f"/api/v1/fault-lines/{SAMPLE_FAULT_ID}/earthquakes?max_distance_km=0"
        ).status_code
        == 422
    )
    assert (
        client.get(
            f"/api/v1/fault-lines/{SAMPLE_FAULT_ID}/earthquakes?max_distance_km=-10"
        ).status_code
        == 422
    )
    assert (
        client.get(
            f"/api/v1/fault-lines/{SAMPLE_FAULT_ID}/earthquakes?max_distance_km=501"
        ).status_code
        == 422
    )

    # Unknown fault UUID
    random_fault = str(uuid.uuid4())
    assert (
        client.get(
            f"/api/v1/fault-lines/{random_fault}/earthquakes?max_distance_km=50"
        ).status_code
        == 404
    )

    # Malformed fault UUID
    assert (
        client.get(
            "/api/v1/fault-lines/invalid-uuid/earthquakes?max_distance_km=50"
        ).status_code
        == 422
    )


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


def test_scientific_terminology_integrity() -> None:
    """Verify strict non-causal terminology in all responses."""
    r = client.get(
        "/api/v1/earthquakes/recent-major?days=1500&max_distance_km=50&limit=5"
    )
    assert r.status_code == 200
    text_content = r.text

    forbidden_terms = [
        "occurred on this fault",
        "caused the earthquake",
        "responsible fault",
        "belongs to this fault",
    ]
    for term in forbidden_terms:
        assert term not in text_content.lower()


def test_edge_radius_deterministic_inclusion_and_exclusion(
    isolated_session: Session,
) -> None:
    """Verify exact ST_DWithin geography governs inclusion at boundary."""
    # Create synthetic test fault at (0.0, 0.0) isolated from regional DB faults
    fault_id = uuid.uuid4()
    test_fault = FaultSegment(
        id=fault_id,
        source="TEST",
        source_feature_id="TEST_EDGE_FAULT",
        name="Test Edge Fault",
        geometry="SRID=4326;MULTILINESTRING((0.0 -1.0, 0.0 1.0))",
    )
    isolated_session.add(test_fault)

    # Generate exact geodesic distance points from (0.0, 0.0) Eastward
    pts_sql = text("""
        SELECT
            ST_AsText(ST_GeogFromText('POINT(0.1 0.0)')::geometry) as inside_20km,
            ST_AsText(ST_Project(
                ST_GeogFromText('POINT(0.0 0.0)'), 49500.0, radians(90.0)
            )::geometry) as boundary_inside,
            ST_AsText(ST_Project(
                ST_GeogFromText('POINT(0.0 0.0)'), 50500.0, radians(90.0)
            )::geometry) as boundary_outside,
            ST_AsText(ST_GeogFromText('POINT(1.0 0.0)')::geometry) as clearly_outside;
    """)
    pts = isolated_session.execute(pts_sql).mappings().first()
    assert pts is not None

    now = datetime.now(UTC)
    events = [
        EarthquakeEvent(
            id=uuid.uuid4(),
            source="TEST",
            source_event_id="TEST_EV_INSIDE_20KM",
            occurred_at=now - timedelta(days=1),
            depth_km=10.0,
            magnitude=5.5,
            magnitude_type="MW",
            geometry=f"SRID=4326;{pts['inside_20km']}",
        ),
        EarthquakeEvent(
            id=uuid.uuid4(),
            source="TEST",
            source_event_id="TEST_EV_BOUNDARY_INSIDE",
            occurred_at=now - timedelta(days=2),
            depth_km=10.0,
            magnitude=5.5,
            magnitude_type="MW",
            geometry=f"SRID=4326;{pts['boundary_inside']}",
        ),
        EarthquakeEvent(
            id=uuid.uuid4(),
            source="TEST",
            source_event_id="TEST_EV_BOUNDARY_OUTSIDE",
            occurred_at=now - timedelta(days=3),
            depth_km=10.0,
            magnitude=5.5,
            magnitude_type="MW",
            geometry=f"SRID=4326;{pts['boundary_outside']}",
        ),
        EarthquakeEvent(
            id=uuid.uuid4(),
            source="TEST",
            source_event_id="TEST_EV_CLEARLY_OUTSIDE",
            occurred_at=now - timedelta(days=4),
            depth_km=10.0,
            magnitude=5.5,
            magnitude_type="MW",
            geometry=f"SRID=4326;{pts['clearly_outside']}",
        ),
    ]
    isolated_session.add_all(events)
    isolated_session.flush()

    # Query using repository with max_distance_km = 50.0
    repo = EarthquakeEventRepository(isolated_session)
    fault_matched = repo.list_near_fault(
        fault_id=fault_id,
        max_distance_km=50.0,
        min_magnitude=5.0,
    )
    matched_source_ids = {r["source_event_id"] for r in fault_matched}

    # Verify exact inclusion: inside (20km) and boundary inside (49.5km) MUST be present
    assert "TEST_EV_INSIDE_20KM" in matched_source_ids
    assert "TEST_EV_BOUNDARY_INSIDE" in matched_source_ids

    # Verify exact exclusion: boundary outside (50.5km) & clearly outside absent
    assert "TEST_EV_BOUNDARY_OUTSIDE" not in matched_source_ids
    assert "TEST_EV_CLEARLY_OUTSIDE" not in matched_source_ids

    # Verify exact distance accuracy
    for r in fault_matched:
        assert r["distance_to_fault_km"] <= 50.0
        if r["source_event_id"] == "TEST_EV_BOUNDARY_INSIDE":
            # 49.5 km rounded to 3 decimals = 49.5
            assert round(r["distance_to_fault_km"], 1) == 49.5

    # Also verify recent_major with proximity on isolated data
    recent_matched = repo.list_recent_major(
        since=now - timedelta(days=30),
        min_magnitude=5.0,
        max_distance_km=50.0,
    )
    recent_source_ids = {r["source_event_id"] for r in recent_matched}
    assert "TEST_EV_INSIDE_20KM" in recent_source_ids
    assert "TEST_EV_BOUNDARY_INSIDE" in recent_source_ids
    assert "TEST_EV_BOUNDARY_OUTSIDE" not in recent_source_ids
    assert "TEST_EV_CLEARLY_OUTSIDE" not in recent_source_ids


def test_upper_boundary_500km_safety_case() -> None:
    """Verify maximum supported API proximity radius (500 km) executes safely."""
    # 1. Fault earthquakes at 500 km
    r_fault = client.get(
        f"/api/v1/fault-lines/{SAMPLE_FAULT_ID}/earthquakes?max_distance_km=500.0&limit=50"
    )
    assert r_fault.status_code == 200
    data_fault = r_fault.json()
    assert data_fault["type"] == "FeatureCollection"
    assert data_fault["metadata"]["max_distance_km"] == 500.0
    assert (
        data_fault["metadata"]["scientific_disclaimer"]
        == SCIENTIFIC_PROXIMITY_DISCLAIMER
    )
    for f in data_fault["features"]:
        assert f["properties"]["distance_to_fault_km"] <= 500.0

    # 2. Recent major earthquakes with 500 km proximity
    r_major = client.get(
        "/api/v1/earthquakes/recent-major?max_distance_km=500.0&limit=50"
    )
    assert r_major.status_code == 200
    data_major = r_major.json()
    assert data_major["type"] == "FeatureCollection"
    assert data_major["metadata"]["max_distance_km"] == 500.0
    for f in data_major["features"]:
        assert f["properties"]["distance_to_fault_km"] <= 500.0

    # 3. Parameter validation beyond 500 km
    assert (
        client.get(
            f"/api/v1/fault-lines/{SAMPLE_FAULT_ID}/earthquakes?max_distance_km=500.1"
        ).status_code
        == 422
    )
    assert (
        client.get("/api/v1/earthquakes/recent-major?max_distance_km=500.1").status_code
        == 422
    )


def test_api_read_operations_leave_database_clean() -> None:
    """Verify that read operations and tests do not pollute or modify DB rows."""
    with engine.connect() as conn:
        f_count = conn.execute(text("SELECT count(*) FROM fault_segments")).scalar()
        q_count = conn.execute(text("SELECT count(*) FROM earthquake_events")).scalar()

    assert f_count == 722
    assert q_count == 84
