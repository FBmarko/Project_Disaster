# AFET360 Backend

## Overview

AFET360 backend is a modular API built with Python and FastAPI designed for the AFET360 natural disaster preparedness platform.

## Requirements

- Python >= 3.12
- `uv` (recommended) or standard Python `venv` + `pip`
- Docker & Docker Compose (for local development database)

## Database Technology

The geospatial database layer is composed of:

- **PostgreSQL**: Relational database engine
- **PostGIS**: Spatial database extender for geographic objects
- **SQLAlchemy 2.x**: Object-relational mapping and database engine layer
- **GeoAlchemy2**: Geospatial extension for SQLAlchemy
- **Alembic**: Database schema migration management tool
- **psycopg 3**: Modern PostgreSQL driver for Python

## Local Setup

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python 3.12 virtual environment:
   ```bash
   # Using uv
   uv venv --python 3.12
   .venv\Scripts\activate      # Windows
   # source .venv/bin/activate # Linux / macOS

   # Or using standard python
   python -m venv .venv
   .venv\Scripts\activate      # Windows
   # source .venv/bin/activate # Linux / macOS
   ```

3. Install project dependencies:
   ```bash
   # Using uv
   uv pip install -e ".[dev]"

   # Or standard pip
   pip install -e ".[dev]"
   ```

4. (Optional) Configure environment variables:
   Copy `.env.example` to `.env` if custom configuration is needed:
   ```bash
   cp .env.example .env
   ```

## Local Database Setup

A PostgreSQL + PostGIS service is configured using Docker Compose at the repository root.

1. Start the development database:
   ```bash
   docker compose up -d
   ```

2. Run database migrations from the `backend/` directory:
   ```bash
   alembic upgrade head
   ```

3. Inspect migration status:
   ```bash
   alembic current
   alembic history
   ```

4. Stop the development database:
   ```bash
   docker compose down
   ```

*Note: During local development, the PostgreSQL/PostGIS database runs inside Docker, while the FastAPI backend runs directly on the host machine.*

## Running the Development Server

Start the local development server with auto-reload:

```bash
uvicorn app.main:app --reload
```

By default, the server will run on `http://127.0.0.1:8000`.

## API Documentation

FastAPI provides automatic interactive documentation available when the server is running:

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI JSON**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

### Health Endpoint

A public health-check endpoint is exposed at:

- `GET /api/v1/health`

Response:
```json
{
  "status": "ok",
  "service": "AFET360 API",
  "version": "0.1.0"
}
```

### Fault Lines REST API

Public read-only endpoints serving active fault segments as standard RFC 7946 GeoJSON:

- `GET /api/v1/fault-lines`: List active fault features (supports optional `bbox=min_lon,min_lat,max_lon,max_lat`, `fault_type`, and `limit`)
  ```bash
  curl "http://127.0.0.1:8000/api/v1/fault-lines?bbox=28.0,40.0,30.0,41.5&limit=100"
  ```
- `GET /api/v1/fault-lines/nearby`: Query fault segments within a required geodesic radius (in km) from a WGS84 point
  ```bash
  curl "http://127.0.0.1:8000/api/v1/fault-lines/nearby?latitude=40.99&longitude=29.03&radius_km=50"
  ```
- `GET /api/v1/fault-lines/{fault_id}`: Retrieve a single fault segment feature by its AFET360 internal UUID
  ```bash
  curl http://127.0.0.1:8000/api/v1/fault-lines/0f2943fd-5947-450b-88e5-ca7e68036d9b
  ```

Key details:
- **Coordinate Order**: Strictly follows RFC 7946 GeoJSON format: `[longitude, latitude]`.
- **Proximity Semantics**: The `radius_km` parameter represents geographic proximity only (not a hazard zone threshold).
- **Attribution & Provenance**: Active fault data is sourced from GEM GAF-DB (CC BY-SA 4.0) intersecting the Natural Earth 1:50m Türkiye polygon. It is open research data for development/staging and is **not** official Turkish government / MTA fault data.

## Running Tests

Run the unit test suite:

```bash
pytest
```

To run only unit tests (excluding integration tests requiring a live database):

```bash
pytest -m "not integration"
```

To run all tests including database integration tests:

```bash
pytest -m "integration"
```

## Linting

