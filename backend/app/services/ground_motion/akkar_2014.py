"""Akkar, Sandıkkaya & Bommer (2014) point-source model (AkkarEtAlRhyp2014).

Mathematical formulation and coefficient values are sourced directly from:
    Akkar, S., Sandıkkaya, M. A., & Bommer, J. J. (2014).
    Empirical ground-motion models for point- and extended-source crustal
    earthquake scenarios in Europe and the Middle East.
    Bulletin of Earthquake Engineering, 12(1), 359–387.
    DOI: 10.1007/s10518-013-9461-4

This implementation evaluates the point-source hypocentral-distance (Rhyp)
formulation for Peak Ground Acceleration (PGA) in active shallow crust.
It uses only standard-library math and is completely stateless.
"""

import math
from dataclasses import dataclass

# Model metadata constants
MODEL_NAME = "AkkarEtAlRhyp2014"
MODEL_CITATION = (
    "Akkar, S., Sandıkkaya, M. A., & Bommer, J. J. (2014). "
    "Empirical ground-motion models for point- and extended-source crustal "
    "earthquake scenarios in Europe and the Middle East. "
    "Bulletin of Earthquake Engineering, 12(1), 359–387."
)
MODEL_DOI = "10.1007/s10518-013-9461-4"
TECTONIC_REGION = "active_shallow_crust"
INTENSITY_MEASURE = "PGA"
PGA_UNIT = "g"
HORIZONTAL_COMPONENT = "geometric_mean_horizontal"

# Exact regression coefficients for PGA (Rhyp formulation, Table 4.b)
_A1 = 3.26685
_A2 = 0.0029
_A3 = -0.04846
_A4 = -1.47905
_A5 = 0.2529
_A6 = 7.5
_A7 = -0.5096
_A8 = -0.1091
_A9 = 0.0937

# Reference magnitude (Mw)
_C1 = 6.75

# Site amplification model constants (Sandıkkaya et al., 2013 / Table 3 & 4.b)
_V_REF = 750.0
_V_CON = 1000.0
_C = 2.5
_N = 3.2
_B1 = -0.41997
_B2 = -0.28846

# Standard deviations (natural log units):
# phi = intra-event standard deviation, tau = inter-event standard deviation
_PHI = 0.6475
_TAU = 0.3472
TOTAL_SIGMA_LN = math.sqrt(_PHI**2 + _TAU**2)

# Applicability bounds
MIN_MAGNITUDE_MW = 4.0
MAX_MAGNITUDE_MW = 7.6  # AFET360 calibration-data / no-extrapolation guard
MAX_RHYPO_KM = 200.0
MAX_FOCAL_DEPTH_KM = 30.0
MIN_VS30_M_S = 150.0
MAX_VS30_M_S = 1200.0


@dataclass(frozen=True)
class AkkarRhypPgaResult:
    """Ground-motion prediction result for Akkar et al. (2014) Rhyp PGA."""

    median_pga_g: float
    total_sigma_ln: float
    minus_1sigma_pga_g: float
    plus_1sigma_pga_g: float


def calculate_akkar_rhyp_pga(
    magnitude_mw: float,
    rhypo_km: float,
    rake_degrees: float,
    vs30_m_s: float = 800.0,
) -> AkkarRhypPgaResult:
    """Calculate median PGA (g) and ±1σ variability for a point-source scenario.

    Parameters
    ----------
    magnitude_mw : float
        Moment magnitude Mw in [4.0, 7.6].
    rhypo_km : float
        Hypocentral distance Rhyp in km (0 < Rhyp <= 200.0).
    rake_degrees : float
        Fault slip rake angle in degrees (-180 to 180).
        Representative canonical mappings:
          - Strike-slip: 0.0 deg
          - Normal: -90.0 deg
          - Reverse: +90.0 deg
    vs30_m_s : float, optional
        Time-averaged shear-wave velocity in upper 30 m in m/s (150.0 to 1200.0).
        Defaults to 800.0 m/s (reference rock).

    Returns
    -------
    AkkarRhypPgaResult
        Contains median_pga_g, total_sigma_ln, minus_1sigma_pga_g, plus_1sigma_pga_g.
    """
    if not (MIN_MAGNITUDE_MW <= magnitude_mw <= MAX_MAGNITUDE_MW):
        raise ValueError(
            f"magnitude_mw {magnitude_mw} is outside the calibration guard "
            f"[{MIN_MAGNITUDE_MW}, {MAX_MAGNITUDE_MW}]."
        )
    if not (0.0 < rhypo_km <= MAX_RHYPO_KM):
        raise ValueError(
            f"rhypo_km {rhypo_km} is outside the model applicability range "
            f"(0.0, {MAX_RHYPO_KM}]."
        )
    if not (MIN_VS30_M_S <= vs30_m_s <= MAX_VS30_M_S):
        raise ValueError(
            f"vs30_m_s {vs30_m_s} is outside the model applicability range "
            f"[{MIN_VS30_M_S}, {MAX_VS30_M_S}]."
        )

    # 1. Faulting style term (Eq 2a/2b)
    # Normal faulting: -135 < rake < -45
    # Reverse faulting: 45 < rake < 135
    # Strike-slip: otherwise (reference mechanism, f_flt = 0)
    is_normal = -135.0 < rake_degrees < -45.0
    is_reverse = 45.0 < rake_degrees < 135.0

    f_flt = 0.0
    if is_normal:
        f_flt = _A8
    elif is_reverse:
        f_flt = _A9

    # 2. Linear magnitude scaling (Eq 2a/2b)
    delta_m = magnitude_mw - _C1
    if magnitude_mw <= _C1:
        f_mag1 = _A2 * delta_m
    else:
        f_mag1 = _A7 * delta_m

    # 3. Quadratic magnitude scaling (Eq 2a/2b)
    f_mag2 = _A3 * ((8.5 - magnitude_mw) ** 2)

    # 4. Fictitious depth and geometric attenuation (Eq 2a/2b)
    r_effective = math.sqrt(rhypo_km**2 + _A6**2)
    f_dist = (_A4 + _A5 * delta_m) * math.log(r_effective)

    # 5. Reference rock ground-motion mean ln(PGA_rock in g)
    mean_rock_ln = _A1 + f_mag1 + f_mag2 + f_dist + f_flt
    pga_rock = math.exp(mean_rock_ln)

    # 6. Non-linear site amplification term ln(S) (Eq 3a-3c)
    if vs30_m_s < _V_REF:
        v_ratio = vs30_m_s / _V_REF
        denom_part = (pga_rock + _C) * (v_ratio**_N)
        numer_part = pga_rock + _C * (v_ratio**_N)
        ln_s = _B1 * math.log(v_ratio) + _B2 * math.log(numer_part / denom_part)
    elif vs30_m_s <= _V_CON:
        ln_s = _B1 * math.log(vs30_m_s / _V_REF)
    else:
        ln_s = _B1 * math.log(_V_CON / _V_REF)

    # Total mean natural logarithm of PGA (in g)
    mean_ln_pga = mean_rock_ln + ln_s

    median_pga_g = math.exp(mean_ln_pga)
    minus_1sigma = math.exp(mean_ln_pga - TOTAL_SIGMA_LN)
    plus_1sigma = math.exp(mean_ln_pga + TOTAL_SIGMA_LN)

    return AkkarRhypPgaResult(
        median_pga_g=median_pga_g,
        total_sigma_ln=TOTAL_SIGMA_LN,
        minus_1sigma_pga_g=minus_1sigma,
        plus_1sigma_pga_g=plus_1sigma,
    )
