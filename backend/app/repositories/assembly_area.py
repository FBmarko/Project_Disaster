"""Repository for AssemblyAreaDataset and AssemblyArea persistence."""

import uuid
from typing import Any

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.integrations.osm.osm_reader import ParsedAssemblyPoint
from app.models.assembly_area import AssemblyArea
from app.models.assembly_area_dataset import AssemblyAreaDataset


class AssemblyAreaRepository:
    """Data access repository for emergency assembly areas and provenance datasets."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_dataset_by_natural_key(
        self, source: str, snapshot_sha256: str
    ) -> AssemblyAreaDataset | None:
        """Fetch an assembly area dataset by source and snapshot checksum."""
        stmt = select(AssemblyAreaDataset).where(
            AssemblyAreaDataset.source == source,
            AssemblyAreaDataset.snapshot_sha256 == snapshot_sha256,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_or_create_dataset(
        self, payload: dict[str, Any]
    ) -> tuple[AssemblyAreaDataset, bool]:
        """Fetch an existing dataset by natural key or insert a new one.

        If an existing dataset is found, validates that immutable provenance fields
        match the incoming payload to detect provenance drift.

        Returns:
            tuple of (dataset, was_created).
        """
        source = payload["source"]
        snapshot_sha256 = payload["snapshot_sha256"]

        existing = self.get_dataset_by_natural_key(source, snapshot_sha256)
        if existing is not None:
            # Check for provenance drift
            fields_to_check = [
                "provider",
                "source_classification",
                "license",
                "attribution",
                "source_reference",
                "snapshot_size_bytes",
                "source_endpoint",
                "extraction_query",
            ]
            for field in fields_to_check:
                val_existing = getattr(existing, field)
                val_incoming = payload.get(field)
                if val_existing != val_incoming:
                    raise ValueError(
                        f"Dataset provenance drift detected for field '{field}': "
                        f"existing='{val_existing}' vs incoming='{val_incoming}'."
                    )
            return existing, False

        dataset = AssemblyAreaDataset(**payload)
        self.session.add(dataset)
        self.session.flush()
        return dataset, True

    def count_areas_for_dataset(self, dataset_id: uuid.UUID) -> int:
        """Return total count of assembly areas for a given dataset."""
        stmt = select(func.count(AssemblyArea.id)).where(
            AssemblyArea.dataset_id == dataset_id
        )
        return self.session.execute(stmt).scalar_one()

    def get_existing_features_map(
        self, dataset_id: uuid.UUID
    ) -> dict[str, dict[str, Any]]:
        """Retrieve existing features map for idempotency and drift verification."""
        stmt = select(
            AssemblyArea.source_feature_id,
            AssemblyArea.name,
            AssemblyArea.ref,
            AssemblyArea.operator,
            AssemblyArea.source_properties,
            func.ST_AsEWKT(AssemblyArea.geometry).label("ewkt"),
        ).where(AssemblyArea.dataset_id == dataset_id)

        rows = self.session.execute(stmt).all()
        result: dict[str, dict[str, Any]] = {}
        for r in rows:
            result[r.source_feature_id] = {
                "name": r.name,
                "ref": r.ref,
                "operator": r.operator,
                "source_properties": r.source_properties,
                "ewkt": r.ewkt,
            }
        return result

    def insert_areas_batch(
        self,
        dataset_id: uuid.UUID,
        batch: list[ParsedAssemblyPoint],
    ) -> int:
        """Insert a batch of parsed assembly points using GeoAlchemy2 WKTElement."""
        if not batch:
            return 0

        areas_to_insert = [
            AssemblyArea(
                dataset_id=dataset_id,
                source_feature_id=item.source_feature_id,
                name=item.name,
                ref=item.ref,
                operator=item.operator,
                geometry=WKTElement(item.wkt_geometry, srid=4326),
                source_properties=item.source_properties,
            )
            for item in batch
        ]
        self.session.add_all(areas_to_insert)
        self.session.flush()
        return len(areas_to_insert)

    def validate_polygons_valid_and_simple(
        self, dataset_id: uuid.UUID
    ) -> tuple[int, int, int]:
        """Validate that all stored polygon ways are valid and simple in PostGIS.

        Returns:
            tuple of (total_polygons, valid_count, simple_count).
        """
        sql = text("""
            SELECT
                count(*) AS total,
                count(*) FILTER (WHERE ST_IsValid(geometry)) AS valid_count,
                count(*) FILTER (WHERE ST_IsSimple(geometry)) AS simple_count
            FROM assembly_areas
            WHERE dataset_id = :dataset_id
              AND ST_GeometryType(geometry) = 'ST_Polygon'
        """)
        row = self.session.execute(sql, {"dataset_id": dataset_id}).mappings().one()
        total = row["total"] or 0
        valid = row["valid_count"] or 0
        simple = row["simple_count"] or 0

        if total > 0 and (valid != total or simple != total):
            raise ValueError(
                f"PostGIS polygon validation failed for dataset {dataset_id}: "
                f"total={total}, valid={valid}, simple={simple}."
            )

        return total, valid, simple

    def check_spatial_equality(
        self, dataset_id: uuid.UUID, source_feature_id: str, incoming_wkt: str
    ) -> bool:
        """Verify spatial equality between stored geometry and incoming geometry."""
        sql = text("""
            SELECT ST_Equals(geometry, ST_GeomFromText(:wkt, 4326)) AS is_equal
            FROM assembly_areas
            WHERE dataset_id = :dataset_id AND source_feature_id = :feature_id
        """)
        result = self.session.execute(
            sql,
            {
                "dataset_id": dataset_id,
                "feature_id": source_feature_id,
                "wkt": incoming_wkt,
            },
        ).scalar()
        return bool(result)