Check and format code quality using `ruff`:

```bash
ruff check .
ruff format --check .
```

## Current Architecture

The backend follows a modular domain layout:

```
backend/
├── alembic/                       # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 0001_enable_postgis.py        # Initial migration enabling PostGIS
│       ├── 0002_create_fault_segments.py # FaultSegment table & spatial GiST index
│       ├── 0003_create_earthquake_events.py # EarthquakeEvent table & GiST index
│       └── 0004_create_hazard_tables.py # HazardDataset & EarthquakeHazardPoint tables
├── alembic.ini                    # Alembic configuration
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entrypoint
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py              # Root API router (mounts versioned routers)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py          # v1 router (mounts endpoint routers)
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── earthquakes.py # Earthquake GeoJSON & proximity API endpoints
│   │           ├── fault_lines.py # Fault lines GeoJSON API endpoint router
│   │           └── health.py      # Health check endpoint router
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py              # Application settings via pydantic-settings
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py                # SQLAlchemy 2.x DeclarativeBase
│   │   ├── session.py             # Engine & SessionLocal factory
│   │   ├── dependencies.py        # FastAPI get_db dependency
│   │   └── readiness.py           # Database connectivity & PostGIS check
│   ├── integrations/
│   │   ├── afad/                  # Official AFAD Event Web Service adapter
│   │   │   ├── __init__.py
│   │   │   ├── client.py          # HTTP client with retries, timeout & pagination
│   │   │   ├── mapping.py         # Timestamp UTC parser, context BBOX, attribution
│   │   │   └── parser.py          # JSON parser & Pydantic schema validator
│   │   └── gem/                   # GEM Global Active Faults & GSHM hazard adapters
│   │       ├── __init__.py
│   │       ├── hazard_constants.py # GSHM v2026.1 scientific metadata & specs
│   │       ├── hazard_reader.py   # RTree GeoPackage streaming reader & validator
│   │       ├── mapping.py         # Fault mapping & MultiLineString 2D normalization
│   │       └── parser.py          # Fault GeoJSON parser & bounding box filter
│   ├── models/
│   │   ├── __init__.py
│   │   ├── earthquake_event.py    # EarthquakeEvent PostGIS Point model
│   │   ├── earthquake_hazard_point.py # EarthquakeHazardPoint PostGIS Point model
│   │   ├── fault_segment.py       # FaultSegment PostGIS MultiLineString model
│   │   └── hazard_dataset.py      # HazardDataset normalized metadata model
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── earthquake_event.py    # EarthquakeEvent database repository
│   │   ├── earthquake_hazard.py   # EarthquakeHazardRepository for dataset & points
│   │   └── fault_segment.py       # FaultSegment database repository & spatial queries
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── earthquake_api.py      # Public GeoJSON Feature & attribution schemas
│   │   ├── earthquake_event.py    # EarthquakeEvent validation schemas
│   │   ├── fault_line_api.py      # Public GeoJSON Feature / FeatureCollection schemas
│   │   └── fault_segment.py       # Pydantic validation schemas
│   ├── scripts/
│   │   ├── __init__.py
│   │   ├── import_gem_faults.py   # Developer CLI command to import GEM active faults
│   │   ├── import_gem_hazard.py   # Developer CLI command to ingest GEM GSHM hazard points
│   │   └── sync_afad_earthquakes.py # Developer CLI command to sync AFAD earthquakes
│   └── services/
│       ├── __init__.py
│       ├── earthquake_query.py    # EarthquakeQueryService for GeoJSON response assembly
│       ├── earthquake_sync.py     # EarthquakeSyncService with batch upsert & stats
│       ├── fault_import.py        # FaultImportService with batch transaction & stats
│       ├── fault_query.py         # FaultQueryService for GeoJSON response assembly
│       └── hazard_import.py       # HazardImportService for idempotent hazard ingestion
├── data/                          # Geospatial dataset documentation & local storage
│   ├── README.md
│   └── turkey_boundary.geojson    # Natural Earth 1:50m country boundary polygon
├── docs/                          # Architecture specifications & ADRs
│   ├── gem-gshm-v2026-1-artifact-inspection.md
│   ├── earthquake-hazard-source-validation.md
│   ├── geospatial-data-architecture.md
│   └── adr/
│       └── 0001-geospatial-data-sources.md
├── tests/
│   ├── __init__.py
│   ├── fixtures/
│   │   ├── afad_events_sample.json
│   │   └── gem_faults_turkey_sample.json
│   ├── test_afad_adapter.py
│   ├── test_config.py
│   ├── test_database_integration.py
│   ├── test_db_session.py
│   ├── test_earthquake_api.py
│   ├── test_earthquake_integration.py
│   ├── test_fault_lines_api.py
│   ├── test_fault_segment_integration.py
│   ├── test_gem_adapter.py
│   ├── test_hazard_adapter.py     # GEM hazard reader & synthetic GeoPackage unit tests
│   ├── test_hazard_integration.py # Hazard models & idempotent import integration tests
│   ├── test_hazard_models.py      # HazardDataset & EarthquakeHazardPoint schema tests
│   └── test_health.py
├── .env.example
├── pyproject.toml
└── README.md
```

