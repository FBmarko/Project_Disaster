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

### Earthquake Hazards REST API

Public read-only endpoints serving seismic hazard data from the imported GEM Global Seismic Hazard Map (GSHM v2026.1):

- `GET /api/v1/earthquake-hazards/dataset`: Retrieve full scientific provenance, reference rock parameters, DOIs, license, and bounds for the active dataset.
  ```bash
  curl http://127.0.0.1:8000/api/v1/earthquake-hazards/dataset
  ```
- `GET /api/v1/earthquake-hazards/nearest`: Query modeled PGA at the nearest discrete GEM source node to a coordinate:
  ```bash
  curl "http://127.0.0.1:8000/api/v1/earthquake-hazards/nearest?lat=39.93&lon=32.85"
  ```
- `GET /api/v1/earthquake-hazards`: Retrieve discrete GEM source nodes within a viewport bounding box as an RFC 7946 GeoJSON FeatureCollection:
  ```bash
  curl "http://127.0.0.1:8000/api/v1/earthquake-hazards?bbox=28.0,40.0,30.0,42.0&limit=1000&offset=0"
  ```

Key scientific semantics & details:
- **Scientific Foundation**: Modeled Peak Ground Acceleration (PGA) in units of decimal $g$ for a 10% probability of exceedance in 50 years (approximately 475-year return period) under reference rock conditions ($V_{S,30} = 800\text{ m/s}$).
- **Nearest-Node Semantics**: Returns the discrete modeled value at the nearest stored GEM source node along with the exact geodesic distance in kilometers between the requested coordinate and that node. Strictly avoids spatial interpolation or arbitrary distance cutoffs.
- **Two-Stage Query Optimization & Empirical Validation**: Nearest lookup executes via a two-stage query (32-candidate GiST KNN set followed by exact PostGIS geography `ST_Distance` re-ranking with deterministic `id` tie-breaking). Empirically validated against the exact spheroidal-distance baseline with 0 mismatches across the evaluated 359-coordinate test set (local SQL execution benchmark ~0.15 ms vs ~105 ms baseline). This empirical validation is not a mathematical proof for every possible coordinate.
- **Coverage Validation**: Coordinates and viewport bounding boxes must strictly fall within the imported Türkiye-context scope ($24.0..46.0^\circ\text{E}$, $34.0..44.0^\circ\text{N}$). Requests outside this scope return HTTP 422.
- **Viewport Filtering & Pagination**: Uses PostGIS GiST spatial index envelope filtering (`&&`). Point-in-envelope candidate semantics are exact for discrete POINT geometries. Supports deterministic pagination via `limit` (1–2000, default 1000) and `offset` (default 0), returning a boolean `has_more` without redundant total count queries (local development benchmark: ~3.1 ms query time, ~223 KB payload for 1,000 points; ~418 KB for 2,000 points).
- **Missing Dataset Failure Semantics**: If the required GEM dataset natural identity is absent from the database, all hazard endpoints return HTTP 503 Service Unavailable (*"Earthquake hazard dataset is currently unavailable."*).
- **Scientific Disclaimers & Non-Causal Nature**: Values represent discrete reference-rock nodes and do NOT represent local soil amplification, building safety ratings, earthquake prediction, or official Turkish regulatory design values (AFAD TDTH / Decision 2018/11275).
- **License & Attribution**: GEM GSHM v2026.1 is distributed under CC BY-NC-SA 4.0 for non-commercial development and research.

### Emergency Assembly Areas REST API

Public read-only endpoints serving emergency gathering points from the imported OpenStreetMap snapshot (`emergency=assembly_point`):

- `GET /api/v1/assembly-areas/dataset`: Retrieve comprehensive provenance, ODbL 1.0 license, OpenStreetMap contributors attribution, timestamps, cryptographic SHA-256 checksum, and geometry counts (discrete Points and closed Polygons) for the active dataset.
  ```bash
  curl http://127.0.0.1:8000/api/v1/assembly-areas/dataset
  ```
- `GET /api/v1/assembly-areas/nearby`: Query emergency assembly areas within a required geodesic radius (in km) from a WGS84 coordinate:
  ```bash
  curl "http://127.0.0.1:8000/api/v1/assembly-areas/nearby?lat=41.01&lon=28.97&radius_km=5.0&limit=20"
  ```
