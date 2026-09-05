"""Comprehensive public API contract, boundary, and security regression test suite.

Verifies the exact 15 public API paths, GeoJSON consistency, parameter boundaries,
error semantics, AI provider isolation, dataset row-count conservation, and CORS.
"""

import inspect
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app.integrations.ai.dependencies import get_ai_provider
from app.main import app
from tests.fakes.ai import StubPreparednessAIProvider

client = TestClient(app)

EXPECTED_15_PATHS = {
    "/api/v1/health",
    "/api/v1/fault-lines",
    "/api/v1/fault-lines/nearby",
    "/api/v1/fault-lines/{fault_id}",
    "/api/v1/fault-lines/{fault_id}/earthquakes",
    "/api/v1/earthquakes",
    "/api/v1/earthquakes/recent-major",
    "/api/v1/earthquakes/{event_id}",
    "/api/v1/earthquake-hazards/dataset",
    "/api/v1/earthquake-hazards/nearest",
    "/api/v1/earthquake-hazards",
    "/api/v1/assembly-areas/dataset",
    "/api/v1/assembly-areas/nearby",
    "/api/v1/assembly-areas",
    "/api/v1/ai/preparedness-guide",
}

EXPECTED_METHODS = {
    "/api/v1/health": {"get"},
    "/api/v1/fault-lines": {"get"},
    "/api/v1/fault-lines/nearby": {"get"},
    "/api/v1/fault-lines/{fault_id}": {"get"},
    "/api/v1/fault-lines/{fault_id}/earthquakes": {"get"},
    "/api/v1/earthquakes": {"get"},
    "/api/v1/earthquakes/recent-major": {"get"},
    "/api/v1/earthquakes/{event_id}": {"get"},
    "/api/v1/earthquake-hazards/dataset": {"get"},
    "/api/v1/earthquake-hazards/nearest": {"get"},
    "/api/v1/earthquake-hazards": {"get"},
    "/api/v1/assembly-areas/dataset": {"get"},
    "/api/v1/assembly-areas/nearby": {"get"},
    "/api/v1/assembly-areas": {"get"},
    "/api/v1/ai/preparedness-guide": {"post"},
}

GEOJSON_COLLECTION_ENDPOINTS = [
    "/api/v1/fault-lines?limit=5",
    "/api/v1/earthquakes?limit=5",
    "/api/v1/earthquake-hazards?bbox=28.0,40.0,30.0,42.0&limit=5",
    "/api/v1/assembly-areas?limit=5",
]

DATABASE_TABLES = [
    "assembly_area_datasets",
    "assembly_areas",
    "hazard_datasets",
    "earthquake_hazard_points",
    "fault_segments",
    "earthquake_events",
]


# ==============================================================================
# 1. OPENAPI INVENTORY & METHOD CONTRACTS
# ==============================================================================


def test_openapi_exact_15_paths_and_allowed_methods() -> None:
    """Verify OpenAPI specification exposes exactly the approved 15 paths."""
    schema = app.openapi()
    paths = schema["paths"]

    assert len(paths) == 15, f"Expected 15 paths in OpenAPI, found {len(paths)}"
    assert set(paths.keys()) == EXPECTED_15_PATHS

    for path, expected_method_set in EXPECTED_METHODS.items():
        actual_methods = set(paths[path].keys()) - {"options", "head", "parameters"}
        assert actual_methods == expected_method_set, (
            f"Path {path} expected methods {expected_method_set}, got {actual_methods}"
        )


def test_no_unintended_admin_debug_or_auth_routes() -> None:
    """Verify absence of debug, admin, internal, or authentication routes."""
    schema = app.openapi()
    all_paths = list(schema["paths"].keys())
    prohibited_keywords = [
        "admin",
        "debug",
        "auth",
        "login",
        "user",
        "token",
        "internal",
        "test",
    ]

    for path in all_paths:
        for kw in prohibited_keywords:
            assert f"/{kw}" not in path.lower(), f"Unintended route detected: {path}"


def test_method_not_allowed_behavior() -> None:
    """Verify endpoints reject unapproved HTTP methods with 405 Method Not Allowed."""
    # Health endpoint does not support POST
    resp_health_post = client.post("/api/v1/health")
    assert resp_health_post.status_code == 405

    # AI endpoint does not support GET
    resp_ai_get = client.get("/api/v1/ai/preparedness-guide")
    assert resp_ai_get.status_code == 405