## Data Import Workflow (GEM Active Faults)

For development and staging, active fault geometries are sourced from the **GEM Global Active Faults Database** under the **CC BY-SA 4.0** license:

```bash
# 1. Natural Earth Country Boundary Spatial Intersection [Default]
#    Retains GEM GAF fault features intersecting the Natural Earth 1:50m Türkiye polygon (722 features)
python -m app.scripts.import_gem_faults --download --turkey-only

# 2. Regional Tectonic Context
#    Retains faults within the wider regional tectonic bounding box (24-46°E, 34-44°N, 1,051 features)
python -m app.scripts.import_gem_faults --download --turkey-context

# 3. Global Dataset
#    Imports all worldwide active fault features without spatial filtering (16,195 features)
python -m app.scripts.import_gem_faults --download --all

# Or import from a local GeoJSON file:
python -m app.scripts.import_gem_faults --file path/to/faults.geojson --turkey-only
```

- **Idempotency**: All imports utilize an idempotent composite unique key `(source, source_feature_id)`. Re-running imports updates changed records and leaves unchanged records intact without duplicate creation.
- **Attribution Requirement**: Visualizations and API responses derived from GEM GAF must include attribution to the Global Earthquake Model Foundation.
- **Administrative Boundary**: Country boundary filtering uses the Natural Earth 1:50m open country-boundary polygon (`ne_50m_admin_0_countries`, Public Domain). It is a generalized cartographic boundary, not an official Turkish government boundary source.

## Earthquake Data Synchronization (AFAD Event Web Service)

Major earthquake events ($M \ge 5.0$) are ingested from the official **AFAD Deprem Dairesi Başkanlığı Event Web Service** (`https://deprem.afad.gov.tr/apiv2/event/filter`).

- **Epicenter Geometry**: Persisted as PostGIS `POINT(longitude latitude)` in WGS84 (SRID 4326), indexed with a GiST spatial index.
- **Timestamp Semantics**: Upstream AFAD API timestamps are confirmed to represent UTC and are normalized into timezone-aware UTC `occurred_at` datetimes.
- **Tectonic Context Scope (`turkey-context`)**: Bounded by `[24.0°E, 34.0°N, 46.0°E, 44.0°N]`, encompassing the Anatolian tectonic plate and immediate offshore seismic sources.
- **Idempotent Synchronization**: Keyed on unique `(source, source_event_id)`. Re-syncing preserves existing records and updates revised solutions without generating duplicates.

```bash
# Synchronize M >= 5.0 earthquakes for a bounded time window:
python -m app.scripts.sync_afad_earthquakes --start "2023-01-01 00:00:00" --end "2024-01-01 00:00:00" --min-magnitude 5.0 --scope turkey-context

# Custom magnitude threshold or global scope:
python -m app.scripts.sync_afad_earthquakes --start "2024-01-01" --end "2024-06-01" --min-magnitude 4.5 --scope all
```

- **Attribution**: *T.C. İçişleri Bakanlığı Afet ve Acil Durum Yönetimi Başkanlığı (AFAD) Deprem Dairesi Başkanlığı Event Web Servisi*.

## Seismic Hazard Data Ingestion (GEM GSHM v2026.1)

Seismic hazard data is ingested from the **GEM Global Seismic Hazard Map (v2026.1)** under the **CC BY-NC-SA 4.0** license for non-commercial development and competition use:

- **Scientific Metric**: Peak Ground Acceleration (PGA) in units of $g$ (10% exceedance in 50 years / ~475-year return period, reference rock $V_{S,30} = 800\text{ m/s}$).
- **Database Architecture**: Normalized two-table schema:
  - `hazard_datasets`: Stores model provenance, return period, reference ground conditions, checksum, and licensing once.
  - `earthquake_hazard_points`: Stores discrete grid nodes with `POINT(longitude latitude)` PostGIS geometry and `pga_g`.
- **Idempotency**: Keyed on `UNIQUE (dataset_id, longitude, latitude)`. Re-running the importer verifies unchanged records and leaves existing data intact.

```bash
# Run idempotent GEM GSHM hazard ingestion from external cache:
python -m app.scripts.import_gem_hazard --cache-dir "<external-hazard-cache-path>"

# Or specify GeoPackage directly:
python -m app.scripts.import_gem_hazard --gpkg-path "<path-to-gem_gshm_v2026.1.gpkg>"
```

- **Attribution**: *Global Seismic Hazard Map (v2026.1), Global Earthquake Model (GEM) Foundation (CC BY-NC-SA 4.0)*.
- **Important**: GEM hazard points represent regional modeled reference rock ground motion at discrete nodes. They do not represent building safety, local soil amplification, or official regulatory Turkish hazard (TDTH).

## Public Geospatial REST API

All public endpoints serve RFC 7946 compliant GeoJSON `FeatureCollection` or `Feature` structures with metadata describing data delivery, attribution, and disclaimers.

### 1. Earthquakes API (`/api/v1/earthquakes`)

- **List earthquakes with magnitude, temporal, and bounding box filters**:
  ```bash
  GET /api/v1/earthquakes?min_magnitude=5.0&limit=50
  GET /api/v1/earthquakes?bbox=28.0,40.0,30.0,42.0
  GET /api/v1/earthquakes?start_time=2023-01-01T00:00:00Z&end_time=2023-12-31T23:59:59Z
  ```

- **List recent major earthquakes (default: M>=5.0, past 365 days)**:
  ```bash
  GET /api/v1/earthquakes/recent-major
  ```

- **Recent major earthquakes with optional fault proximity filter**:
  ```bash
  GET /api/v1/earthquakes/recent-major?max_distance_km=25
  ```
  Returns recent major earthquakes within 25 km of any mapped fault trace, enriched with `nearest_fault_id`, `nearest_fault_source_feature_id`, `distance_to_fault_km`, and non-causal disclaimer.

- **Get single earthquake feature**:
  ```bash
  GET /api/v1/earthquakes/{event_id}
  ```

### 2. Fault Proximity Earthquakes (`/api/v1/fault-lines/{fault_id}/earthquakes`)

- **Find earthquakes within a caller-specified radius of a specific fault**:
  ```bash
  GET /api/v1/fault-lines/{fault_id}/earthquakes?max_distance_km=25&min_magnitude=5.0
  ```
  Supports sorting by `order_by=recent` (default) or `order_by=distance`.

> [!IMPORTANT]
> **Scientific Non-Causal Policy**:
> Spatial proximity (`distance_to_fault_km`) is a geographic measurement between an earthquake epicenter Point and a surface-mapped fault trace. **Spatial proximity does not establish that the earthquake ruptured on or was caused by that fault.** The API strictly uses `association_method = "spatial_proximity"`.

## Current Phase

This repository currently represents **Phase 8B-3: GEM GSHM PostgreSQL/PostGIS Model, Migration, and Idempotent Importer**.

At this stage:
- The `fault_segments`, `earthquake_events`, `hazard_datasets`, and `earthquake_hazard_points` PostGIS models, indexes, and migrations (`0001` - `0004`) are operational.
- The public Fault Lines GeoJSON API is operational.
- The public Earthquake GeoJSON API is operational.
- The GEM hazard ingestion foundation is operational (`54,291` Türkiye-context points persisted).
- **Public Earthquake Hazard API (`/api/v1/earthquake-hazards`)** is **NOT** exposed yet (designated for TASK 09).
- **User authentication/accounts** and **AI disaster assistant** have **NOT** been implemented yet.