- `GET /api/v1/assembly-areas`: Retrieve emergency assembly areas as an RFC 7946 GeoJSON FeatureCollection with optional viewport bounding box filter:
  ```bash
  curl "http://127.0.0.1:8000/api/v1/assembly-areas?bbox=28.8,40.9,29.2,41.2&limit=1000"
  ```

Key geospatial details & operational semantics:
- **Geometry Preservation**: Preserves native PostGIS `Point` (650) and `Polygon` (28) geometries without centroid flattening or loss of spatial boundaries.
- **Exact Proximity Calculation**: Distance is calculated directly using PostGIS spheroidal geography (`ST_DWithin` and `ST_Distance`) on the WGS84 ellipsoid without lossy degree-based bounding box prefilters. For Polygon geometries, distance represents the minimum geodesic distance to the polygon boundary; for coordinates inside a polygon, distance is exactly `0.0`.
- **Distance Output Resolution**: The `distance_km` field is serialized to 3 decimal places (0.001 km output resolution / approximately metre-level displayed resolution; this reflects output precision and carries no claim of geodetic survey-grade real-world accuracy).
- **Public Feature Properties Contract**:
  - `GET /api/v1/assembly-areas`: Feature properties allowlist strictly contains `{source_feature_id, name, ref, operator}` (root Feature contains `type`, `id`, `geometry`, `properties`).
  - `GET /api/v1/assembly-areas/nearby`: Feature properties allowlist strictly contains `{source_feature_id, name, ref, operator, distance_km}`.
  - Omitted fields: Per-feature administrative fields (`city`, `district`), capacity, geometry redundancy flags (`has_polygon`), or officiality booleans (`is_designated_official`, `official`, `afad_verified`) are strictly omitted.
- **Missing Dataset vs. Empty Query Semantics**:
  - Missing backing dataset in database: all 3 endpoints (`/`, `/nearby`, `/dataset`) fail closed with HTTP 503 Service Unavailable (`{"detail": "Assembly area dataset is currently unavailable."}`).
  - Valid spatial query with zero matching features: returns HTTP 200 OK with GeoJSON `FeatureCollection` containing empty `features: []`, `metadata.returned_count: 0`, and `metadata.truncated: false`.
- **Canonical Bounding Box Contract**: Follows the canonical AFET360 viewport parameter `bbox=min_lon,min_lat,max_lon,max_lat`. Inverted bounds or malformed values fail closed with HTTP 422.
- **Technical Radius Ceiling**: Proximity search enforces $0 < \text{radius\_km} \le 200\text{ km}$ as a technical API resource ceiling to protect computational resources, never as operational evacuation guidance.
- **Privacy & Security Defense**: Strictly whitelists public properties (`source_feature_id`, `name`, `ref`, `operator`, plus `distance_km` in nearby queries). Internal columns (`dataset_id`, `created_at`, `updated_at`, `source_properties`), local file system paths, and unapproved OSM tags are never exposed.
- **Deterministic Resolution & Availability**: Multiple dataset records are resolved deterministically by `source_data_timestamp DESC, snapshot_retrieved_at DESC, created_at DESC, id DESC`. If no dataset exists, all endpoints return HTTP 503 Service Unavailable (*"Assembly area dataset is currently unavailable."*).
- **Non-Officiality Disclaimer**: Community-mapped data from OpenStreetMap. This dataset is geographically incomplete, may include facility-specific muster points, is NOT official Turkish government / AFAD disaster gathering area data (*"Afet ve Acil Durum Toplanma Alanları"*), and carries no guarantees regarding structural safety, current accessibility, or safe evacuation routes.
- **License & Attribution**: OpenStreetMap data is licensed under the Open Data Commons Open Database License (ODbL 1.0) by the OpenStreetMap Foundation (OSMF). Attribution: *"© OpenStreetMap contributors"*. Required for any frontend view displaying this data.

### AI Disaster Preparedness Guide REST API

Public POST endpoint serving structured, safety-governed disaster preparedness advice generated by an abstract AI provider:

- `POST /api/v1/ai/preparedness-guide`: Generate structured preparedness advice across preparation, response, recovery, and kit phases.

Example request:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/ai/preparedness-guide" \
  -H "Content-Type: application/json" \
  -d '{
    "disaster_type": "earthquake",
    "city": "İzmir",
    "language": "tr"
  }'
