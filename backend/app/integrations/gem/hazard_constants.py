"""Constants and source specifications for the GEM Global Seismic Hazard Map (GSHM)."""

GEM_SOURCE_NAME = "GEM_GSHM"
GEM_SOURCE_VERSION = "2026.1"
GEM_MODEL_NAME = "GEM Global Seismic Hazard Map v2026.1"
GEM_HAZARD_METRIC = "PGA"
GEM_UNIT = "g"
GEM_RETURN_PERIOD_YEARS = 475
GEM_EXCEEDANCE_PROBABILITY = 0.10
GEM_TIME_HORIZON_YEARS = 50
GEM_REFERENCE_VS30_MPS = 800.0
GEM_REFERENCE_GROUND = "Reference Rock"

GEM_VERSION_DOI = "10.5281/zenodo.20735384"
GEM_CONCEPT_DOI = "10.5281/zenodo.8409646"
GEM_LICENSE = "CC BY-NC-SA 4.0"
GEM_ATTRIBUTION = (
    "Global Seismic Hazard Map (v2026.1), Global Earthquake Model (GEM) Foundation. "
    "Distributed under CC BY-NC-SA 4.0. Model represents reference rock ground motion "
    "(Vs30=800 m/s, 10% in 50 years / 475-yr return period) at discrete grid nodes. "
    "Not building safety or regulatory Turkish hazard data."
)

# Source Artifact Specs
GEM_ZIP_FILENAME = "gshm_v2026_1_vector.zip"
GEM_ZIP_SIZE_BYTES = 935540326
GEM_ZIP_MD5 = "7470e54534f4a4307a7310aa766ab11b"

GEM_GPKG_RELPATH = "gshm_v2026_1_vector/gem_gshm_v2026.1.gpkg"
GEM_GPKG_FILENAME = "gem_gshm_v2026.1.gpkg"
GEM_GPKG_SIZE_BYTES = 1761116160

# Ingestion Scope
TURKEY_CONTEXT_SCOPE = "turkey-context"
TURKEY_CONTEXT_BBOX = (24.0, 34.0, 46.0, 44.0)  # min_lon, min_lat, max_lon, max_lat
EXPECTED_TURKEY_POINT_COUNT = 54291
