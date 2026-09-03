import logging
from typing import Any

from app.integrations.afad.mapping import parse_afad_datetime
from app.schemas.earthquake_event import EarthquakeEventCreate

logger = logging.getLogger("afet360.integrations.afad")


def parse_afad_event(item: dict[str, Any]) -> EarthquakeEventCreate | None:
    """Parse a single raw AFAD JSON event dictionary into EarthquakeEventCreate.

    Handles numeric string coercion, UTC datetime parsing, and spatial validation.
    """
    if not isinstance(item, dict):
        logger.warning("Skipping non-dict AFAD item: %s", item)
        return None

    # Mandatory source event ID
    raw_id = item.get("eventID") or item.get("EventID")
    if raw_id is None or str(raw_id).strip() == "":
        logger.warning("Skipping AFAD item without eventID: %s", item)
        return None
    source_event_id = str(raw_id).strip()

    # Mandatory timestamp
    raw_date = item.get("date") or item.get("Date")
    if not raw_date:
        logger.warning("Skipping AFAD event %s without date", source_event_id)
        return None
    try:
        occurred_at = parse_afad_datetime(raw_date)
    except Exception as exc:
        logger.warning(
            "Skipping AFAD event %s with invalid date %s: %s",
            source_event_id,
            raw_date,
            exc,
        )
        return None

    # Mandatory spatial coordinates (AFAD returns strings like "38.82966")
    try:
        raw_lat = item.get("latitude") or item.get("Latitude")
        raw_lon = item.get("longitude") or item.get("Longitude")
        raw_depth = item.get("depth") or item.get("Depth")
        raw_mag = item.get("magnitude") or item.get("Magnitude")

        if raw_lat is None or raw_lon is None or raw_depth is None or raw_mag is None:
            logger.warning(
                "Skipping AFAD event %s missing coordinates or magnitude",
                source_event_id,
            )
            return None

        latitude = float(str(raw_lat).strip())
        longitude = float(str(raw_lon).strip())
        depth_km = float(str(raw_depth).strip())
        magnitude = float(str(raw_mag).strip())
    except (ValueError, TypeError) as exc:
        logger.warning(
            "Skipping AFAD event %s with unparseable numeric values: %s",
            source_event_id,
            exc,
        )
        return None

    # Magnitude scale type (e.g. MW, ML, MD)
    raw_type = item.get("type") or item.get("Type") or "UNKNOWN"
    magnitude_type = str(raw_type).strip().upper()

    # Descriptive location and administrative names
    location_name = item.get("location")
    if location_name:
        location_name = str(location_name).strip() or None

    country = item.get("country")
    if country:
        country = str(country).strip() or None

    province = item.get("province")
    if province:
        province = str(province).strip() or None

    district = item.get("district")
    if district:
        district = str(district).strip() or None

    neighborhood = item.get("neighborhood")
    if neighborhood:
        neighborhood = str(neighborhood).strip() or None

    # Upstream revision tracking
    is_updated = bool(item.get("isEventUpdate", False))
    # Note: AFAD does not document whether lastUpdateDate represents UTC or TSİ.
    # To prevent inventing a false timezone, the raw value is preserved inside
    # source_properties, and normalized last_update_at is left as None.
    last_update_at = None

    try:
        return EarthquakeEventCreate(
            source="AFAD",
            source_event_id=source_event_id,
            occurred_at=occurred_at,
            depth_km=depth_km,
            magnitude=magnitude,
            magnitude_type=magnitude_type,
            location_name=location_name,
            country=country,
            province=province,
            district=district,
            neighborhood=neighborhood,
            latitude=latitude,
            longitude=longitude,
            is_updated=is_updated,
            last_update_at=last_update_at,
            source_properties=dict(item),
        )
    except Exception as exc:
        logger.warning(
            "Validation failed for AFAD event %s: %s",
            source_event_id,
            exc,
        )
        return None


def parse_afad_event_list(
    items: list[dict[str, Any]],
) -> tuple[list[EarthquakeEventCreate], int, int]:
    """Parse a list of AFAD JSON events into valid EarthquakeEventCreate records.

    Returns:
        (valid_records, skipped_count, failed_count)
    """
    valid_records: list[EarthquakeEventCreate] = []
    skipped = 0
    failed = 0

    for item in items:
        record = parse_afad_event(item)
        if record is not None:
            valid_records.append(record)
        else:
            failed += 1

    return valid_records, skipped, failed