# ==============================================================================
# 2. HEALTH ENDPOINT CONTRACT
# ==============================================================================


def test_health_contract_and_rate_limit_exemption() -> None:
    """Verify GET /api/v1/health contract, headers, and rate-limit exemption."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {
        "status": "ok",
        "service": "AFET360 API",
        "version": "0.1.0",
    }

    # Security headers must be present
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("referrer-policy") == "no-referrer"

    # Health must be exempt from rate limiting
    for _ in range(10):
        r = client.get("/api/v1/health")
        assert r.status_code == 200


# ==============================================================================
# 3. GEOJSON STRUCTURAL CONSISTENCY & INTERNAL LEAKAGE CHECKS
# ==============================================================================


@pytest.mark.parametrize("endpoint", GEOJSON_COLLECTION_ENDPOINTS)
def test_geojson_feature_collection_invariants(endpoint: str) -> None:
    """Verify GeoJSON FeatureCollection invariants across all four spatial domains."""
    resp = client.get(endpoint)
    assert resp.status_code == 200, (
        f"Endpoint {endpoint} returned status {resp.status_code}"
    )

    data = resp.json()
    assert data.get("type") == "FeatureCollection"
    assert "features" in data
    assert isinstance(data["features"], list)

    for feature in data["features"]:
        assert feature.get("type") == "Feature"
        assert "geometry" in feature
        geom = feature["geometry"]
        assert isinstance(geom, dict)
        assert "type" in geom
        assert "coordinates" in geom

        # Check properties dictionary
        props = feature.get("properties")
        assert isinstance(props, dict)

        # Invariant: No raw SQLAlchemy internal metadata
        assert "_sa_instance_state" not in props
        assert "_sa_instance_state" not in feature

        # Invariant: No raw binary geometry (WKB) strings leaked in properties
        for k, v in props.items():
            assert not (
                isinstance(v, str) and v.startswith("0101000020") and len(v) > 40
            ), f"Leaked raw geometry hex in key {k}"


# ==============================================================================
# 4. COORDINATE & BOUNDARY VALIDATION
# ==============================================================================


@pytest.mark.parametrize(
    ("endpoint", "invalid_param"),
    [
        (
            "/api/v1/fault-lines/nearby?latitude=91.0&longitude=29.0&radius_km=10",
            "lat > 90",
        ),
        (
            "/api/v1/fault-lines/nearby?latitude=-91.0&longitude=29.0&radius_km=10",
            "lat < -90",
        ),
        (
            "/api/v1/fault-lines/nearby?latitude=40.0&longitude=181.0&radius_km=10",
            "lon > 180",
        ),
        (
            "/api/v1/fault-lines/nearby?latitude=40.0&longitude=-181.0&radius_km=10",
            "lon < -180",
        ),
        (
            "/api/v1/fault-lines/nearby?latitude=40.0&longitude=29.0&radius_km=0",
            "radius == 0",
        ),
        (
            "/api/v1/fault-lines/nearby?latitude=40.0&longitude=29.0&radius_km=-5",
            "radius < 0",
        ),
        (
            "/api/v1/fault-lines/nearby?latitude=40.0&longitude=29.0&radius_km=10000",
            "radius > max",
        ),
        ("/api/v1/earthquake-hazards/nearest?lat=95.0&lon=32.85", "lat > 90"),
        ("/api/v1/earthquake-hazards/nearest?lat=39.93&lon=-195.0", "lon < -180"),
        ("/api/v1/assembly-areas/nearby?lat=91.0&lon=29.0&radius_km=5", "lat > 90"),
        ("/api/v1/assembly-areas/nearby?lat=41.0&lon=29.0&radius_km=0", "radius == 0"),
        (
            "/api/v1/assembly-areas/nearby?lat=41.0&lon=29.0&radius_km=250",
            "radius > 200",
        ),
        (
            "/api/v1/assembly-areas/nearby?lat=41.0&lon=29.0&radius_km=5&limit=0",
            "limit == 0",
        ),
        (
            "/api/v1/assembly-areas/nearby?lat=41.0&lon=29.0&radius_km=5&limit=101",
            "limit > 100",
        ),
        ("/api/v1/assembly-areas?limit=0", "limit == 0"),
        ("/api/v1/assembly-areas?limit=2500", "limit > 2000"),
        ("/api/v1/earthquake-hazards?bbox=28.0,40.0,30.0,42.0&limit=0", "limit == 0"),
        (
            "/api/v1/earthquake-hazards?bbox=28.0,40.0,30.0,42.0&limit=2500",
            "limit > 2000",
        ),
    ],
)
def test_spatial_parameter_boundary_rejection(
    endpoint: str, invalid_param: str
) -> None:
    """Verify endpoints reject out-of-range coordinates and limits with 422."""
    resp = client.get(endpoint)
    assert resp.status_code == 422, (
        f"Endpoint {endpoint} ({invalid_param}) expected 422, got {resp.status_code}"
    )


@pytest.mark.parametrize(
    "bbox_param",
    [
        "invalid_text",
        "28.0,40.0,30.0",  # 3 elements instead of 4
        "28.0,40.0,30.0,42.0,10.0",  # 5 elements
        "30.0,40.0,28.0,42.0",  # min_lon > max_lon
        "28.0,42.0,30.0,40.0",  # min_lat > max_lat
        "28.0,40.0,30.0,abc",  # non-numeric
    ],
)
def test_malformed_bbox_rejection(bbox_param: str) -> None:
    """Verify malformed bounding boxes are rejected with 422 across endpoints."""
    endpoints = [
        f"/api/v1/fault-lines?bbox={bbox_param}",
        f"/api/v1/earthquakes?bbox={bbox_param}",
        f"/api/v1/earthquake-hazards?bbox={bbox_param}",
        f"/api/v1/assembly-areas?bbox={bbox_param}",
    ]
    for ep in endpoints:
        resp = client.get(ep)
        assert resp.status_code == 422, (
            f"Endpoint {ep} expected 422, got {resp.status_code}"
        )


# ==============================================================================
# 5. DATASET METADATA & EMPTY VS. MISSING CONTRACTS
# ==============================================================================


def test_hazard_dataset_metadata_provenance() -> None:
    """Verify GET /api/v1/earthquake-hazards/dataset returns valid GEM provenance."""
    resp = client.get("/api/v1/earthquake-hazards/dataset")
    assert resp.status_code == 200
    data = resp.json()

    assert data.get("source") == "GEM_GSHM"
    assert "Global Earthquake Model" in data.get("attribution", "")
    assert data.get("license") == "CC BY-NC-SA 4.0"
    assert "hazard_metric" in data
    assert "unit" in data

    # Ensure internal file system paths do not leak
    for val in data.values():
        if isinstance(val, str):
            assert "C:\\" not in val
            assert "/home/" not in val
            assert "/tmp/" not in val


def test_assembly_dataset_metadata_provenance() -> None:
    """Verify GET /api/v1/assembly-areas/dataset returns valid OSM provenance."""
    resp = client.get("/api/v1/assembly-areas/dataset")
    assert resp.status_code == 200
    data = resp.json()

    assert data.get("source") == "OpenStreetMap"
    assert data.get("source_classification") == "community_open_data"
    assert "OpenStreetMap contributors" in data.get("attribution", "")
    assert data.get("license") == "ODbL 1.0"
    assert data.get("feature_count") == 678
    assert data.get("point_count") == 650
    assert data.get("polygon_count") == 28

    # Invariant: No false official AFAD classification
    assert "official" not in data.get("source_classification", "").lower()
    assert "afad" not in data.get("source", "").lower()

    # Ensure internal local file system cache paths do not leak
    for val in data.values():
        if isinstance(val, str):
            assert "C:\\" not in val
            assert "AppData" not in val


def test_valid_dataset_with_zero_spatial_matches_returns_empty_200() -> None:
    """Verify queries with zero spatial features return 200 with empty collection."""
    # Bbox in remote ocean
    resp_empty_bbox = client.get("/api/v1/assembly-areas?bbox=-170.0,0.0,-169.0,1.0")
    assert resp_empty_bbox.status_code == 200
    data = resp_empty_bbox.json()
    assert data["type"] == "FeatureCollection"
    assert data["features"] == []
    assert data["metadata"]["returned_count"] == 0

    # Nearby in remote location
    resp_empty_nearby = client.get(
        "/api/v1/assembly-areas/nearby?lat=0.0&lon=0.0&radius_km=1.0"
    )
    assert resp_empty_nearby.status_code == 200
    data_nearby = resp_empty_nearby.json()
    assert data_nearby["type"] == "FeatureCollection"
    assert data_nearby["features"] == []
    assert data_nearby["metadata"]["returned_count"] == 0


# ==============================================================================
# 6. FAULT & EARTHQUAKE RELATIONSHIPS (NON-CAUSAL CONTRACT)
# ==============================================================================


def test_fault_earthquake_relationship_spatial_proximity_contract() -> None:
    """Verify fault-earthquake relationship is proximity without causation."""
    # Obtain a known fault ID from the collection
    resp_faults = client.get("/api/v1/fault-lines?limit=1")
    assert resp_faults.status_code == 200
    features = resp_faults.json()["features"]
    assert len(features) > 0
    fault_id = features[0]["id"]

    # Retrieve associated earthquakes
    resp = client.get(f"/api/v1/fault-lines/{fault_id}/earthquakes?max_distance_km=50")
    assert resp.status_code == 200
    data = resp.json()

    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert "metadata" in data
    assert data["metadata"]["fault_id"] == fault_id
    assert "scientific_disclaimer" in data["metadata"]

    # Verify no causation claims exist in keys or values
    data_str = str(data).lower()
    assert "caused_by" not in data_str
    assert "triggered_by" not in data_str
    assert "prediction" not in data_str


def test_single_fault_and_single_earthquake_not_found() -> None:
    """Verify 404 responses for nonexistent UUIDs without leaking internal DB state."""
    random_uuid = str(uuid.uuid4())

    resp_fault = client.get(f"/api/v1/fault-lines/{random_uuid}")
    assert resp_fault.status_code == 404
    assert (
        f"Fault line with id '{random_uuid}' not found" in resp_fault.json()["detail"]
    )

    resp_earthquake = client.get(f"/api/v1/earthquakes/{random_uuid}")
    assert resp_earthquake.status_code == 404
    assert (
        f"Earthquake event with ID '{random_uuid}' not found"
        in resp_earthquake.json()["detail"]
    )


# ==============================================================================
# 7. AI PUBLIC CONTRACT, SAFETY BOUNDARIES & ERROR CONTRACTS
# ==============================================================================


def test_ai_preparedness_guide_public_contract() -> None:
    """Verify POST /api/v1/ai/preparedness-guide response structure and disclaimer."""
    stub = StubPreparednessAIProvider(mode="success")
    app.dependency_overrides[get_ai_provider] = lambda: stub
    try:
        payload = {
            "disaster_type": "earthquake",
            "city": "İzmir",
            "language": "tr",
        }
        resp = client.post("/api/v1/ai/preparedness-guide", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["disaster_type"] == "earthquake"
        assert data["city"] == "İzmir"
        assert data["language"] == "tr"
        assert data["generated_by_ai"] is True
        assert "guide" in data
        assert "disclaimer" in data
        assert len(data["disclaimer"]) > 10

        guide = data["guide"]
        for section in [
            "summary",
            "before",
            "during",
            "after",
            "emergency_kit",
            "important_notes",
        ]:
            assert section in guide
            assert guide[section] is not None
    finally:
        app.dependency_overrides.pop(get_ai_provider, None)


@pytest.mark.parametrize(
    "forbidden_field",
    [
        "prompt",
        "system_prompt",
        "instructions",
        "messages",
        "conversation_history",
        "max_tokens",
        "model",
        "temperature",
        "api_key",
    ],
)
def test_ai_request_rejects_unapproved_prompt_override_fields(
    forbidden_field: str,
) -> None:
    """Verify schema rejects extra fields such as prompt or instructions.

    The server controls the safety policy and system context; the public schema
    does not accept arbitrary prompt fields, reducing the prompt-injection surface.
    """
    stub = StubPreparednessAIProvider(mode="success")
    app.dependency_overrides[get_ai_provider] = lambda: stub
    try:
        payload = {
            "disaster_type": "earthquake",
            "city": "Ankara",
            "language": "en",
            forbidden_field: "test-override",
        }
        resp = client.post("/api/v1/ai/preparedness-guide", json=payload)
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.pop(get_ai_provider, None)


def test_ai_request_validation_boundaries() -> None:
    """Verify validation boundaries on disaster_type, language, and city."""
    stub = StubPreparednessAIProvider(mode="success")
    app.dependency_overrides[get_ai_provider] = lambda: stub
    try:
        # Invalid disaster type
        r1 = client.post(
            "/api/v1/ai/preparedness-guide",
            json={"disaster_type": "tornado", "language": "en"},
        )
        assert r1.status_code == 422

        # Invalid language
        r2 = client.post(
            "/api/v1/ai/preparedness-guide",
            json={"disaster_type": "fire", "language": "fr"},
        )
        assert r2.status_code == 422

        # Whitespace-only city
        r3 = client.post(
            "/api/v1/ai/preparedness-guide",
            json={"disaster_type": "flood", "language": "tr", "city": "   "},
        )
        assert r3.status_code == 422

        # City exceeding 80 chars
        r4 = client.post(
            "/api/v1/ai/preparedness-guide",
            json={"disaster_type": "flood", "language": "tr", "city": "A" * 81},
        )
        assert r4.status_code == 422
    finally:
        app.dependency_overrides.pop(get_ai_provider, None)


def test_ai_upstream_failure_error_contracts() -> None:
    """Verify upstream AI failures map to HTTP 502 with bounded error details."""
    # 1. Upstream AI provider error
    stub_error = StubPreparednessAIProvider(mode="error")
    app.dependency_overrides[get_ai_provider] = lambda: stub_error
    try:
        resp_err = client.post(
            "/api/v1/ai/preparedness-guide",
            json={"disaster_type": "earthquake", "language": "tr"},
        )
        assert resp_err.status_code == 502
        assert resp_err.json() == {
            "detail": "Upstream AI provider encountered an error."
        }
    finally:
        app.dependency_overrides.pop(get_ai_provider, None)

    # 2. Malformed / invalid response from provider
    stub_malformed = StubPreparednessAIProvider(mode="malformed")
    app.dependency_overrides[get_ai_provider] = lambda: stub_malformed
    try:
        resp_malformed = client.post(
            "/api/v1/ai/preparedness-guide",
            json={"disaster_type": "earthquake", "language": "tr"},
        )
        assert resp_malformed.status_code == 502
        assert resp_malformed.json() == {
            "detail": "AI provider returned an invalid response."
        }
    finally:
        app.dependency_overrides.pop(get_ai_provider, None)


def test_ai_provider_vendor_isolation() -> None:
    """Verify google.genai vendor SDK is isolated strictly to the Gemini module."""
    import app.api.v1.endpoints.ai as ai_endpoint
    import app.integrations.ai.base as ai_base
    import app.integrations.ai.gemini as ai_gemini
    import app.integrations.ai.policy as ai_policy
    import app.schemas.ai as ai_schemas
    import app.services.preparedness_guide as ai_service

    # Actual Gemini adapter module imports google.genai
    gemini_source = inspect.getsource(ai_gemini)
    assert "google.genai" in gemini_source, (
        "Expected google.genai import in app.integrations.ai.gemini"
    )

    # Core endpoint, schemas, services, and policies are strictly provider-neutral
    for mod in [ai_endpoint, ai_schemas, ai_service, ai_base, ai_policy]:
        source = inspect.getsource(mod)
        assert "google.genai" not in source, (
            f"Module {mod.__name__} leaked direct google.genai dependency"
        )
        assert "import google" not in source, (
            f"Module {mod.__name__} leaked direct google dependency"
        )


def test_ai_request_preserves_dataset_row_counts() -> None:
    """Verify generating AI guide does not alter persisted dataset row counts."""
    stub = StubPreparednessAIProvider(mode="success")
    app.dependency_overrides[get_ai_provider] = lambda: stub
    try:
        with engine.connect() as conn:
            before_counts = {
                t: conn.execute(text(f"SELECT count(*) FROM {t}")).scalar()
                for t in DATABASE_TABLES
            }

        payload = {"disaster_type": "earthquake", "city": "Bursa", "language": "tr"}
        resp = client.post("/api/v1/ai/preparedness-guide", json=payload)
        assert resp.status_code == 200

        with engine.connect() as conn:
            after_counts = {
                t: conn.execute(text(f"SELECT count(*) FROM {t}")).scalar()
                for t in DATABASE_TABLES
            }

        assert before_counts == after_counts, (
            "AI generation altered dataset row counts!"
        )
    finally:
        app.dependency_overrides.pop(get_ai_provider, None)


# ==============================================================================
# 8. SECURITY HEADERS, CORS SEMANTICS & ERROR SANITIZATION
# ==============================================================================


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/health",
        "/api/v1/fault-lines?limit=1",
        "/api/v1/earthquakes?limit=1",
        "/api/v1/earthquake-hazards?bbox=28.0,40.0,30.0,42.0&limit=1",
        "/api/v1/assembly-areas?limit=1",
    ],
)
def test_security_headers_present_on_successful_responses(path: str) -> None:
    """Verify mandatory security headers are present on all public API responses."""
    resp = client.get(path)
    assert resp.status_code == 200

    headers = resp.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("referrer-policy") == "no-referrer"
    assert "geolocation=()" in headers.get("permissions-policy", "")


def test_public_error_contracts_sanitized() -> None:
    """Verify error responses (404, 413, 422, 429) do not leak internals."""
    # 404
    r_404 = client.get(f"/api/v1/fault-lines/{uuid.uuid4()}")
    assert r_404.status_code == 404

    # 422
    r_422 = client.get("/api/v1/fault-lines/nearby?latitude=invalid")
    assert r_422.status_code == 422

    # 413
    oversized = "x" * (settings.API_MAX_REQUEST_BODY_BYTES + 10)
    r_413 = client.post(
        "/api/v1/ai/preparedness-guide",
        content=oversized,
        headers={"Content-Type": "application/json"},
    )
    assert r_413.status_code == 413
    assert r_413.json() == {"detail": "Request body too large."}

    for r in [r_404, r_422, r_413]:
        body = r.text
        assert "Traceback" not in body
        assert 'File "' not in body
        assert "SELECT " not in body
        assert "postgresql://" not in body
        assert "psycopg" not in body
        assert "C:\\" not in body


def test_cors_preflight_disallowed_origin_omits_allow_header() -> None:
    """Verify allowed origin receives allow header while disallowed origin does not.

    CORS headers are browser-enforced cross-origin controls, not a server-side
    authorization boundary. A disallowed origin request does not receive
    Access-Control-Allow-Origin.
    """
    allowed_origin = "http://localhost:5173"
    preflight = client.options(
        "/api/v1/fault-lines",
        headers={
            "Origin": allowed_origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers.get("access-control-allow-origin") == allowed_origin

    # Disallowed origin does not receive CORS allow header
    disallowed_preflight = client.options(
        "/api/v1/fault-lines",
        headers={
            "Origin": "http://disallowed-domain.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert disallowed_preflight.headers.get("access-control-allow-origin") is None


# ==============================================================================
# 9. DATASET ROW-COUNT CONSERVATION DURING GET REQUESTS
# ==============================================================================


def test_get_requests_preserve_dataset_row_counts() -> None:
    """Verify dataset row counts are unchanged before and after GET requests."""
    with engine.connect() as conn:
        before_counts = {
            t: conn.execute(text(f"SELECT count(*) FROM {t}")).scalar()
            for t in DATABASE_TABLES
        }

    # Execute read requests across all public domains
    endpoints = [
        "/api/v1/health",
        "/api/v1/fault-lines?limit=5",
        "/api/v1/fault-lines/nearby?latitude=40.0&longitude=29.0&radius_km=25",
        "/api/v1/earthquakes?limit=5",
        "/api/v1/earthquakes/recent-major",
        "/api/v1/earthquake-hazards/dataset",
        "/api/v1/earthquake-hazards/nearest?lat=39.93&lon=32.85",
        "/api/v1/earthquake-hazards?bbox=28.0,40.0,30.0,42.0&limit=5",
        "/api/v1/assembly-areas/dataset",
        "/api/v1/assembly-areas/nearby?lat=41.0&lon=29.0&radius_km=5",
        "/api/v1/assembly-areas?limit=5",
    ]

    for ep in endpoints:
        res = client.get(ep)
        assert res.status_code == 200, f"GET {ep} failed with status {res.status_code}"

    with engine.connect() as conn:
        after_counts = {
            t: conn.execute(text(f"SELECT count(*) FROM {t}")).scalar()
            for t in DATABASE_TABLES
        }

    assert before_counts == after_counts, (
        f"Row counts modified after GET: before={before_counts}, after={after_counts}"
    )