```

Example response (with active provider):
```json
{
  "generated_by_ai": true,
  "disaster_type": "earthquake",
  "language": "tr",
  "city": "İzmir",
  "disclaimer": "Bu afet rehberi yapay zeka tarafından genel bilgilendirme amacıyla hazırlanmıştır. Resmi uyarı, bina güvenliği veya tahliye garantisi içermez. Acil durumlarda AFAD ve resmi makamların talimatlarına uyunuz.",
  "guide": {
    "summary": "Deprem öncesi, sırası ve sonrasında can güvenliğinizi korumak için temel adımlar.",
    "before": [
      "Mobilyaları duvara sabitleyin.",
      "Aile afet ve acil durum planı hazırlayın.",
      "Afet ve acil durum çantanızı hazır bulundurun."
    ],
    "during": [
      "Sarsıntı anında panik yapmayın.",
      "ÇÖK - KAPAN - TUTUN pozisyonunu uygulayın.",
      "Merdivenlere ve asansörlere koşmayın."
    ],
    "after": [
      "Sarsıntı durduğunda gaz, su ve elektrik vanalarını kapatın.",
      "Acil durum çantanızı alarak binayı dikkatle tahliye edin.",
      "Resmi duyuruları takip edin ve toplanma alanına geçin."
    ],
    "emergency_kit": [
      "Kişi başı en az 3 günlük su ve bozulmayan gıda",
      "İlk yardım çantası ve düzenli kullanılan ilaçlar",
      "Pilli radyo, el feneri ve yedek piller",
      "Düdük ve çok amaçlı çakı"
    ],
    "important_notes": [
      "Telefon hatlarını gereksiz yere meşgul etmeyin; iletişimi SMS veya internet üzerinden sağlayın.",
      "Hasarlı binalara kesinlikle girmeyin."
    ]
  }
}
```

Key contract specifications & safety architecture:
- **Disaster Types & Supported Languages**: Strictly constrained to supported disaster types (`earthquake`, `flood`, `fire`) and ISO 639-1 language codes (`tr`, `en`). Unsupported values fail closed with HTTP 422.
- **City Contextual Framing Semantics**: The optional `city` field (1–80 characters, whitespace-trimmed) provides high-level regional context only (e.g. general regional climate or geographic awareness). It is strictly forbidden from triggering local soil analysis, building certification, safe route guarantees, or official emergency declarations. Blank or whitespace-only inputs fail with HTTP 422.
- **Strict Payload Hardening (`extra="forbid"`)**: The request schema strictly rejects unknown or unexpected parameters (e.g. `prompt`, `system_prompt`, `instructions`, `messages`) with HTTP 422 Unprocessable Entity. Constraining user-controlled input and isolating server policy from user context significantly reduces the prompt-injection surface.
- **Structured Response Contract**: Responses enforce strict item counts and lengths across all advisory sections:
  - `summary`: 10–500 characters.
  - `before`: 1–8 bounded actionable steps (3–300 chars each).
  - `during`: 1–8 immediate protective actions (3–300 chars each).
  - `after`: 1–8 safe recovery actions (3–300 chars each).
  - `emergency_kit`: 1–12 practical kit supplies (2–160 chars each).
  - `important_notes`: 0–6 safety caveats and warnings (3–300 chars each).
- **Server-Side Safety Policy & Non-Negotiable Prohibitions**: Prompts are assembled server-side with strict safety rules:
  - Never predict specific future disasters or claim probabilities, dates, or times.
  - Never claim any specific building or structure is safe or unsafe.
  - Never guarantee that an evacuation route is open or safe.
  - Never claim an assembly area is officially certified without verified source data.
  - Never invent emergency alerts, alarms, sirens, or evacuation orders.
  - Never claim real-time sensor, weather, or incident knowledge.
  - Never impersonate AFAD, government officials, or emergency services.
  - Never diagnose medical conditions, prescribe medications, or claim professional medical authority (general emergency guidance such as checking for injuries, calling 112, keeping a first-aid kit, and following responders is permitted).
- **Accessibility-Aware Guidance**: The safety policy permits inclusive preparedness guidance for children, older adults, people with disabilities, and pets within existing structured sections, without collecting sensitive medical or personal health profiles.
- **Server-Attached Disclaimers**: Every response includes `generated_by_ai: true` and an authoritative, language-matched disclaimer (`DEFAULT_AI_DISCLAIMER_TR` or `DEFAULT_AI_DISCLAIMER_EN`) added exclusively by the server layer.
- **Production Default (HTTP 503) & Safety Defense**: In production, where no real external AI provider is configured (i.e. `GEMINI_API_KEY` is unset or blank), the endpoint returns HTTP 503 Service Unavailable (`{"detail": "AI preparedness service is currently unavailable."}`). Test/dummy content is **never** returned in production to prevent misrepresenting mock data as live AI advice.
- **Provider Abstraction & Testing Architecture**: The system uses `PreparednessAIProvider` (ABC) with dependency injection via FastAPI's `get_ai_provider`. A deterministic test stub (`StubPreparednessAIProvider`) lives strictly in the test suite (`tests/fakes/ai.py`) for offline testing, simulating successful responses, upstream service errors (HTTP 502), unavailabilities (HTTP 503), and malformed payloads (HTTP 502).
- **Production Google Gemini Integration (TASK 11B)**:
  - **Provider**: Google Gemini API via the official modern `google-genai` SDK (`from google import genai`).
  - **API Contract**: Uses Gemini's modern Interactions API (`client.interactions.create`) with single-turn, stateless execution.
  - **Default Model**: `gemini-3.8-flash` (configurable via `GEMINI_MODEL`).
  - **Stateless Privacy (`store=False`)**: AFET360 uses `store=False` for Gemini interactions and does not maintain application-level conversation history or persist generated guides.
  - **Structured Outputs**: Outputs are constrained to `PreparednessGuideContent` JSON Schema via `response_format` and defended in depth by local Pydantic validation.
  - **Latency & Predictability**: Configured with `thinking_level="low"`, `max_output_tokens=2500`, and configurable request timeout (`GEMINI_TIMEOUT_SECONDS`, default: 30.0s).
  - **Grounding & Tools**: Completely disabled (no web search, no maps, no function calling, no code execution), preserving the boundary that the system does not possess live situational awareness.
- **Stateless Operation & Zero Persistence**: The AI preparedness guide service is completely stateless. It performs zero database writes, creates zero tables, and stores no user prompts, contexts, or AI responses.
- **Dependency Pinning**: The direct dependency `google-genai==2.22.0` is pinned in `pyproject.toml` for SDK stability with the Interactions API (full transitive dependency locking is addressed in the container packaging stage).

#### AI Provider Operator & Configuration Reference

| Environment Variable | Required / Optional | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` | **Required for AI** | *None* | Google Gemini API key. If unset or blank, the endpoint fails closed with HTTP 503 without crashing the server. |
| `GEMINI_MODEL` | Optional | `gemini-3.8-flash` | Gemini model name used for structured preparedness guide generation. |
| `GEMINI_TIMEOUT_SECONDS` | Optional | `30.0` | Maximum network timeout in seconds for Gemini interaction requests. |

