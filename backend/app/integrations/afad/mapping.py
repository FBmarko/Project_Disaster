from datetime import UTC, datetime
from typing import Any

# Regional tectonic context bounding box: 24.0°E - 46.0°E, 34.0°N - 44.0°N
TURKEY_CONTEXT_BBOX = (24.0, 34.0, 46.0, 44.0)

AFAD_DEFAULT_BASE_URL = "https://deprem.afad.gov.tr/apiv2/event/filter"

AFAD_ATTRIBUTION_SOURCE = (
    "T.C. İçişleri Bakanlığı Afet ve Acil Durum Yönetimi Başkanlığı (AFAD)"
)
AFAD_ATTRIBUTION_DATASET = "AFAD Deprem Dairesi Başkanlığı Event Web Service"
AFAD_ATTRIBUTION_NOTICE = (
    "Deprem verileri T.C. İçişleri Bakanlığı AFAD Deprem Dairesi Başkanlığı "
    "Event Web Servisi üzerinden temin edilmiştir."
)


def parse_afad_datetime(dt_str: Any) -> datetime:
    """Parse AFAD ISO-like datetime string into a timezone-aware UTC datetime.

    Live verification confirms AFAD Event Web Service timestamps represent UTC.
    For example: 2023-02-06 Kahramanmaraş earthquake (04:17:32 TSİ) is reported as
    '2023-02-06T01:17:32' in the API.
    """
    if not dt_str or not isinstance(dt_str, str):
        raise ValueError(f"Invalid timestamp string: {dt_str}")

    cleaned = dt_str.strip().replace(" ", "T")
    dt = datetime.fromisoformat(cleaned)

    # Attach UTC if naive
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)

    return dt


def coords_to_point_wkt(longitude: float, latitude: float) -> str:
    """Format WGS84 coordinates into PostGIS Point WKT (lon lat)."""
    return f"SRID=4326;POINT({longitude} {latitude})"
