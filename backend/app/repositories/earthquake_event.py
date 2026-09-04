import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select, text
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
        """Fetch a single earthquake event entity by its internal UUID."""
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

    def get_by_id_with_geojson(self, event_id: uuid.UUID) -> dict[str, Any] | None:
        """Fetch a single earthquake event with PostGIS GeoJSON geometry."""
        query = text("""
            SELECT
                e.id, e.source, e.source_event_id, e.occurred_at, e.depth_km,
                e.magnitude, e.magnitude_type, e.location_name, e.country,
                e.province, e.district, e.neighborhood,
                ST_AsGeoJSON(e.geometry) as geojson
            FROM earthquake_events e
            WHERE e.id = :event_id;
        """)
        row = self.session.execute(query, {"event_id": event_id}).mappings().first()
        return dict(row) if row else None

    def list_events(
        self,
        min_magnitude: float | None = None,
        max_magnitude: float | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        magnitude_type: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Query earthquake events with spatial, temporal, and magnitude filters."""
        clauses = ["1=1"]
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if min_magnitude is not None:
            clauses.append("e.magnitude >= :min_mag")
            params["min_mag"] = min_magnitude
        if max_magnitude is not None:
            clauses.append("e.magnitude <= :max_mag")
            params["max_mag"] = max_magnitude
        if start_time is not None:
            clauses.append("e.occurred_at >= :start_time")
            params["start_time"] = start_time
        if end_time is not None:
            clauses.append("e.occurred_at <= :end_time")
            params["end_time"] = end_time
        if magnitude_type is not None:
            clauses.append("e.magnitude_type = :mag_type")
            params["mag_type"] = magnitude_type.upper()
        if bbox is not None:
            min_lon, min_lat, max_lon, max_lat = bbox
            clauses.append(
                "ST_Intersects(e.geometry, "
                "ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326))"
            )
            params.update(
                {
                    "min_lon": min_lon,
                    "min_lat": min_lat,
                    "max_lon": max_lon,
                    "max_lat": max_lat,
                }
            )

        where_clause = " AND ".join(clauses)
        query = text(f"""
            SELECT
                e.id, e.source, e.source_event_id, e.occurred_at, e.depth_km,
                e.magnitude, e.magnitude_type, e.location_name, e.country,
                e.province, e.district, e.neighborhood,
                ST_AsGeoJSON(e.geometry) as geojson
            FROM earthquake_events e
            WHERE {where_clause}
            ORDER BY e.occurred_at DESC
            LIMIT :limit OFFSET :offset;
        """)
        rows = self.session.execute(query, params).mappings().fetchall()
        return [dict(r) for r in rows]

    def list_recent_major(
        self,
        since: datetime,
        min_magnitude: float = 5.0,
        max_distance_km: float | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List recent major earthquakes, optionally near mapped faults."""
        if max_distance_km is None:
            query = text("""
                SELECT
                    e.id, e.source, e.source_event_id, e.occurred_at, e.depth_km,
                    e.magnitude, e.magnitude_type, e.location_name, e.country,
                    e.province, e.district, e.neighborhood,
                    ST_AsGeoJSON(e.geometry) as geojson,
                    NULL as nearest_fault_id,
                    NULL as nearest_fault_source_feature_id,
                    NULL as distance_to_fault_km
                FROM earthquake_events e
                WHERE e.magnitude >= :min_mag
                  AND e.occurred_at >= :since
                ORDER BY e.occurred_at DESC
                LIMIT :limit OFFSET :offset;
            """)
            params = {
                "min_mag": min_magnitude,
                "since": since,
                "limit": limit,
                "offset": offset,
            }
            rows = self.session.execute(query, params).mappings().fetchall()
            return [dict(r) for r in rows]

        # When max_distance_km is supplied: index-assisted LATERAL join
        radius_meters = max_distance_km * 1000.0
        query = text("""
            SELECT
                e.id, e.source, e.source_event_id, e.occurred_at, e.depth_km,
                e.magnitude, e.magnitude_type, e.location_name, e.country,
                e.province, e.district, e.neighborhood,
                ST_AsGeoJSON(e.geometry) as geojson,
                nf.fault_id as nearest_fault_id,
                nf.source_feature_id as nearest_fault_source_feature_id,
                nf.dist_meters / 1000.0 as distance_to_fault_km
            FROM earthquake_events e
            CROSS JOIN LATERAL (
                SELECT
                    f.id as fault_id,
                    f.source_feature_id,
                    ST_Distance(
                        f.geometry::geography, e.geometry::geography
                    ) as dist_meters
                FROM fault_segments f
                WHERE f.geometry && ST_Envelope(
                    ST_Buffer(e.geometry::geography, :radius_meters)::geometry
                )
                AND ST_DWithin(
                    f.geometry::geography,
                    e.geometry::geography,
                    :radius_meters
                )
                ORDER BY dist_meters ASC
                LIMIT 1
            ) nf
            WHERE e.magnitude >= :min_mag
              AND e.occurred_at >= :since
            ORDER BY e.occurred_at DESC
            LIMIT :limit OFFSET :offset;
        """)
        params = {
            "radius_meters": radius_meters,
            "min_mag": min_magnitude,
            "since": since,
            "limit": limit,
            "offset": offset,
        }
        rows = self.session.execute(query, params).mappings().fetchall()
        return [dict(r) for r in rows]

    def list_near_fault(
        self,
        fault_id: uuid.UUID,
        max_distance_km: float,
        min_magnitude: float = 5.0,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "recent",
    ) -> list[dict[str, Any]]:
        """List earthquakes within max_distance_km of a specific mapped fault."""
        radius_meters = max_distance_km * 1000.0

        clauses = [
            (
                "e.geometry && ST_Envelope("
                "ST_Buffer(f.geometry::geography, :radius_meters)::geometry)"
            ),
            "ST_DWithin(e.geometry::geography, f.geometry::geography, :radius_meters)",
            "e.magnitude >= :min_mag",
        ]
        params: dict[str, Any] = {
            "fault_id": fault_id,
            "radius_meters": radius_meters,
            "min_mag": min_magnitude,
            "limit": limit,
            "offset": offset,
        }

        if start_time is not None:
            clauses.append("e.occurred_at >= :start_time")
            params["start_time"] = start_time
        if end_time is not None:
            clauses.append("e.occurred_at <= :end_time")
            params["end_time"] = end_time

        where_clause = " AND ".join(clauses)
        order_clause = (
            "distance_to_fault_km ASC, e.occurred_at DESC"
            if order_by == "distance"
            else "e.occurred_at DESC"
        )

        query = text(f"""
            SELECT
                e.id, e.source, e.source_event_id, e.occurred_at, e.depth_km,
                e.magnitude, e.magnitude_type, e.location_name, e.country,
                e.province, e.district, e.neighborhood,
                ST_AsGeoJSON(e.geometry) as geojson,
                ST_Distance(
                    e.geometry::geography, f.geometry::geography
                ) / 1000.0 as distance_to_fault_km
            FROM earthquake_events e
            JOIN fault_segments f ON f.id = :fault_id
            WHERE {where_clause}
            ORDER BY {order_clause}
            LIMIT :limit OFFSET :offset;
        """)
        rows = self.session.execute(query, params).mappings().fetchall()
        return [dict(r) for r in rows]

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
