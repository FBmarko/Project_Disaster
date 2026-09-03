# AFET360 Backend

## Overview

AFET360 backend is a modular API built with Python and FastAPI designed for the AFET360 natural disaster preparedness platform.

## Requirements

- Python >= 3.12
- `uv` (recommended) or standard Python `venv` + `pip`

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

A health-check endpoint is exposed at:

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

Run the automated test suite using `pytest` from the `backend/` directory:

```bash
pytest
```

## Linting

Check and format code quality using `ruff`:

```bash
ruff check .
```

## Current Architecture

The backend follows a modular router layout:

```
backend/
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
│   └── core/
│       ├── __init__.py
│       └── config.py              # Application settings via pydantic-settings
├── tests/
│   ├── __init__.py
│   └── test_health.py             # TestClient health endpoint tests
├── .env.example                   # Safe template for environment variables
├── pyproject.toml                 # Dependencies, tool configurations
└── README.md
```

Routing structure flow:
`app.main:app` -> `app/api/router.py` -> `app/api/v1/router.py` -> `app/api/v1/endpoints/health.py`

## Current Phase

This repository currently represents **Phase 1: Backend Foundation**.

At this stage:
- The core FastAPI application structure, configuration management, and health endpoint are established.
- **Database (PostgreSQL / PostGIS / SQLAlchemy / Alembic)**, **Redis**, **Authentication**, **AI / LLM integrations**, **Docker / CI-CD**, and **external disaster/map APIs** have **NOT** been implemented yet.
- These components will be introduced systematically in upcoming development phases.