#### Frontend Integration & Teammate Handoff (Person 1 Quick Reference)

| Question / Specification | Backend Answer & Integration Guidance |
| :--- | :--- |
| **Endpoint URL & Method** | `POST /api/v1/ai/preparedness-guide` |
| **Request Payload Fields** | `{"disaster_type": "earthquake"|"flood"|"fire", "city": "Optional City", "language": "tr"|"en"}` |
| **Allowed Disaster Types** | `earthquake`, `flood`, `fire` |
| **Supported Languages** | `tr` (Turkish, default), `en` (English) |
| **Response Sections** | `summary`, `before`, `during`, `after`, `emergency_kit`, `important_notes` |
| **Does frontend parse Markdown?** | **NO.** Content is pre-structured into bounded JSON lists and strings for direct UI rendering. |
| **AI Provider Integration** | Google Gemini (`gemini-3.8-flash`) via official `google-genai` Interactions API (`store=False`). |
| **Production behavior without provider** | Returns `HTTP 503 Service Unavailable` (`{"detail": "AI preparedness service is currently unavailable."}`). |
| **Official emergency advice?** | **NO.** Educational guidance only; disclaimers explicitly mandate following AFAD instructions. |
| **Disaster prediction service?** | **NO.** The API never predicts events or computes occurrence probabilities. |
| **Are requests or guides stored in DB?** | **NO.** Completely stateless; zero database writes or logging of user prompts. |

### API Security Foundation & Rate Limiting Architecture (TASK 12)

AFET360 implements a lightweight, testable, configuration-driven security layer designed for single-process operation without distributed infrastructure dependencies (no Redis, no external gateway):

- **CORS Hardening**:
  - Configurable via `CORS_ALLOWED_ORIGINS` (defaults: `http://localhost:5173`, `http://127.0.0.1:5173` for Vite React frontend).
  - Wildcard origins (`*`) are disallowed in configured environments.
  - Credentials are explicitly disabled (`allow_credentials=False`) since AFET360 is an unauthenticated public educational emergency API.
  - Allowed HTTP methods are restricted to minimal required operations: `GET`, `POST`, `OPTIONS`.
  - Allowed headers are restricted to `Content-Type`, `Accept`.
