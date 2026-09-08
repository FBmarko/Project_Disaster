"""Deterministic synthetic dataset fixtures for isolated database testing."""

import uuid
from datetime import UTC, datetime, timedelta

from geoalchemy2.elements import WKTElement
from sqlalchemy.orm import Session

from app.integrations.gem.hazard_constants import (
    GEM_ATTRIBUTION,
    GEM_CONCEPT_DOI,
    GEM_HAZARD_METRIC,
    GEM_LICENSE,
    GEM_MODEL_NAME,
    GEM_REFERENCE_GROUND,
    GEM_REFERENCE_VS30_MPS,
    GEM_RETURN_PERIOD_YEARS,
    GEM_SOURCE_NAME,
    GEM_SOURCE_VERSION,
    GEM_TIME_HORIZON_YEARS,
    GEM_UNIT,
    GEM_VERSION_DOI,
    GEM_ZIP_FILENAME,
    GEM_ZIP_MD5,
    GEM_ZIP_SIZE_BYTES,
    TURKEY_CONTEXT_SCOPE,
)
from app.models.assembly_area import AssemblyArea
from app.models.assembly_area_dataset import AssemblyAreaDataset
from app.models.earthquake_event import EarthquakeEvent
from app.models.earthquake_hazard_point import EarthquakeHazardPoint
from app.models.fault_segment import FaultSegment
from app.models.hazard_dataset import HazardDataset

CANONICAL_SAMPLE_FAULT_ID = uuid.UUID("7e4faae8-4da3-43fc-9063-2581b719ceba")
CANONICAL_HAZARD_DATASET_ID = uuid.UUID("2066cc5a-7dc8-40ac-9555-24a3bc67e1ac")
CANONICAL_ASSEMBLY_DATASET_ID = uuid.UUID("d858c496-c4e2-4d08-be02-a6e74b5e6bdb")


def create_sample_faults(session: Session) -> list[FaultSegment]:
    """Create a minimal representative set of fault segments if not already present."""
    existing = session.query(FaultSegment).first()
    if existing is not None:
        return session.query(FaultSegment).limit(10).all()

    faults = [
        FaultSegment(
            id=CANONICAL_SAMPLE_FAULT_ID,
            source="GEM_GAF",
            source_feature_id="GEM_FAULT_001",
            name="North Anatolian Fault - Marmara Segment",
            fault_type="Dextral",
            geometry=(
                "SRID=4326;MULTILINESTRING((28.95 41.00, 28.98 41.01, 29.02 41.02))"
            ),
            source_properties={"name": "NAF Marmara", "slip_rate": 20.0},
        ),
        FaultSegment(
            id=uuid.UUID("7e4faae8-4da3-43fc-9063-2581b719cebb"),
            source="GEM_GAF",
            source_feature_id="GEM_FAULT_002",
            name="North Anatolian Fault - Princes Islands",
            fault_type="Dextral",
            geometry="SRID=4326;MULTILINESTRING((29.05 40.85, 29.15 40.88))",
            source_properties={"name": "NAF Adalar"},
        ),
        FaultSegment(
            id=uuid.UUID("7e4faae8-4da3-43fc-9063-2581b719cebc"),
            source="GEM_GAF",
            source_feature_id="GEM_FAULT_003",
            name="North Anatolian Fault - Ganos",
            fault_type="Dextral",
            geometry="SRID=4326;MULTILINESTRING((28.10 40.80, 28.30 40.85))",
            source_properties={"name": "NAF Ganos"},
        ),
        FaultSegment(
            id=uuid.UUID("7e4faae8-4da3-43fc-9063-2581b719cebd"),
            source="GEM_GAF",
            source_feature_id="GEM_FAULT_004",
            name="East Anatolian Fault - Maras",
            fault_type="Sinistral",
            geometry="SRID=4326;MULTILINESTRING((36.80 37.50, 37.00 37.60))",
            source_properties={"name": "EAF Maras"},
        ),
        FaultSegment(
            id=uuid.UUID("7e4faae8-4da3-43fc-9063-2581b719cebe"),
            source="GEM_GAF",
            source_feature_id="GEM_FAULT_005",
            name="East Anatolian Fault - Pazarcik",
            fault_type="Sinistral",
            geometry="SRID=4326;MULTILINESTRING((37.10 37.65, 37.30 37.80))",
            source_properties={"name": "EAF Pazarcik"},
        ),
        FaultSegment(
            id=uuid.UUID("7e4faae8-4da3-43fc-9063-2581b719cebf"),
            source="GEM_GAF",
            source_feature_id="GEM_FAULT_006",
            name="Western Anatolia Graben Fault",
            fault_type="Normal",
            geometry="SRID=4326;MULTILINESTRING((27.50 38.30, 27.80 38.40))",
            source_properties={"name": "WAGF"},
        ),
        FaultSegment(
            id=uuid.UUID("7e4faae8-4da3-43fc-9063-2581b719cec0"),
            source="GEM_GAF",
            source_feature_id="GEM_FAULT_007",
            name="North Anatolian Fault - Izmit",
            fault_type="Dextral",
            geometry="SRID=4326;MULTILINESTRING((29.90 40.75, 30.00 40.78))",
            source_properties={"name": "NAF Izmit"},
        ),
        FaultSegment(
            id=uuid.UUID("0f2943fd-5947-450b-88e5-ca7e68036d9b"),
            source="GEM_GAF",
            source_feature_id="GEM_FAULT_ZERO",
            name="Zero Result Fault Segment",
            fault_type="Normal",
            geometry=(
                "SRID=4326;MULTILINESTRING((29.586795 40.314221,29.536795 40.290469,"
                "29.486794 40.266716,29.436818 40.242974,29.386841 40.219232))"
            ),
            source_properties={"name": "Zero Result Fault"},
        ),
    ]
    session.add_all(faults)
    session.flush()
    return faults


