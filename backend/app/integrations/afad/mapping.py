import calendar
from datetime import UTC, datetime
from typing import Any

# Regional tectonic context bounding box: 24.0°E - 46.0°E, 34.0°N - 44.0°N
TURKEY_CONTEXT_BBOX = (24.0, 34.0, 46.0, 44.0)

# AFAD Event Web Service URLs
AFAD_DEFAULT_BASE_URL = "https://deprem.afad.gov.tr/apiv2/event/filter"
AFAD_REDIRECT_TARGET_URL = (
    "https://servisnet.afad.gov.tr/apigateway/deprem/apiv2/event/filter"
)

# Project earthquake coverage policy defaults:
# - Rolling previous 10 calendar years
# - Minimum magnitude M >= 4.5
# - Sequential 90-day chunking
# - Bounded HTTP request budget
DEFAULT_COVERAGE_YEARS = 10
DEFAULT_MIN_MAGNITUDE = 4.5
DEFAULT_WINDOW_DAYS = 90
DEFAULT_MAX_PAGES_PER_WINDOW = 50
DEFAULT_PAGE_SIZE = 100
DEFAULT_MAX_HTTP_REQUESTS = 100

AFAD_ATTRIBUTION_SOURCE = (
    "T.C. İçişleri Bakanlığı Afet ve Acil Durum Yönetimi Başkanlığı (AFAD)"
)
AFAD_ATTRIBUTION_DATASET = "AFAD Deprem Dairesi Başkanlığı Event Web Service"
AFAD_ATTRIBUTION_NOTICE = (
    "Deprem verileri T.C. İçişleri Bakanlığı AFAD Deprem Dairesi Başkanlığı "
    "Event Web Servisi üzerinden temin edilmiştir."
)


def subtract_calendar_years(dt: datetime, years: int) -> datetime:
    """Subtract calendar years from a datetime with deterministic leap-day behavior.

    If the source date is February 29 and the target year is not a leap year,
    the day is clamped to February 28 of the target year.
    All time components (hour, minute, second, microsecond) and timezone info
    are preserved.
    """
    target_year = dt.year - years
    month = dt.month
    day = dt.day

    if month == 2 and day == 29 and not calendar.isleap(target_year):
        day = 28

    return dt.replace(year=target_year, day=day)


def get_project_coverage_start(
    reference_time: datetime | None = None,
    years: int = DEFAULT_COVERAGE_YEARS,
) -> datetime:
    """Compute the deterministic start timestamp for AFET360 project coverage.

    AFET360 project coverage policy:
        - Rolling previous `years` calendar years (default: 10 calendar years).
        - If reference_time is None, defaults to current UTC time.
        - Reference timestamps are normalized to UTC.
        - Leap-day behavior: February 29 rolls back to February 28 on non-leap
          target years.
    """
    if reference_time is None:
        ref = datetime.now(UTC)
    elif reference_time.tzinfo is None:
        ref = reference_time.replace(tzinfo=UTC)
    else:
        ref = reference_time.astimezone(UTC)

    return subtract_calendar_years(ref, years)


def parse_afad_datetime(dt_str: Any) -> datetime:
    """Parse AFAD datetime string into a timezone-aware datetime normalized to UTC.

    AFET360 normalizes ingested event timestamps to UTC for deterministic internal
    storage and temporal queries. Naive timestamps are interpreted as UTC.
    """
    if not dt_str or not isinstance(dt_str, str):
        raise ValueError(f"Invalid timestamp string: {dt_str}")

    cleaned = dt_str.strip().replace(" ", "T")
    dt = datetime.fromisoformat(cleaned)

    # Normalize to UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)

    return dt


def coords_to_point_wkt(longitude: float, latitude: float) -> str:
    """Format WGS84 coordinates into PostGIS Point WKT (lon lat)."""
    return f"SRID=4326;POINT({longitude} {latitude})"
