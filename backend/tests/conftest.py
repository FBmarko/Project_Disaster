from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session

from app.core.rate_limit import rate_limiter
from app.db.dependencies import get_db
from app.db.session import engine
from app.models.assembly_area import AssemblyArea
from app.models.assembly_area_dataset import AssemblyAreaDataset
from app.models.earthquake_event import EarthquakeEvent
from app.models.earthquake_hazard_point import EarthquakeHazardPoint
from app.models.fault_segment import FaultSegment
from app.models.hazard_dataset import HazardDataset
from tests.fixtures.sample_dataset_fixtures import (
    create_sample_assembly_dataset,
    create_sample_earthquakes,
    create_sample_faults,
    create_sample_hazard_dataset,
)


@pytest.fixture(autouse=True)
def reset_rate_limiter_each_test():
    """Reset rate limiter state before each test to maintain test isolation."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture
def isolated_session() -> Generator[Session, None, None]:
    """Provide an isolated database session within a transaction that rolls back."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def sample_fault_dataset(
    isolated_session: Session,
) -> Generator[list[FaultSegment], None, None]:
    """Provide sample fault records bound to test request dependency override."""
    faults = create_sample_faults(isolated_session)
    from app.main import app

    app.dependency_overrides[get_db] = lambda: isolated_session
    try:
        yield faults
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def sample_hazard_dataset(
    isolated_session: Session,
) -> Generator[tuple[HazardDataset, list[EarthquakeHazardPoint]], None, None]:
    """Provide sample GEM GSHM hazard dataset and grid points bound to test request."""
    dataset, points = create_sample_hazard_dataset(isolated_session)
    from app.main import app

    app.dependency_overrides[get_db] = lambda: isolated_session
    try:
        yield dataset, points
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def sample_assembly_dataset(
    isolated_session: Session,
) -> Generator[tuple[AssemblyAreaDataset, list[AssemblyArea]], None, None]:
    """Provide sample OSM assembly area dataset and features bound to test request."""
    dataset, areas = create_sample_assembly_dataset(isolated_session)
    from app.main import app

    app.dependency_overrides[get_db] = lambda: isolated_session
    try:
        yield dataset, areas
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def sample_earthquake_dataset(
    isolated_session: Session,
) -> Generator[tuple[list[FaultSegment], list[EarthquakeEvent]], None, None]:
    """Provide sample faults and earthquake events bound to test request."""
    faults = create_sample_faults(isolated_session)
    events = create_sample_earthquakes(isolated_session)
    from app.main import app

    app.dependency_overrides[get_db] = lambda: isolated_session
    try:
        yield faults, events
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def sample_all_datasets(
    isolated_session: Session,
) -> Generator[dict[str, object], None, None]:
    """Provide all 4 sample datasets bound to test request dependency override."""
    faults = create_sample_faults(isolated_session)
    events = create_sample_earthquakes(isolated_session)
    h_ds, h_pts = create_sample_hazard_dataset(isolated_session)
    a_ds, a_areas = create_sample_assembly_dataset(isolated_session)
    from app.main import app

    app.dependency_overrides[get_db] = lambda: isolated_session
    try:
        yield {
            "faults": faults,
            "earthquakes": events,
            "hazard_dataset": h_ds,
            "hazard_points": h_pts,
            "assembly_dataset": a_ds,
            "assembly_areas": a_areas,
        }
    finally:
        app.dependency_overrides.pop(get_db, None)
