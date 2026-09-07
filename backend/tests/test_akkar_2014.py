"""Unit tests and reference vector regression for Akkar et al. (2014) Rhyp PGA.

Provenance:
- Formulation and coefficients from Akkar, Sandıkkaya & Bommer (2014),
  Bulletin of Earthquake Engineering 12:359-387, DOI: 10.1007/s10518-013-9461-4.
- Independent reference oracle: cross-checked against GEM OpenQuake hazardlib
  AkkarEtAlRhyp2014 implementation for active shallow crustal point sources.
"""

import math

import pytest

from app.services.ground_motion.akkar_2014 import (
    TOTAL_SIGMA_LN,
    calculate_akkar_rhyp_pga,
)

# Reference regression vectors locked in task specification
# Format: (Mw, Rhyp_km, rake_deg, vs30_m_s, expected_median_pga_g)
LOCKED_REFERENCE_VECTORS = [
    (6.5, 10.0, 0.0, 800.0, 0.4273348472),
    (6.5, 20.0, 0.0, 800.0, 0.1870226216),
    (6.5, 50.0, 0.0, 800.0, 0.0495192992),
    (6.5, 20.0, -90.0, 800.0, 0.1676921035),
    (6.5, 20.0, 90.0, 800.0, 0.2053938962),
    (4.5, 20.0, 0.0, 800.0, 0.0220959103),
    (7.5, 20.0, 0.0, 800.0, 0.3203432582),
]


def test_akkar_total_sigma_ln() -> None:
    """Verify total log-normal standard deviation equals sqrt(phi^2 + tau^2)."""
    expected_sigma = 0.7347136109
    assert math.isclose(TOTAL_SIGMA_LN, expected_sigma, rel_tol=1e-8)


@pytest.mark.parametrize(
    ("mag", "rhyp", "rake", "vs30", "expected_pga"),
    LOCKED_REFERENCE_VECTORS,
)
def test_akkar_locked_reference_vectors(
    mag: float,
    rhyp: float,
    rake: float,
    vs30: float,
    expected_pga: float,
) -> None:
    """Verify calculation reproduces locked reference outputs with high precision."""
    res = calculate_akkar_rhyp_pga(mag, rhyp, rake, vs30)

    # Assert within 1e-6 relative tolerance (actual difference is ~1e-10)
    assert math.isclose(res.median_pga_g, expected_pga, rel_tol=1e-6, abs_tol=1e-7)
    assert res.minus_1sigma_pga_g < res.median_pga_g < res.plus_1sigma_pga_g
    assert math.isclose(
        res.minus_1sigma_pga_g,
        math.exp(math.log(res.median_pga_g) - TOTAL_SIGMA_LN),
        rel_tol=1e-10,
    )
    assert math.isclose(
        res.plus_1sigma_pga_g,
        math.exp(math.log(res.median_pga_g) + TOTAL_SIGMA_LN),
        rel_tol=1e-10,
    )


def test_akkar_vs30_boundaries() -> None:
    """Verify calculation at model boundary points: Vref, Vcon, lower/upper bounds."""
    # Vref boundary (750 m/s)
    res_750 = calculate_akkar_rhyp_pga(6.5, 20.0, 0.0, 750.0)
    assert res_750.median_pga_g > 0
    assert math.isfinite(res_750.median_pga_g)

    # Vcon boundary (1000 m/s)
    res_1000 = calculate_akkar_rhyp_pga(6.5, 20.0, 0.0, 1000.0)
    assert res_1000.median_pga_g > 0
    assert math.isfinite(res_1000.median_pga_g)

    # Lower bound (150 m/s)
    res_150 = calculate_akkar_rhyp_pga(6.5, 20.0, 0.0, 150.0)
    assert res_150.median_pga_g > 0
    assert math.isfinite(res_150.median_pga_g)

    # Upper bound (1200 m/s)
    res_1200 = calculate_akkar_rhyp_pga(6.5, 20.0, 0.0, 1200.0)
    assert res_1200.median_pga_g > 0
    assert math.isfinite(res_1200.median_pga_g)

    # Beyond Vcon (1000), site term is capped at Vcon; 1000 & 1200 give equal results
    assert math.isclose(res_1000.median_pga_g, res_1200.median_pga_g, rel_tol=1e-12)


def test_akkar_distance_attenuation_monotonicity() -> None:
    """For a fixed scenario, median PGA must strictly decrease as Rhyp increases."""
    distances = [5.0, 10.0, 20.0, 35.0, 50.0, 75.0, 100.0, 150.0, 200.0]
    results = [
        calculate_akkar_rhyp_pga(6.5, d, 0.0, 800.0).median_pga_g for d in distances
    ]

    for i in range(len(results) - 1):
        assert results[i] > results[i + 1], (
            f"Expected PGA at {distances[i]} km ({results[i]}) to be greater than "
            f"at {distances[i + 1]} km ({results[i + 1]})"
        )


def test_akkar_deterministic_repeatability() -> None:
    """Sequential invocations with identical parameters must return identical values."""
    res1 = calculate_akkar_rhyp_pga(6.8, 15.2, 0.0, 800.0)
    res2 = calculate_akkar_rhyp_pga(6.8, 15.2, 0.0, 800.0)
    assert res1 == res2


def test_akkar_guard_validations() -> None:
    """Out-of-range parameters must raise ValueError."""
    # Magnitude out of bounds
    with pytest.raises(ValueError, match="magnitude_mw"):
        calculate_akkar_rhyp_pga(3.9, 20.0, 0.0, 800.0)
    with pytest.raises(ValueError, match="magnitude_mw"):
        calculate_akkar_rhyp_pga(7.7, 20.0, 0.0, 800.0)

    # Rhyp out of bounds
    with pytest.raises(ValueError, match="rhypo_km"):
        calculate_akkar_rhyp_pga(6.5, 0.0, 0.0, 800.0)
    with pytest.raises(ValueError, match="rhypo_km"):
        calculate_akkar_rhyp_pga(6.5, 200.1, 0.0, 800.0)

    # Vs30 out of bounds
    with pytest.raises(ValueError, match="vs30_m_s"):
        calculate_akkar_rhyp_pga(6.5, 20.0, 0.0, 149.9)
    with pytest.raises(ValueError, match="vs30_m_s"):
        calculate_akkar_rhyp_pga(6.5, 20.0, 0.0, 1200.1)