- **Security Response Headers**:
  - `X-Content-Type-Options: nosniff` (prevents MIME-type confusion/sniffing).
  - `X-Frame-Options: DENY` (clickjacking protection; prevents embedding API in iframes).
  - `Referrer-Policy: no-referrer` (protects query parameters and paths from leakage in Referer header).
  - `Permissions-Policy: accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()` (restricts browser device access).
  - *HSTS is deferred to the production HTTPS reverse-proxy/TLS termination layer (TASK 16) to avoid breaking local development.*
  - *Frontend CSP is deferred to the web client packaging as this service is a pure JSON API.*
- **In-Memory Sliding-Window Rate Limiting (Per Process)**:
  - **Architecture**: In-memory FIFO deque of monotonic timestamps (`time.monotonic()`) protected by fine-grained thread locks (`threading.Lock`).
  - **Scope Limitation**: Limiter operates strictly **per backend process**. It is not a distributed rate limiter and does not require Redis or message brokers.
  - **Client Identity**: Uses directly connected client addresses from ASGI `request.client.host`.
  - **Spoofing Prevention**: `X-Forwarded-For`, `X-Real-IP`, and `Forwarded` headers are **not** trusted by default to prevent trivial client IP spoofing and rate-limit bypass. Trusted proxy IP resolution will be configured explicitly in TASK 16 deployment.
  - **Window-Aware Memory Bounding**: Each tracked bucket maintains its own window configuration. Stale cleanup prunes timestamps strictly according to each bucket's own sliding window (no arbitrary fixed expiration rules). A strict capacity bound (`max_keys`) ensures active bucket storage never exceeds memory limits; if capacity is exhausted after cleanup, new identities fail closed without evicting active clients.
  - **Precedence & Independent Quotas**:
    - **Exempt Routes**: CORS preflight (`OPTIONS`), exact documentation routes (`/docs`, `/redoc`, `/openapi.json`), and exact service health (`/api/v1/health`) are exempt. Generic route suffixes are not exempt.
    - **AI Endpoint (`POST /api/v1/ai/preparedness-guide`)**: Governed by a dedicated, stricter quota (`AI_RATE_LIMIT_REQUESTS=5`, `AI_RATE_LIMIT_WINDOW_SECONDS=60`) to protect paid LLM resources and upstream API quotas. Rate-limit rejection occurs **before** invoking the Gemini provider, ensuring rejected requests consume zero AI quota.
    - **General Endpoints (`/api/v1/*`)**: Governed by the general resource protection quota (`API_RATE_LIMIT_REQUESTS=120`, `API_RATE_LIMIT_WINDOW_SECONDS=60`) protecting database capacity and map responsiveness.
    - **Zero Double-Counting**: AI requests and general GeoJSON requests operate against separate bucket keys (`ai:{ip}` vs `general:{ip}`), ensuring high-frequency map navigation does not inadvertently block disaster guide generation.
  - **Rejection Contract**: Exceeded quotas return `HTTP 429 Too Many Requests` with a non-sensitive body (`{"detail": "Too many requests. Please try again later."}`) and an authoritative `Retry-After: <seconds>` header. Internal state, counters, client IPs, and tracebacks are never exposed.
- **Request Body Size Protection**:
  - **Configurable Limit**: Controlled by `API_MAX_REQUEST_BODY_BYTES` (default: `65536` bytes / 64 KiB).
  - **Scope**: Applied to mutating API methods (`POST`, `PUT`, `PATCH`) under `/api/v1/`. Read-only methods (`GET`), preflights (`OPTIONS`), responses, and documentation are unaffected.
  - **Two-Layer Enforcement**:
    1. Early rejection: Checks `Content-Length` header if present; if it exceeds the limit, immediately returns `HTTP 413` without reading the body.
    2. Streamed/chunked accounting: For requests with missing or chunked transfer encoding, received chunks are counted as streamed from ASGI `receive()`. If accumulated bytes exceed the limit, reading terminates immediately (buffering at most `limit + 1` bytes) to prevent memory exhaustion.
  - **Rejection Contract**: Returns `HTTP 413 Payload Too Large` with body `{"detail": "Request body too large."}`. Does not include `Retry-After`. Rejection occurs before Pydantic model parsing, service execution, or Gemini provider invocation.
