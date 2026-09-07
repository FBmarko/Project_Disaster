"""Stateless scenario calculation service for deterministic ground-motion simulation."""

import math

from app.schemas.scenario_api import (
    DEFAULT_SCENARIO_DISCLAIMER,
    FaultMechanism,
    ScenarioCalculationRequest,
    ScenarioCalculationResponse,
    ScenarioModelMetadata,
    ScenarioModelScope,
    ScenarioParameters,
    ScenarioPointEstimate,
)
from app.services.ground_motion.akkar_2014 import (
    HORIZONTAL_COMPONENT,
    INTENSITY_MEASURE,
    MAX_FOCAL_DEPTH_KM,
    MAX_MAGNITUDE_MW,
    MAX_RHYPO_KM,
    MAX_VS30_M_S,
    MIN_MAGNITUDE_MW,
    MIN_VS30_M_S,
    MODEL_CITATION,
    MODEL_DOI,
    MODEL_NAME,
    PGA_UNIT,
    TECTONIC_REGION,
    TOTAL_SIGMA_LN,
    calculate_akkar_rhyp_pga,
)

PROFILE_STEP_KM = 5

_MECHANISM_RAKE_MAP: dict[FaultMechanism, float] = {
    FaultMechanism.strike_slip: 0.0,
    FaultMechanism.normal: -90.0,
    FaultMechanism.reverse: 90.0,
}


def calculate_scenario(
    request: ScenarioCalculationRequest,
) -> ScenarioCalculationResponse:
    """Calculate a deterministic ground-motion scenario along a radial distance profile.

    Parameters
    ----------
    request : ScenarioCalculationRequest
        Validated scenario request parameters.

    Returns
    -------
        Complete scenario response including model metadata, inputs,
        epicentral estimate, and 5-km sampled radial attenuation profile.
    """
    rake_degrees = _MECHANISM_RAKE_MAP[request.mechanism]
    mag = request.magnitude_mw
    depth = request.depth_km
    vs30 = request.vs30_m_s
    max_dist = request.max_surface_distance_km

    # Generate radial attenuation profile at 5-km increments: 0, 5, 10, ..., max_dist
    profile_points: list[ScenarioPointEstimate] = []
    num_steps = max_dist // PROFILE_STEP_KM

    for step_idx in range(num_steps + 1):
        surface_dist = float(step_idx * PROFILE_STEP_KM)
        rhypo = math.hypot(surface_dist, depth)

        if rhypo > MAX_RHYPO_KM:
            raise ValueError(
                f"Computed hypocentral distance {rhypo:.2f} km exceeds the "
                f"model applicability limit of {MAX_RHYPO_KM} km."
            )

        calc = calculate_akkar_rhyp_pga(
            magnitude_mw=mag,
            rhypo_km=rhypo,
            rake_degrees=rake_degrees,
            vs30_m_s=vs30,
        )

        profile_points.append(
            ScenarioPointEstimate(
                surface_distance_km=surface_dist,
                rhypo_km=round(rhypo, 3),
                median_pga_g=round(calc.median_pga_g, 6),
                minus_1sigma_pga_g=round(calc.minus_1sigma_pga_g, 6),
                plus_1sigma_pga_g=round(calc.plus_1sigma_pga_g, 6),
            )
        )

    epicenter_estimate = profile_points[0]

    return ScenarioCalculationResponse(
        model=ScenarioModelMetadata(
            name=MODEL_NAME,
            citation=MODEL_CITATION,
            doi=MODEL_DOI,
            tectonic_region=TECTONIC_REGION,
            component=HORIZONTAL_COMPONENT,
            intensity_measure=INTENSITY_MEASURE,
            unit=PGA_UNIT,
        ),
        scenario=ScenarioParameters(
            epicenter=request.epicenter,
            magnitude_mw=mag,
            depth_km=depth,
            mechanism=request.mechanism,
            rake_degrees=rake_degrees,
            vs30_m_s=vs30,
            max_surface_distance_km=max_dist,
        ),
        model_scope=ScenarioModelScope(
            af360_magnitude_guard=[MIN_MAGNITUDE_MW, MAX_MAGNITUDE_MW],
            max_rhypo_km=MAX_RHYPO_KM,
            max_focal_depth_km=MAX_FOCAL_DEPTH_KM,
            vs30_m_s=[MIN_VS30_M_S, MAX_VS30_M_S],
        ),
        total_sigma_ln=round(TOTAL_SIGMA_LN, 6),
        epicenter_estimate=epicenter_estimate,
        profile_step_km=PROFILE_STEP_KM,
        radial_profile=profile_points,
        disclaimer=DEFAULT_SCENARIO_DISCLAIMER,
    )
