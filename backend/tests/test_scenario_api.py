"""Contract and behavior tests for POST /api/v1/earthquake-hazards/scenario."""

import math

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SCENARIO_URL = "/api/v1/earthquake-hazards/scenario"


def _make_valid_payload(**overrides) -> dict:
    base = {
        "epicenter": {
            "latitude": 40.8,
            "longitude": 29.4,
        },
        "magnitude_mw": 6.8,
        "depth_km": 10.0,
        "mechanism": "strike_slip",
        "vs30_m_s": 800.0,
        "max_surface_distance_km": 150,
    }
    base.update(overrides)
    return base


def test_scenario_valid_request_200_contract() -> None:
    """Verify standard valid scenario request returns 200 with full contract."""
    payload = _make_valid_payload()
    resp = client.post(SCENARIO_URL, json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # Model metadata
    model = data["model"]
    assert model["name"] == "AkkarEtAlRhyp2014"
    assert "Akkar, S." in model["citation"]
    assert model["doi"] == "10.1007/s10518-013-9461-4"
    assert model["tectonic_region"] == "active_shallow_crust"
    assert model["component"] == "geometric_mean_horizontal"
    assert model["intensity_measure"] == "PGA"
    assert model["unit"] == "g"

    # Scenario parameters echoed
    scenario = data["scenario"]
    assert scenario["epicenter"]["latitude"] == 40.8
    assert scenario["epicenter"]["longitude"] == 29.4
    assert scenario["magnitude_mw"] == 6.8
    assert scenario["depth_km"] == 10.0
    assert scenario["mechanism"] == "strike_slip"
    assert scenario["rake_degrees"] == 0.0
    assert scenario["vs30_m_s"] == 800.0
    assert scenario["max_surface_distance_km"] == 150

    # Model scope guards
    scope = data["model_scope"]
    assert scope["af360_magnitude_guard"] == [4.0, 7.6]
    assert scope["max_rhypo_km"] == 200.0
    assert scope["max_focal_depth_km"] == 30.0
    assert scope["vs30_m_s"] == [150.0, 1200.0]

    # Total sigma
    assert math.isclose(data["total_sigma_ln"], 0.734714, rel_tol=1e-5)

    # Epicenter estimate
    epi = data["epicenter_estimate"]
    assert epi["surface_distance_km"] == 0.0
    assert epi["rhypo_km"] == 10.0
    assert epi["median_pga_g"] > 0
    assert epi["minus_1sigma_pga_g"] < epi["median_pga_g"] < epi["plus_1sigma_pga_g"]

    # Radial profile length: 150 / 5 + 1 = 31 points
    profile = data["radial_profile"]
    assert len(profile) == 31
    assert data["profile_step_km"] == 5

    # Check first and last profile items
    first = profile[0]
    assert first["surface_distance_km"] == 0.0
    assert first["rhypo_km"] == 10.0
    assert first["median_pga_g"] == epi["median_pga_g"]

    last = profile[-1]
    assert last["surface_distance_km"] == 150.0
    expected_last_rhyp = math.hypot(150.0, 10.0)
    assert math.isclose(last["rhypo_km"], expected_last_rhyp, rel_tol=1e-3)
    assert last["median_pga_g"] < first["median_pga_g"]

    # Invariant checks for every profile point
    for point in profile:
        s_dist = point["surface_distance_km"]
        expected_rhyp = math.hypot(s_dist, 10.0)
        assert math.isclose(point["rhypo_km"], expected_rhyp, rel_tol=1e-3)
        assert point["median_pga_g"] > 0
        assert math.isfinite(point["median_pga_g"])
        assert (
            point["minus_1sigma_pga_g"]
            < point["median_pga_g"]
            < point["plus_1sigma_pga_g"]
        )

    # Scientific disclaimer
    assert "deprem tahmini veya olasılık analizi değildir" in data["disclaimer"]

    # Ensure prohibited fields are NOT present
    raw_text = resp.text
    for forbidden in ["MMI", "risk_level", "damage", "casualty", "probability"]:
        assert forbidden not in raw_text


@pytest.mark.parametrize(
    ("mechanism", "expected_rake"),
    [
        ("strike_slip", 0.0),
        ("normal", -90.0),
        ("reverse", 90.0),
    ],
)
def test_scenario_mechanism_rake_mappings(
    mechanism: str,
    expected_rake: float,
) -> None:
    """Verify faulting mechanisms correctly map to representative rake angles."""
    payload = _make_valid_payload(mechanism=mechanism)
    resp = client.post(SCENARIO_URL, json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["scenario"]["mechanism"] == mechanism
    assert data["scenario"]["rake_degrees"] == expected_rake


@pytest.mark.parametrize("radius", [25, 50, 100, 150])
def test_scenario_supported_radii_counts(radius: int) -> None:
    """Verify allowed surface radii produce the exact expected step count."""
    payload = _make_valid_payload(max_surface_distance_km=radius)
    resp = client.post(SCENARIO_URL, json=payload)
    assert resp.status_code == 200
    profile = resp.json()["radial_profile"]
    expected_count = (radius // 5) + 1
    assert len(profile) == expected_count
    assert profile[-1]["surface_distance_km"] == float(radius)


def test_scenario_default_vs30_800() -> None:
    """Verify omittable vs30_m_s defaults to 800.0."""
    payload = _make_valid_payload()
    del payload["vs30_m_s"]
    resp = client.post(SCENARIO_URL, json=payload)
    assert resp.status_code == 200
    assert resp.json()["scenario"]["vs30_m_s"] == 800.0


def test_scenario_deterministic_repeatability() -> None:
    """Verify identical requests return bit-for-bit identical results."""
    payload = _make_valid_payload()
    resp1 = client.post(SCENARIO_URL, json=payload).json()
    resp2 = client.post(SCENARIO_URL, json=payload).json()
    assert resp1 == resp2


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        # Magnitude boundaries (4.0 to 7.6)
        ("magnitude_mw", 3.9),
        ("magnitude_mw", 7.7),
        ("magnitude_mw", 0.0),
        ("magnitude_mw", -5.0),
        # Depth boundaries (0 < depth <= 30.0)
        ("depth_km", 0.0),
        ("depth_km", -1.0),
        ("depth_km", 30.1),
        ("depth_km", 50.0),
        # Vs30 boundaries (150 to 1200)
        ("vs30_m_s", 149.0),
        ("vs30_m_s", 1201.0),
        # Mechanism invalid enum
        ("mechanism", "unknown"),
        ("mechanism", "oblique"),
        ("mechanism", "strike-slip"),
        # Max surface distance options (25, 50, 100, 150)
        ("max_surface_distance_km", 30),
        ("max_surface_distance_km", 0),
        ("max_surface_distance_km", 200),
    ],
)
def test_scenario_validation_errors_422(field: str, invalid_value: object) -> None:
    """Invalid parameter values must produce HTTP 422 with validation detail."""
    payload = _make_valid_payload(**{field: invalid_value})
    resp = client.post(SCENARIO_URL, json=payload)
    assert resp.status_code == 422


@pytest.mark.parametrize(
    ("lat", "lon"),
    [
        (90.1, 30.0),
        (-90.1, 30.0),
        (40.0, 180.1),
        (40.0, -180.1),
    ],
)
def test_scenario_invalid_coordinates_422(lat: float, lon: float) -> None:
    """Out-of-bound coordinates must produce HTTP 422."""
    payload = _make_valid_payload(epicenter={"latitude": lat, "longitude": lon})
    resp = client.post(SCENARIO_URL, json=payload)
    assert resp.status_code == 422


def test_scenario_extra_fields_forbidden_422() -> None:
    """Extra unexpected payload fields must be rejected with HTTP 422."""
    payload = _make_valid_payload(unsupported_extra_field="malicious")
    resp = client.post(SCENARIO_URL, json=payload)
    assert resp.status_code == 422
