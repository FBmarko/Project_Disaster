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

The backend follows a modular layout:

```
backend/
├── alembic/                       # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_enable_postgis.py # Initial migration enabling PostGIS
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
│   │           └── health.py      # Health check endpoint router
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py              # Application settings via pydantic-settings
│   └── db/
│       ├── __init__.py
│       ├── base.py                # SQLAlchemy 2.x DeclarativeBase
│       ├── session.py             # Engine & SessionLocal factory
│       ├── dependencies.py        # FastAPI get_db dependency
│       └── readiness.py           # Database connectivity & PostGIS check
├── tests/
│   ├── __init__.py
│   ├── test_config.py             # Database configuration tests
│   ├── test_database_integration.py # Live PostgreSQL/PostGIS integration tests
│   ├── test_db_session.py         # Session lifecycle tests
│   └── test_health.py             # Public health endpoint tests
├── .env.example                   # Safe template for environment variables
├── pyproject.toml                 # Dependencies, tool configurations
└── README.md
```

## Current Phase

This repository currently represents **Phase 2: Database Infrastructure Foundation**.

At this stage:
- PostgreSQL + PostGIS database infrastructure, SQLAlchemy 2.x configuration, session management, and Alembic migrations are established.
- **Domain models** (e.g. `FaultLine`, `EarthquakeHazard`, `AssemblyArea`, `Disaster`), **user authentication/accounts**, **AI/LLM integrations**, and **external disaster/map APIs** have **NOT** been implemented yet.
- The FastAPI backend itself is **not containerized** in this phase (only the database runs in Docker).
