"""Pydantic schemas for ground-motion scenario calculation (Akkar et al., 2014)."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_SCENARIO_DISCLAIMER = (
    "Bu hesaplama kullanıcı tarafından belirlenen varsayımsal bir deprem "
    "senaryosudur; deprem tahmini veya olasılık analizi değildir. Sonuçlar "
    "Akkar ve ark. (2014) yer hareketi modelinin medyan PGA kestirimleridir; "
    "yapı hasarını, can kaybını veya resmî mühendislik değerlendirmesini temsil etmez."
)


class ScenarioEpicenter(BaseModel):
    """Epicenter geographic coordinate pair."""

    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="WGS84 epicenter latitude in decimal degrees (-90.0 to 90.0)",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="WGS84 epicenter longitude in decimal degrees (-180.0 to 180.0)",
    )


class FaultMechanism(StrEnum):
    """Supported faulting style mechanism for ground-motion scaling."""

    strike_slip = "strike_slip"
    normal = "normal"
    reverse = "reverse"


class ScenarioCalculationRequest(BaseModel):
    """Request payload for deterministic scenario ground-motion calculation."""

    model_config = ConfigDict(extra="forbid")

    epicenter: ScenarioEpicenter = Field(
        ..., description="Epicenter location of the hypothetical earthquake"
    )
    magnitude_mw: float = Field(
        ...,
        ge=4.0,
        le=7.6,
        description="Moment magnitude Mw within AFET360 calibration guard (4.0 to 7.6)",
    )
    depth_km: float = Field(
        ...,
        gt=0.0,
        le=30.0,
        description="Focal depth in kilometers (0 < depth <= 30.0)",
    )
    mechanism: FaultMechanism = Field(
        ...,
        description="Faulting mechanism: 'strike_slip', 'normal', or 'reverse'",
    )
    vs30_m_s: float = Field(
        800.0,
        ge=150.0,
        le=1200.0,
        description=(
            "Site Vs30 in m/s (150.0 to 1200.0, default 800.0 reference rock)"
        ),
    )
    max_surface_distance_km: int = Field(
        150,
        description="Calculation surface radius in km (one of: 25, 50, 100, 150)",
    )

    @field_validator("max_surface_distance_km")
    @classmethod
    def validate_surface_distance(cls, v: int) -> int:
        if v not in (25, 50, 100, 150):
            raise ValueError(
                "max_surface_distance_km must be exactly one of: 25, 50, 100, 150"
            )
        return v


class ScenarioModelMetadata(BaseModel):
    """Scientific metadata and provenance of the ground-motion model."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Model identifier")
    citation: str = Field(..., description="Full bibliographic literature citation")
    doi: str = Field(..., description="Digital Object Identifier")
    tectonic_region: str = Field(
        ..., description="Tectonic region applicability classification"
    )
    component: str = Field(
        ..., description="Ground-motion horizontal component definition"
    )
    intensity_measure: str = Field(..., description="Predicted intensity measure type")
    unit: str = Field(..., description="Physical measurement unit")


class ScenarioParameters(BaseModel):
    """Validated input parameters used in the scenario calculation."""

    model_config = ConfigDict(extra="forbid")

    epicenter: ScenarioEpicenter
    magnitude_mw: float
    depth_km: float
    mechanism: FaultMechanism
    rake_degrees: float
    vs30_m_s: float
    max_surface_distance_km: int


class ScenarioModelScope(BaseModel):
    """Model validity and AFET360 calibration guard ranges."""

    model_config = ConfigDict(extra="forbid")

    af360_magnitude_guard: list[float]
    max_rhypo_km: float
    max_focal_depth_km: float
    vs30_m_s: list[float]


class ScenarioPointEstimate(BaseModel):
    """Point estimate of ground-motion acceleration and variability."""

    model_config = ConfigDict(extra="forbid")

    surface_distance_km: float = Field(
        ..., description="Epicentral surface distance in kilometers"
    )
    rhypo_km: float = Field(
        ...,
        description="Hypocentral distance in km: hypot(surface_distance, depth)",
    )
    median_pga_g: float = Field(
        ..., description="Estimated median Peak Ground Acceleration in fractions of g"
    )
    minus_1sigma_pga_g: float = Field(
        ..., description="Lower -1σ aleatory model variability bound in fractions of g"
    )
    plus_1sigma_pga_g: float = Field(
        ..., description="Upper +1σ aleatory model variability bound in fractions of g"
    )


class ScenarioCalculationResponse(BaseModel):
    """Complete response payload for a deterministic scenario calculation."""

    model_config = ConfigDict(extra="forbid")

    model: ScenarioModelMetadata
    scenario: ScenarioParameters
    model_scope: ScenarioModelScope
    total_sigma_ln: float
    epicenter_estimate: ScenarioPointEstimate
    profile_step_km: int
    radial_profile: list[ScenarioPointEstimate]
    disclaimer: str
