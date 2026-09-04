import uuid
from typing import Any

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, insert, select, text
from sqlalchemy.orm import Session

from app.integrations.gem.hazard_constants import (
    GEM_HAZARD_METRIC,
    GEM_RETURN_PERIOD_YEARS,
    GEM_SOURCE_NAME,
    GEM_SOURCE_VERSION,
    TURKEY_CONTEXT_SCOPE,
)
from app.integrations.gem.hazard_reader import GemHazardRecord
from app.models.earthquake_hazard_point import EarthquakeHazardPoint
from app.models.hazard_dataset import HazardDataset


class EarthquakeHazardRepository:
    """Repository handling database operations for seismic hazard data."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_or_create_dataset(
        self, dataset_data: dict[str, Any]
    ) -> tuple[HazardDataset, bool]:
        """Fetch or create a HazardDataset metadata record by natural unique key.

        Returns:
            (HazardDataset, was_created)
        """
        stmt = select(HazardDataset).where(
            HazardDataset.source == dataset_data["source"],
            HazardDataset.source_version == dataset_data["source_version"],
            HazardDataset.hazard_metric == dataset_data["hazard_metric"],
            HazardDataset.return_period_years == dataset_data["return_period_years"],
            HazardDataset.ingest_scope == dataset_data["ingest_scope"],
        )
        existing = self.session.scalar(stmt)
        if existing is not None:
            # Verify ALL immutable provenance metadata fields
            immutable_fields = [
                "source",
                "source_version",
                "model_name",
                "hazard_metric",
                "unit",
                "return_period_years",
                "time_horizon_years",
                "reference_ground",
                "version_doi",
                "concept_doi",
                "license",
                "attribution",
                "source_artifact",
                "source_artifact_size_bytes",
                "source_checksum_algorithm",
                "source_checksum_value",
                "ingest_scope",
            ]
            for field in immutable_fields:
                stored_val = getattr(existing, field)
                incoming_val = dataset_data.get(field)
                if stored_val != incoming_val:
                    err = (
                        f"Provenance conflict for {field} in dataset "
                        f"{existing.source} v{existing.source_version}: "
                        f"stored='{stored_val}', incoming='{incoming_val}'"
                    )
                    raise ValueError(err)

            # Strict float comparisons with tight tolerance (1e-9)
            float_fields = [
                "exceedance_probability",
                "reference_vs30_mps",
                "scope_min_longitude",
                "scope_min_latitude",
                "scope_max_longitude",
                "scope_max_latitude",
            ]
            for f_field in float_fields:
                stored_flt = getattr(existing, f_field)
                incoming_flt = dataset_data.get(f_field)
                if (
                    stored_flt is not None
                    and incoming_flt is not None
                    and abs(stored_flt - incoming_flt) > 1e-9
                ):
                    err = (
                        f"Provenance float conflict for {f_field} in dataset "
                        f"{existing.source} v{existing.source_version}: "
                        f"stored={stored_flt}, incoming={incoming_flt}"
                    )
                    raise ValueError(err)

            return existing, False

        dataset = HazardDataset(**dataset_data)
        self.session.add(dataset)
        self.session.flush()
        return dataset, True

    def get_active_gem_dataset(self) -> HazardDataset | None:
        """Fetch the active GEM GSHM v2026.1 dataset for the Türkiye context."""
        stmt = select(HazardDataset).where(
            HazardDataset.source == GEM_SOURCE_NAME,
            HazardDataset.source_version == GEM_SOURCE_VERSION,
            HazardDataset.hazard_metric == GEM_HAZARD_METRIC,
            HazardDataset.return_period_years == GEM_RETURN_PERIOD_YEARS,
            HazardDataset.ingest_scope == TURKEY_CONTEXT_SCOPE,
        )
        return self.session.scalar(stmt)

    def get_dataset_by_id(self, dataset_id: uuid.UUID) -> HazardDataset | None:
        """Fetch dataset metadata by UUID."""
        return self.session.get(HazardDataset, dataset_id)

    def count_points_for_dataset(self, dataset_id: uuid.UUID) -> int:
        """Count total persisted hazard points for a given dataset."""
        stmt = select(func.count(EarthquakeHazardPoint.id)).where(
            EarthquakeHazardPoint.dataset_id == dataset_id
        )
        return self.session.scalar(stmt) or 0

    def get_existing_points_map(
        self, dataset_id: uuid.UUID
    ) -> dict[tuple[float, float], tuple[float, int | None]]:
        """Fetch existing (lon, lat) -> (pga_g, source_fid) map for a dataset."""
        stmt = select(
            EarthquakeHazardPoint.longitude,
            EarthquakeHazardPoint.latitude,
            EarthquakeHazardPoint.pga_g,
            EarthquakeHazardPoint.source_record_id,
        ).where(EarthquakeHazardPoint.dataset_id == dataset_id)

        rows = self.session.execute(stmt).all()
        return {
            (round(lon, 7), round(lat, 7)): (float(pga), src_id)
            for lon, lat, pga, src_id in rows
        }

    def insert_points_batch(
        self, dataset_id: uuid.UUID, records: list[GemHazardRecord]
    ) -> int:
        """Insert a batch of EarthquakeHazardPoint records using SQLAlchemy Core."""
        if not records:
            return 0

        payload = [
            {
                "id": uuid.uuid4(),
                "dataset_id": dataset_id,
                "source_record_id": rec.fid,
                "longitude": rec.longitude,
                "latitude": rec.latitude,
                "pga_g": rec.pga_g,
                "geometry": WKTElement(
                    f"POINT({rec.longitude} {rec.latitude})", srid=4326
                ),
            }
            for rec in records
        ]

        stmt = insert(EarthquakeHazardPoint).values(payload)
        self.session.execute(stmt)
        return len(payload)

    def find_nearest_hazard_point(
        self,
        dataset_id: uuid.UUID,
        longitude: float,
        latitude: float,
        candidate_count: int = 32,
    ) -> dict[str, Any] | None:
        """Find nearest node using two-stage GiST KNN + exact geodesic distance."""
        sql = text("""
            WITH candidates AS (
                SELECT id, source_record_id, longitude, latitude, pga_g, geometry
                FROM earthquake_hazard_points
                WHERE dataset_id = :dataset_id
                ORDER BY geometry <-> ST_SetSRID(
                    ST_MakePoint(:longitude, :latitude), 4326
                )
                LIMIT :candidate_count
            )
            SELECT id, source_record_id, longitude, latitude, pga_g,
                   ST_Distance(
                       geometry::geography,
                       ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography
                   ) / 1000.0 AS distance_km
            FROM candidates
            ORDER BY distance_km, id
            LIMIT 1;
        """)
        row = (
            self.session.execute(
                sql,
                {
                    "dataset_id": dataset_id,
                    "longitude": longitude,
                    "latitude": latitude,
                    "candidate_count": candidate_count,
                },
            )
            .mappings()
            .first()
        )

        if row is None:
            return None
        return dict(row)

    def list_hazard_points_in_bbox(
        self,
        dataset_id: uuid.UUID,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        limit: int = 1000,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], bool]:
        """List hazard points within a bbox using PostGIS GiST envelope filtering.

        Fetches limit + 1 records to determine has_more without a count query.
        """
        fetch_limit = limit + 1
        sql = text("""
            SELECT id, source_record_id, longitude, latitude, pga_g
            FROM earthquake_hazard_points
            WHERE dataset_id = :dataset_id
              AND geometry && ST_MakeEnvelope(
                  :min_lon, :min_lat, :max_lon, :max_lat, 4326
              )
            ORDER BY latitude, longitude
            LIMIT :fetch_limit OFFSET :offset;
        """)
        rows = (
            self.session.execute(
                sql,
                {
                    "dataset_id": dataset_id,
                    "min_lon": min_lon,
                    "min_lat": min_lat,
                    "max_lon": max_lon,
                    "max_lat": max_lat,
                    "fetch_limit": fetch_limit,
                    "offset": offset,
                },
            )
            .mappings()
            .all()
        )

        has_more = len(rows) > limit
        result_rows = [dict(r) for r in rows[:limit]]
        return result_rows, has_more
