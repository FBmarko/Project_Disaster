import uuid
from collections.abc import Sequence

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.earthquake_event import EarthquakeEvent
from app.schemas.earthquake_event import EarthquakeEventCreate


def coords_to_point_element(longitude: float, latitude: float) -> WKTElement:
    """Format coordinates into GeoAlchemy2 WKTElement Point (EPSG:4326)."""
    return WKTElement(f"POINT({longitude} {latitude})", srid=4326)


class EarthquakeEventRepository:
    """Repository handling database operations for EarthquakeEvent entities."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, event_id: uuid.UUID) -> EarthquakeEvent | None:
        """Fetch a single earthquake event by its internal UUID."""
        return self.session.get(EarthquakeEvent, event_id)

    def get_by_source_event_id(
        self, source: str, source_event_id: str
    ) -> EarthquakeEvent | None:
        """Fetch an earthquake event by its source identifier."""
        stmt = select(EarthquakeEvent).where(
            EarthquakeEvent.source == source,
            EarthquakeEvent.source_event_id == source_event_id,
        )
        return self.session.scalar(stmt)

    def count(self, source: str | None = None) -> int:
        """Count total persisted earthquake events."""
        stmt = select(func.count(EarthquakeEvent.id))
        if source:
            stmt = stmt.where(EarthquakeEvent.source == source)
        return self.session.scalar(stmt) or 0

    def upsert_batch(
        self,
        records: Sequence[EarthquakeEventCreate],
    ) -> tuple[int, int, int]:
        """Upsert a batch of EarthquakeEvent records idempotently.

        Returns:
            (inserted_count, updated_count, unchanged_count)
        """
        if not records:
            return 0, 0, 0

        source = records[0].source
        source_ids = [r.source_event_id for r in records]

        # Fetch existing records in this batch
        stmt = select(EarthquakeEvent).where(
            EarthquakeEvent.source == source,
            EarthquakeEvent.source_event_id.in_(source_ids),
        )
        existing_records = {
            e.source_event_id: e for e in self.session.scalars(stmt).all()
        }

        inserted = 0
        updated = 0
        unchanged = 0

        for record in records:
            point_elem = coords_to_point_element(record.longitude, record.latitude)
            existing = existing_records.get(record.source_event_id)

            if existing is None:
                new_event = EarthquakeEvent(
                    source=record.source,
                    source_event_id=record.source_event_id,
                    occurred_at=record.occurred_at,
                    depth_km=record.depth_km,
                    magnitude=record.magnitude,
                    magnitude_type=record.magnitude_type,
                    location_name=record.location_name,
                    country=record.country,
                    province=record.province,
                    district=record.district,
                    neighborhood=record.neighborhood,
                    geometry=point_elem,
                    is_updated=record.is_updated,
                    last_update_at=record.last_update_at,
                    source_properties=record.source_properties,
                )
                self.session.add(new_event)
                inserted += 1
            else:
                has_changes = (
                    existing.occurred_at != record.occurred_at
                    or abs(existing.depth_km - record.depth_km) > 1e-4
                    or abs(existing.magnitude - record.magnitude) > 1e-4
                    or existing.magnitude_type != record.magnitude_type
                    or existing.location_name != record.location_name
                    or existing.country != record.country
                    or existing.province != record.province
                    or existing.district != record.district
                    or existing.neighborhood != record.neighborhood
                    or existing.is_updated != record.is_updated
                    or existing.last_update_at != record.last_update_at
                    or existing.source_properties != record.source_properties
                )

                if has_changes:
                    existing.occurred_at = record.occurred_at
                    existing.depth_km = record.depth_km
                    existing.magnitude = record.magnitude
                    existing.magnitude_type = record.magnitude_type
                    existing.location_name = record.location_name
                    existing.country = record.country
                    existing.province = record.province
                    existing.district = record.district
                    existing.neighborhood = record.neighborhood
                    existing.geometry = point_elem
                    existing.is_updated = record.is_updated
                    existing.last_update_at = record.last_update_at
                    existing.source_properties = record.source_properties
                    updated += 1
                else:
                    unchanged += 1

        return inserted, updated, unchanged