- **Google Maps & Geolocation Compatibility Note**:
  - The API security header `Permissions-Policy: ... geolocation=() ...` applies strictly to JSON API responses. In production, the React frontend is served as a separate document origin. If frontend documents are later served through the same origin or reverse-proxy security-header layer, the frontend Permissions-Policy must be reviewed separately so required browser geolocation continues to function.

#### Security & Rate Limiting Configuration Reference

| Environment Variable | Required / Optional | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `CORS_ALLOWED_ORIGINS` | Optional | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated list of browser origins permitted to query the API. |
| `API_RATE_LIMIT_REQUESTS` | Optional | `120` | Maximum requests per sliding window for general `/api/v1/*` endpoints. |
| `API_RATE_LIMIT_WINDOW_SECONDS` | Optional | `60` | Duration in seconds of the general API sliding window. |
| `AI_RATE_LIMIT_REQUESTS` | Optional | `5` | Maximum requests per sliding window for `POST /api/v1/ai/preparedness-guide`. |
| `AI_RATE_LIMIT_WINDOW_SECONDS` | Optional | `60` | Duration in seconds of the AI endpoint sliding window. |
| `API_MAX_REQUEST_BODY_BYTES` | Optional | `65536` | Maximum incoming request body size in bytes (64 KiB) for mutating API endpoints. |

#### Jury & Evaluator Security Explainability Boundary

