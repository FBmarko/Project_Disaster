import uuid
from collections.abc import Sequence

from geoalchemy2 import Geography, Geometry
from geoalchemy2.elements import WKTElement
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from app.models.fault_segment import FaultSegment
from app.schemas.fault_segment import FaultSegmentCreate


def coords_to_wkt_element(coords: list[list[list[float]]]) -> WKTElement:
    """Serialize MultiLineString coordinates into GeoAlchemy2 WKTElement (EPSG:4326)."""
    lines_wkt = []
    for line in coords:
        pts_wkt = ", ".join(f"{pt[0]} {pt[1]}" for pt in line)
        lines_wkt.append(f"({pts_wkt})")
    wkt = f"MULTILINESTRING({', '.join(lines_wkt)})"
    return WKTElement(wkt, srid=4326)


class FaultSegmentRepository:
    """Repository handling database operations for FaultSegment entities."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, segment_id: uuid.UUID) -> FaultSegment | None:
        """Fetch a single fault segment entity by its primary key UUID."""
        return self.session.get(FaultSegment, segment_id)

    def get_by_id_with_geojson(
        self, segment_id: uuid.UUID
    ) -> tuple[FaultSegment, str] | None:
        """Fetch a fault segment and its PostGIS GeoJSON geometry string by UUID."""
        stmt = select(
            FaultSegment,
            func.ST_AsGeoJSON(FaultSegment.geometry).label("geojson"),
        ).where(FaultSegment.id == segment_id)
        row = self.session.execute(stmt).first()
        if not row:
            return None
        return row[0], row[1]

    def get_by_source_feature_id(
        self, source: str, source_feature_id: str
    ) -> FaultSegment | None:
        """Fetch a fault segment by its source catalog identity."""
        stmt = select(FaultSegment).where(
            FaultSegment.source == source,
            FaultSegment.source_feature_id == source_feature_id,
        )
        return self.session.scalar(stmt)

    def count(self, source: str | None = None) -> int:
        """Count total persisted fault segment records."""
        stmt = select(func.count(FaultSegment.id))
        if source:
            stmt = stmt.where(FaultSegment.source == source)
        return self.session.scalar(stmt) or 0

    def list_faults(
        self,
        bbox: tuple[float, float, float, float] | None = None,
        fault_type: str | None = None,
        limit: int = 1000,
    ) -> list[tuple[FaultSegment, str]]:
        """Query fault segments with optional bounding box and fault type filters.

        Uses the PostGIS GiST index via ST_Intersects(geometry, ST_MakeEnvelope(...)).

        Returns:
            List of tuples: (FaultSegment, geojson_geometry_string)
        """
        stmt = select(
            FaultSegment,
            func.ST_AsGeoJSON(FaultSegment.geometry).label("geojson"),
        )

        if bbox is not None:
            min_lon, min_lat, max_lon, max_lat = bbox
            envelope = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
            stmt = stmt.where(func.ST_Intersects(FaultSegment.geometry, envelope))

        if fault_type is not None:
            stmt = stmt.where(FaultSegment.fault_type == fault_type)

        stmt = stmt.order_by(FaultSegment.source_feature_id.asc()).limit(limit)
        rows = self.session.execute(stmt).all()
        return [(r[0], r[1]) for r in rows]

    def find_nearby(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
        limit: int = 20,
    ) -> list[tuple[FaultSegment, str, float]]:
        """Find fault segments within a geodesic radius from a WGS84 point.

        Uses a two-stage spatial filter:
        1. Coarse index-assisted envelope filter via GiST index on geometry (&&).
        2. Exact geodesic distance filter using geography ST_DWithin and ST_Distance.

        Returns:
            List of tuples: (FaultSegment, geojson_geometry_string, distance_km)
        """
        query_point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
        point_geog = cast(query_point, Geography)
        geom_geog = cast(FaultSegment.geometry, Geography)

        radius_meters = radius_km * 1000.0

        # Stage 1: Envelope of geodesic buffer for index-assisted GiST bounding
        envelope_geom = func.ST_Envelope(
            cast(func.ST_Buffer(point_geog, radius_meters), Geometry)
        )

        # Stage 2: Exact geodesic distance calculation
        distance_km = (func.ST_Distance(geom_geog, point_geog) / 1000.0).label(
            "distance_km"
        )

        stmt = (
            select(
                FaultSegment,
                func.ST_AsGeoJSON(FaultSegment.geometry).label("geojson"),
                distance_km,
            )
            .where(
                FaultSegment.geometry.op("&&")(envelope_geom),
                func.ST_DWithin(geom_geog, point_geog, radius_meters),
            )
            .order_by(distance_km.asc())
            .limit(limit)
        )

        rows = self.session.execute(stmt).all()
        return [(r[0], r[1], float(r[2])) for r in rows]

    def upsert_batch(
        self,
        records: Sequence[FaultSegmentCreate],
    ) -> tuple[int, int, int]:
        """Upsert a batch of FaultSegment records idempotently.

        Returns:
            (inserted_count, updated_count, unchanged_count)
        """
        if not records:
            return 0, 0, 0

        source = records[0].source
        source_ids = [r.source_feature_id for r in records]

        stmt = select(FaultSegment).where(
            FaultSegment.source == source,
            FaultSegment.source_feature_id.in_(source_ids),
        )
        existing_records = {
            f.source_feature_id: f for f in self.session.scalars(stmt).all()
        }

        inserted = 0
        updated = 0
        unchanged = 0

        for record in records:
            geom_element = coords_to_wkt_element(record.coordinates)
            existing = existing_records.get(record.source_feature_id)

            if existing is None:
                new_segment = FaultSegment(
                    source=record.source,
                    source_feature_id=record.source_feature_id,
                    name=record.name,
                    segment_name=record.segment_name,
                    fault_type=record.fault_type,
                    activity_status=record.activity_status,
                    geometry=geom_element,
                    source_reference=record.source_reference,
                    source_properties=record.source_properties,
                )
                self.session.add(new_segment)
                inserted += 1
            else:
                has_changes = (
                    existing.name != record.name
                    or existing.segment_name != record.segment_name
                    or existing.fault_type != record.fault_type
                    or existing.activity_status != record.activity_status
                    or existing.source_reference != record.source_reference
                    or existing.source_properties != record.source_properties
                )

                if has_changes:
                    existing.name = record.name
                    existing.segment_name = record.segment_name
                    existing.fault_type = record.fault_type
                    existing.activity_status = record.activity_status
                    existing.geometry = geom_element
                    existing.source_reference = record.source_reference
                    existing.source_properties = record.source_properties
                    updated += 1
                else:
                    unchanged += 1

        return inserted, updated, unchanged
