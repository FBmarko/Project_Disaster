import uuid
from collections.abc import Sequence

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
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
        return self.session.get(FaultSegment, segment_id)

    def get_by_source_feature_id(
        self, source: str, source_feature_id: str
    ) -> FaultSegment | None:
        stmt = select(FaultSegment).where(
            FaultSegment.source == source,
            FaultSegment.source_feature_id == source_feature_id,
        )
        return self.session.scalar(stmt)

    def count(self, source: str | None = None) -> int:
        stmt = select(func.count(FaultSegment.id))
        if source:
            stmt = stmt.where(FaultSegment.source == source)
        return self.session.scalar(stmt) or 0

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

        # Fetch existing records in this batch
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
                # Insert new entity
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
                # Check if mutable properties changed
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