> "AFET360 utilizes rigorous input validation, explicit origin control (CORS), standard security headers, request body size protection, and process-level sliding-window rate limiting. AI generation operates under a stricter independent quota because it consumes external LLM resources. Secrets remain isolated to the backend, and rate limiting rejects unauthorized volume before invoking external providers."
>
> *AFET360 does not claim distributed DDoS mitigation, enterprise Web Application Firewall (WAF) functionality, or distributed multi-region rate synchronization. These infrastructure concerns are appropriately decoupled from the application layer and deferred to edge reverse-proxy/cloud infrastructure.*

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
│       ├── 0004_create_hazard_tables.py # HazardDataset & EarthquakeHazardPoint tables
│       └── 0005_create_assembly_tables.py # AssemblyAreaDataset & AssemblyArea tables
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
│   │           ├── ai.py                  # AI disaster preparedness guide POST endpoint
│   │           ├── assembly_areas.py # Emergency assembly areas REST API (dataset, nearby, bbox)
│   │           ├── earthquake_hazards.py # Earthquake hazard API endpoints (dataset, nearest, bbox)
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
│   │   ├── ai/                    # AI provider abstraction & safety policy architecture
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # PreparednessAIProvider abstract base class
│   │   │   ├── dependencies.py    # FastAPI provider dependency injection
│   │   │   ├── exceptions.py      # Domain exceptions (Unavailable, Malformed, Error)
│   │   │   ├── gemini.py          # Google Gemini Interactions API provider adapter
│   │   │   └── policy.py          # Safety policy constraints & prompt builder
│   │   ├── gem/                   # GEM Global Active Faults & GSHM hazard adapters
│   │   │   ├── __init__.py
│   │   │   ├── hazard_constants.py # GSHM v2026.1 scientific metadata & specs
│   │   │   ├── hazard_reader.py   # RTree GeoPackage streaming reader & validator
│   │   │   ├── mapping.py         # Fault mapping & MultiLineString 2D normalization
│   │   │   └── parser.py          # Fault GeoJSON parser & bounding box filter
│   │   └── osm/                   # OpenStreetMap assembly area snapshot ingestion
│   │       ├── __init__.py
│   │       ├── osm_constants.py   # ODbL provenance, contracts, and tag allowlists
│   │       ├── osm_reader.py      # Strict JSON snapshot parser and geometry builder
│   │       └── osm_sanitizer.py   # Allowlist-first tag sanitizer and PII defense
│   ├── models/
│   │   ├── __init__.py
│   │   ├── assembly_area.py       # AssemblyArea PostGIS Point/Polygon model
│   │   ├── assembly_area_dataset.py # AssemblyAreaDataset normalized provenance model
│   │   ├── earthquake_event.py    # EarthquakeEvent PostGIS Point model
│   │   ├── earthquake_hazard_point.py # EarthquakeHazardPoint PostGIS Point model
│   │   ├── fault_segment.py       # FaultSegment PostGIS MultiLineString model
│   │   └── hazard_dataset.py      # HazardDataset normalized metadata model
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── assembly_area.py       # AssemblyAreaRepository for dataset & areas
│   │   ├── earthquake_event.py    # EarthquakeEvent database repository
│   │   ├── earthquake_hazard.py   # EarthquakeHazardRepository for dataset & points
│   │   └── fault_segment.py       # FaultSegment database repository & spatial queries
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── ai.py                  # AI preparedness request, content & response schemas
│   │   ├── assembly_api.py        # Public GeoJSON Feature / Nearby schemas & metadata
│   │   ├── earthquake_api.py      # Public GeoJSON Feature & attribution schemas
│   │   ├── earthquake_event.py    # EarthquakeEvent validation schemas
│   │   ├── fault_line_api.py      # Public GeoJSON Feature / FeatureCollection schemas
│   │   ├── fault_segment.py       # Pydantic validation schemas
│   │   └── hazard_api.py          # GeoJSON schemas & scientific disclaimers for hazards
│   ├── scripts/
│   │   ├── __init__.py
│   │   ├── import_gem_faults.py   # Developer CLI command to import GEM active faults
│   │   ├── import_gem_hazard.py   # Developer CLI command to ingest GEM GSHM hazard points
│   │   ├── import_osm_assembly_areas.py # Developer CLI command to import OSM assembly areas
│   │   └── sync_afad_earthquakes.py # Developer CLI command to sync AFAD earthquakes
│   └── services/
│       ├── __init__.py
│       ├── assembly_import.py     # AssemblyImportService for idempotent OSM ingestion
│       ├── assembly_query.py      # AssemblyQueryService for GeoJSON collection & proximity queries
│       ├── earthquake_query.py    # EarthquakeQueryService for GeoJSON response assembly
│       ├── earthquake_sync.py     # EarthquakeSyncService with batch upsert & stats
│       ├── fault_import.py        # FaultImportService with batch transaction & stats
│       ├── fault_query.py         # FaultQueryService for GeoJSON response assembly
│       ├── hazard_import.py       # HazardImportService for idempotent hazard ingestion
│       ├── hazard_query.py        # HazardQueryService for spatial lookup & GeoJSON assembly
│       └── preparedness_guide.py  # PreparednessGuideService for safety prompt & validation
├── data/                          # Geospatial dataset documentation & local storage
│   ├── README.md
│   └── turkey_boundary.geojson    # Natural Earth 1:50m country boundary polygon
├── docs/                          # Architecture specifications & ADRs
│   ├── assembly-area-source-validation.md
│   ├── osm-turkey-assembly-point-snapshot-characterization.md
│   ├── gem-gshm-v2026-1-artifact-inspection.md
│   ├── earthquake-hazard-source-validation.md
│   ├── geospatial-data-architecture.md
│   └── adr/
│       ├── 0001-geospatial-data-sources.md
│       └── 0002-assembly-area-data-source.md
├── tests/
│   ├── __init__.py
│   ├── fakes/                     # Deterministic test-only providers & stubs
│   │   ├── __init__.py
│   │   └── ai.py                  # StubPreparednessAIProvider for automated testing
│   ├── fixtures/
│   │   ├── afad_events_sample.json
│   │   └── gem_faults_turkey_sample.json
│   ├── test_afad_adapter.py
│   ├── test_ai_preparedness.py    # AI preparedness API & safety policy tests
│   ├── test_config.py
│   ├── test_database_integration.py
│   ├── test_db_session.py
│   ├── test_earthquake_api.py
│   ├── test_earthquake_integration.py
│   ├── test_fault_lines_api.py
│   ├── test_fault_segment_integration.py
│   ├── test_gem_adapter.py
│   ├── test_gemini_provider.py    # Google Gemini Interactions API adapter tests
│   ├── test_hazard_adapter.py     # GEM hazard reader & synthetic GeoPackage unit tests
│   ├── test_hazard_api.py         # Public hazard API endpoints & correctness tests
│   ├── test_hazard_integration.py # Hazard models & idempotent import integration tests
│   ├── test_hazard_models.py      # HazardDataset & EarthquakeHazardPoint schema tests
│   ├── test_health.py
│   ├── test_osm_assembly_integration.py # OSM assembly models & idempotent import tests
│   ├── test_osm_assembly_models.py # AssemblyArea & Dataset schema & API boundary tests
│   ├── test_osm_assembly_reader.py # OSM JSON parser & geometry contract unit tests
│   └── test_osm_assembly_sanitizer.py # OSM tag allowlist & PII sanitizer unit tests
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