def create_sample_earthquakes(session: Session) -> list[EarthquakeEvent]:
    """Create a minimal representative set of earthquake events if absent."""
    existing = session.query(EarthquakeEvent).first()
    if existing is not None:
        return session.query(EarthquakeEvent).limit(10).all()

    events = [
        EarthquakeEvent(
            id=uuid.UUID("6a111111-1111-1111-1111-111111111111"),
            source="AFAD",
            source_event_id="AFAD_EV_001",
            occurred_at=datetime(2023, 2, 6, 4, 17, 0, tzinfo=UTC),
            depth_km=10.0,
            magnitude=5.5,
            magnitude_type="MW",
            geometry="SRID=4326;POINT(28.97 41.01)",
            source_properties={"location": "Marmara Sea"},
        ),
        EarthquakeEvent(
            id=uuid.UUID("6a222222-2222-2222-2222-222222222222"),
            source="AFAD",
            source_event_id="AFAD_EV_002",
            occurred_at=datetime(2023, 2, 6, 10, 24, 0, tzinfo=UTC),
            depth_km=12.0,
            magnitude=6.2,
            magnitude_type="MW",
            geometry="SRID=4326;POINT(28.90 40.95)",
            source_properties={"location": "Marmara Sea South"},
        ),
        EarthquakeEvent(
            id=uuid.UUID("6a333333-3333-3333-3333-333333333333"),
            source="AFAD",
            source_event_id="AFAD_EV_003",
            occurred_at=datetime(2018, 5, 10, 12, 0, 0, tzinfo=UTC),
            depth_km=8.0,
            magnitude=4.8,
            magnitude_type="MW",
            geometry="SRID=4326;POINT(29.10 40.85)",
            source_properties={"location": "Adalar"},
        ),
        EarthquakeEvent(
            id=uuid.UUID("6a444444-4444-4444-4444-444444444444"),
            source="AFAD",
            source_event_id="AFAD_EV_004",
            occurred_at=datetime(2022, 1, 1, 0, 0, 0, tzinfo=UTC),
            depth_km=7.0,
            magnitude=5.0,
            magnitude_type="ML",
            geometry="SRID=4326;POINT(29.05 40.80)",
            source_properties={"location": "Cinarcik"},
        ),
        EarthquakeEvent(
            id=uuid.UUID("6a555555-5555-5555-5555-555555555555"),
            source="AFAD",
            source_event_id="AFAD_EV_005",
            occurred_at=datetime(2024, 3, 15, 0, 0, 0, tzinfo=UTC),
            depth_km=15.0,
            magnitude=5.1,
            magnitude_type="MW",
            geometry="SRID=4326;POINT(37.00 37.60)",
            source_properties={"location": "Maras"},
        ),
        EarthquakeEvent(
            id=uuid.UUID("6a666666-6666-6666-6666-666666666666"),
            source="AFAD",
            source_event_id="AFAD_EV_006",
            occurred_at=datetime(2025, 6, 1, 0, 0, 0, tzinfo=UTC),
            depth_km=5.0,
            magnitude=4.6,
            magnitude_type="ML",
            geometry="SRID=4326;POINT(27.60 38.35)",
            source_properties={"location": "Manisa"},
        ),
    ]
    session.add_all(events)
    session.flush()
    return events