## Emergency Assembly Area Ingestion (OpenStreetMap Snapshot)

Emergency assembly areas are ingested from an authoritative, pre-captured **OpenStreetMap (OSM)** snapshot under the **ODbL 1.0** license:

- **Source**: OpenStreetMap
- **Data Provider**: OpenStreetMap contributors
- **Source Classification**: `community_open_data`
- **License**: Open Data Commons Open Database License 1.0 (ODbL 1.0)
- **Attribution**: `© OpenStreetMap contributors`
- **Source Reference**: [https://www.openstreetmap.org/copyright](https://www.openstreetmap.org/copyright)
- **Database Architecture**: Normalized two-table PostGIS schema:
  - `assembly_area_datasets`: Stores provenance, snapshot SHA-256 (`23b86cfc29f3...`), size (179,012 bytes), timestamps, Overpass extraction query, and source metadata.
  - `assembly_areas`: Stores individual assembly area features with `source_feature_id` (e.g. `node/123`, `way/456`), normalized `name`, `ref`, `operator`, PostGIS `GEOMETRY(Geometry, 4326)` (Point or Polygon), sanitized `source_properties` JSONB, `created_at`, and `updated_at`.
- **Idempotency & Integrity**: Bounded by `UNIQUE (source, snapshot_sha256)` on datasets and `UNIQUE (dataset_id, source_feature_id)` on features. Re-importing detects provenance and geometry/attribute drift, failing closed on unexpected mutations and safely no-oping on identical reruns.

```bash
# Run reproducible OSM snapshot importer:
python -m app.scripts.import_osm_assembly_areas --snapshot "<path-to-snapshot.json>"

# Example using authoritative local cache:
python -m app.scripts.import_osm_assembly_areas --snapshot "$env:LOCALAPPDATA\AFET360\assembly-cache\osm_turkey_emergency_assembly_point_20260904T084910Z.json"
```

### Key Operating & Semantic Principles
- **Snapshot-Based Ingestion**: The importer operates exclusively on pre-captured, checksum-verified local snapshots.
- **Zero Runtime Overpass Dependency**: Ingestion and application execution have no runtime or import-time network dependency on third-party public Overpass API endpoints.
- **Approved Snapshot Scope**: The current approved snapshot contains exactly **678 features** (650 nodes / Points, 28 closed ways / Polygons, 0 relations) across Türkiye.
- **Raw Snapshot Git Exclusion**: The raw JSON snapshot artifact remains strictly outside the Git repository in external cache storage (`%LOCALAPPDATA%\AFET360\assembly-cache\...`) to preserve repository hygiene.
- **Neutral Community Terminology & Non-Official Nature**: Assembly area data represents community-mapped gathering points (`emergency=assembly_point`) from OpenStreetMap. **This data is NOT official Turkish government / AFAD disaster gathering area data** (*"Afet ve Acil Durum Toplanma Alanları"*). It does not carry official emergency management verification, structural safety clearance, or safe-route guarantees.
- **Public API Exposure**: Public assembly-area API routes (`/api/v1/assembly-areas`, `/nearby`, `/dataset`) are fully operational with GeoJSON FeatureCollection serialization and spatial proximity queries.

## Current Phase

This repository currently represents **Phase 13: Comprehensive Backend Test Coverage + Final Public Contract Audit**.

At this stage:
- PostGIS database migrations (`0001` - `0005`) are fully applied and operational.
- Public Fault Lines GeoJSON API (`/api/v1/fault-lines`) is operational (4 endpoints).
- Public Earthquake GeoJSON & Proximity API (`/api/v1/earthquakes`) is operational (3 endpoints).
- Public Earthquake Hazard GeoJSON API (`/api/v1/earthquake-hazards`) is operational (3 endpoints).
- Public Emergency Assembly Area GeoJSON API (`/api/v1/assembly-areas`) is operational (3 endpoints).
- Public AI Preparedness Guide API (`/api/v1/ai/preparedness-guide`) is operational with Gemini integration (1 endpoint).
- Public Health API (`/api/v1/health`) is operational (1 endpoint, 15 total OpenAPI endpoints).
- API Security Foundation, sliding-window rate limiting, and request body size limiting (TASK 12) are fully active.
- GEM GSHM hazard dataset and 54,291 Türkiye-context hazard points are persisted and active.
- OpenStreetMap assembly area dataset provenance and 678 assembly features (650 Points, 28 Polygons) are persisted and verified.
- User authentication and persistent user accounts are intentionally omitted by architectural design.