def create_sample_hazard_dataset(
    session: Session,
) -> tuple[HazardDataset, list[EarthquakeHazardPoint]]:
    """Create a minimal representative GEM GSHM hazard dataset if absent."""
    existing = session.query(HazardDataset).first()
    if existing is not None:
        points = (
            session.query(EarthquakeHazardPoint)
            .filter(EarthquakeHazardPoint.dataset_id == existing.id)
            .limit(50)
            .all()
        )
        return existing, points

    dataset = HazardDataset(
        id=CANONICAL_HAZARD_DATASET_ID,
        source=GEM_SOURCE_NAME,
        source_version=GEM_SOURCE_VERSION,
        model_name=GEM_MODEL_NAME,
        hazard_metric=GEM_HAZARD_METRIC,
        unit=GEM_UNIT,
        return_period_years=GEM_RETURN_PERIOD_YEARS,
        exceedance_probability=0.10,
        time_horizon_years=GEM_TIME_HORIZON_YEARS,
        reference_vs30_mps=GEM_REFERENCE_VS30_MPS,
        reference_ground=GEM_REFERENCE_GROUND,
        version_doi=GEM_VERSION_DOI,
        concept_doi=GEM_CONCEPT_DOI,
        license=GEM_LICENSE,
        attribution=GEM_ATTRIBUTION,
        source_artifact=GEM_ZIP_FILENAME,
        source_artifact_size_bytes=GEM_ZIP_SIZE_BYTES,
        source_checksum_algorithm="md5",
        source_checksum_value=GEM_ZIP_MD5,
        ingest_scope=TURKEY_CONTEXT_SCOPE,
        scope_min_longitude=24.0,
        scope_min_latitude=34.0,
        scope_max_longitude=46.0,
        scope_max_latitude=44.0,
    )
    session.add(dataset)
    session.flush()

    raw_points: list[tuple[int, float, float, float]] = [
        (1, 32.85, 39.93, 0.20),
        (2, 29.00, 41.00, 0.35),
        (3, 27.14, 38.42, 0.40),
        (4, 43.38, 38.50, 0.38),
        (5, 24.05, 34.05, 0.10),
        (6, 45.95, 43.95, 0.15),
        (7, 26.0, 37.0, 0.22),
        (8, 28.5, 41.2, 0.31),
        (9, 30.0, 36.5, 0.18),
        (10, 32.8, 39.9, 0.21),
        (11, 35.2, 42.0, 0.25),
        (12, 38.0, 38.0, 0.33),
        (13, 40.5, 39.5, 0.36),
        (14, 43.0, 37.5, 0.29),
        (15, 44.8, 41.0, 0.27),
        (16, 24.5, 34.5, 0.12),
    ]

    seen_coords = {(lon, lat) for _, lon, lat, _ in raw_points}
    rec_id = 100
    for lon_i in [28.7, 28.8, 28.9, 29.0, 29.1, 29.2, 29.3]:
        for lat_j in [40.85, 40.9, 40.95, 41.0, 41.05, 41.1, 41.15]:
            coord = (round(lon_i, 4), round(lat_j, 4))
            if coord not in seen_coords:
                seen_coords.add(coord)
                raw_points.append(
                    (
                        rec_id,
                        lon_i,
                        lat_j,
                        round(0.15 + (lon_i - 28.8) * 0.1 + (lat_j - 40.9) * 0.1, 4),
                    )
                )
                rec_id += 1

    hazard_points: list[EarthquakeHazardPoint] = []
    for s_id, lon, lat, pga in raw_points:
        pt = EarthquakeHazardPoint(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            source_record_id=s_id,
            longitude=lon,
            latitude=lat,
            pga_g=pga,
            geometry=WKTElement(f"POINT({lon} {lat})", srid=4326),
        )
        hazard_points.append(pt)

    session.add_all(hazard_points)
    session.flush()
    return dataset, hazard_points


def create_sample_assembly_dataset(
    session: Session,
) -> tuple[AssemblyAreaDataset, list[AssemblyArea]]:
    """Create a minimal representative OSM assembly area dataset if absent."""
    existing = session.query(AssemblyAreaDataset).first()
    if existing is not None:
        areas = (
            session.query(AssemblyArea)
            .filter(AssemblyArea.dataset_id == existing.id)
            .limit(20)
            .all()
        )
        return existing, areas

    now = datetime.now(UTC)
    dataset = AssemblyAreaDataset(
        id=CANONICAL_ASSEMBLY_DATASET_ID,
        source="OpenStreetMap",
        provider="OpenStreetMap contributors",
        source_classification="community_open_data",
        license="ODbL 1.0",
        attribution="© OpenStreetMap contributors",
        source_reference="https://www.openstreetmap.org/copyright",
        snapshot_retrieved_at=now - timedelta(days=1),
        source_data_timestamp=now - timedelta(days=2),
        snapshot_sha256="23b86cfc29f30a47ca49c4e0037c4bcf914066870d06d234d53b64be2a46c340",
        snapshot_size_bytes=1000,
        source_endpoint="https://overpass-api.de/api/interpreter",
        extraction_query="test",
        source_metadata={},
    )
    session.add(dataset)
    session.flush()

    areas: list[AssemblyArea] = [
        AssemblyArea(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            source_feature_id="node/1000000001",
            name="Kadıköy Rıhtım Toplanma Alanı",
            ref="KDK-01",
            operator="Kadıköy Belediyesi",
            geometry=WKTElement("POINT(29.03 40.99)", srid=4326),
            source_properties={"emergency": "assembly_point"},
        ),
        AssemblyArea(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            source_feature_id="node/1000000002",
            name="Moda Parkı Toplanma Alanı",
            ref="KDK-02",
            operator="Kadıköy Belediyesi",
            geometry=WKTElement("POINT(29.035 40.992)", srid=4326),
            source_properties={"emergency": "assembly_point"},
        ),
        AssemblyArea(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            source_feature_id="node/1000000003",
            name="Sancaktepe Meydanı Toplanma Alanı",
            ref="SNC-01",
            operator="Sancaktepe Belediyesi",
            geometry=WKTElement("POINT(29.25 41.03)", srid=4326),
            source_properties={"emergency": "assembly_point"},
        ),
        AssemblyArea(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            source_feature_id="node/1000000004",
            name="Fatih Parkı Toplanma Alanı",
            ref="FTH-01",
            operator="Fatih Belediyesi",
            geometry=WKTElement("POINT(28.97 41.01)", srid=4326),
            source_properties={"emergency": "assembly_point"},
        ),
        AssemblyArea(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            source_feature_id="node/1000000005",
            name="Bakırköy Sahil Alanı",
            ref="BKR-01",
            operator="Bakırköy Belediyesi",
            geometry=WKTElement("POINT(28.87 40.97)", srid=4326),
            source_properties={"emergency": "assembly_point"},
        ),
        AssemblyArea(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            source_feature_id="node/1000000006",
            name="Üsküdar Meydanı Toplanma Alanı",
            ref="USK-01",
            operator="Üsküdar Belediyesi",
            geometry=WKTElement("POINT(29.02 41.02)", srid=4326),
            source_properties={"emergency": "assembly_point"},
        ),
        AssemblyArea(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            source_feature_id="node/1000000007",
            name="Beşiktaş Parkı Toplanma Alanı",
            ref="BES-01",
            operator="Beşiktaş Belediyesi",
            geometry=WKTElement("POINT(29.00 41.04)", srid=4326),
            source_properties={"emergency": "assembly_point"},
        ),
        AssemblyArea(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            source_feature_id="node/1000000008",
            name="Kartal Sahil Toplanma Alanı",
            ref="KTL-01",
            operator="Kartal Belediyesi",
            geometry=WKTElement("POINT(29.18 40.89)", srid=4326),
            source_properties={"emergency": "assembly_point"},
        ),
        AssemblyArea(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            source_feature_id="node/1000000009",
            name="Pendik Sahil Toplanma Alanı",
            ref="PND-01",
            operator="Pendik Belediyesi",
            geometry=WKTElement("POINT(29.23 40.87)", srid=4326),
            source_properties={"emergency": "assembly_point"},
        ),
        AssemblyArea(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            source_feature_id="node/1000000010",
            name="Maltepe Sahil Toplanma Alanı",
            ref="MLT-01",
            operator="Maltepe Belediyesi",
            geometry=WKTElement("POINT(29.13 40.92)", srid=4326),
            source_properties={"emergency": "assembly_point"},
        ),
        AssemblyArea(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            source_feature_id="way/226421064",
            name="Athletic Center",
            ref=None,
            operator=None,
            geometry=WKTElement(
                "POLYGON((29.2573531 41.0342234,29.2578147 41.034509,"
                "29.2583958 41.0340062,29.2581229 41.0338401,"
                "29.2581881 41.0337742,29.2580086 41.0336661,"
                "29.2573531 41.0342234))",
                srid=4326,
            ),
            source_properties={"leisure": "sports_centre"},
        ),
    ]

    session.add_all(areas)
    session.flush()
    return dataset, areas
