# AFET360 Dataset Provisioning & Readiness Runbook

This document details the repeatable, non-destructive workflow for provisioning required non-migration datasets into a clean or production PostgreSQL/PostGIS database.

---

## 1. Architectural Principle: Schema vs. Dataset Provisioning

AFET360 strictly decouples database schema management from application dataset ingestion:

1. **Schema Provisioning (Alembic)**:
   - Manages DDL, table structures, PostGIS geometry types, and spatial indexes (`idx_*_geometry`).
   - Run via: `alembic upgrade head`.
   - Results in a fully migrated database containing empty application tables.

2. **Dataset Provisioning (Explicit Operator Ingestion)**:
   - Populates domain datasets into the migrated schema.
   - **Never runs automatically on application startup** (FastAPI lifespan, Uvicorn start, or Docker CMD).
   - Executed explicitly by an operator or staging/CI runner using authoritative import commands or the unified provisioning CLI.

---

## 2. Dataset Classification & Provenance

| Dataset | Type | Source & Attribution | License | Local Artifact / Ingestion Requirement |
| :--- | :--- | :--- | :--- | :--- |
| Dataset | Type | Source & Attribution | License | Local Artifact / Ingestion Requirement |
| :--- | :--- | :--- | :--- | :--- |
| **Active Faults** | **Static** | Global Earthquake Model Foundation (GEM GAF) | CC BY-SA 4.0 | Local GeoJSON file or automated GitHub download via `--download-faults`. Spatial filter uses committed Natural Earth 1:50m boundary (`backend/data/turkey_boundary.geojson`). |
| **Seismic Hazard** | **Static** | GEM Global Seismic Hazard Map (GSHM v2026.1) | CC BY-NC-SA 4.0 | Local GeoPackage (`gem_gshm_v2026.1.gpkg`) or automated download from official Zenodo repository via `--download-hazard` (Zenodo DOI: 10.5281/zenodo.20735384). Streamed and MD5-verified into `backend/data/cache/hazard/`. |
| **Assembly Areas** | **Static** | OpenStreetMap (OSM) contributors via Overpass API | ODbL 1.0 | Approved Overpass JSON snapshot or automated live fetch via `--download-assembly` querying canonical Overpass API (`https://overpass-api.de/api/interpreter`). Stored in `backend/data/cache/assembly/`. |
| **Earthquake Catalog** | **Dynamic** | AFAD (Disaster and Emergency Management Authority) | Official Research Attribution | Dynamic rolling 10-year window ($M \ge 4.5$). Synced explicitly via network API using system TLS certificate verification; not bundled as a static file. |

---

## 3. Operator CLI Interface: `provision_datasets.py`

AFET360 provides a unified entrypoint for inspecting readiness and provisioning static datasets:

```bash
python -m app.scripts.provision_datasets --help
```

### 3.1 Inspect Dataset Status (Read-Only)

Inspect the presence, provenance metadata, geometry validity, and row counts of all datasets:

```bash
# Human-readable console status
python -m app.scripts.provision_datasets status

# Machine-readable JSON output (for automated orchestration)
python -m app.scripts.provision_datasets status --json

# Strict exit code check (exits 0 if all static datasets are ready; 1 if any is missing)
python -m app.scripts.provision_datasets status --check
```

**Guarantees:**
- Strictly read-only: executes only `SELECT` queries with zero database writes.
- Semantic readiness: verifies metadata existence, $>0$ records, valid PostGIS geometries, and EPSG:4326 SRID.
- Does **not** hardcode permanent historical row counts (e.g. `== 722` or `== 54291`) as rigid schema constraints.

### 3.2 Provision Static Datasets (`provision-static`)

Provision one, two, or all three static datasets in an explicit, controlled run:

```bash
# Option A: Full reproducible clean-machine automated download & ingestion
python -m app.scripts.provision_datasets provision-static --download-all

# Option B: Selective automated network downloads
python -m app.scripts.provision_datasets provision-static \
    --download-faults \
    --download-hazard \
    --download-assembly

# Option C: Offline / Pre-staged local artifacts
python -m app.scripts.provision_datasets provision-static \
    --faults-file /path/to/gem_active_faults.geojson \
    --faults-scope turkey-only \
    --gshm-gpkg /path/to/gem_gshm_v2026.1.gpkg \
    --assembly-snapshot /path/to/osm_assembly_areas.json
```

**Failure Safety & Non-Destructive Behavior:**
- Pre-execution validation: validates local file existence before launching database operations.
- Streaming & Cache Reuse: GSHM (~935 MB archive, extracts to ~1.76 GB GeoPackage) and OSM downloads stream to `.part` files under `backend/data/cache/` (gitignored). MD5 and SHA-256 checksums are verified before promotion. Valid cached files are automatically reused on subsequent runs.
- Non-destructive: **never** executes `TRUNCATE`, `DROP TABLE`, or `DELETE FROM`.
- Idempotent: delegates directly to existing authoritative services (`FaultImportService`, `HazardImportService`, `AssemblyImportService`) which implement conflict-free upsert / skip semantics.
- Non-zero exit: halts immediately on any import failure and returns a non-zero exit code without falsely reporting readiness.

---

## 4. Fresh Clean-Machine Provisioning Sequence

When setting up AFET360 on a new laptop or staging environment:

### Step 1: Initialize Database & Run Schema Migrations
```bash
# Ensure PostgreSQL with PostGIS extension is running
# From the backend/ directory:
alembic upgrade head
```

### Step 2: Check Initial Dataset Status
```bash
python -m app.scripts.provision_datasets status
# Expected: Schema present, datasets show [NOT READY]
```

### Step 3: Provision Static Datasets (Automated Download & Ingestion)
```bash
# Downloads official GEM faults, Zenodo GSHM hazard, and OSM Overpass assembly points
python -m app.scripts.provision_datasets provision-static --download-all
```

### Step 4: Synchronize Initial Earthquake Catalog (AFAD)
```bash
# Synchronize initial earthquake catalog (e.g. M >= 4.5 rolling window)
python -m app.scripts.sync_afad_earthquakes --min-magnitude 4.5 --scope turkey-context
```

### Step 5: Final Readiness Verification
```bash
python -m app.scripts.provision_datasets status --check
# Expected exit code: 0, Overall Readiness: READY
```

### Step 6: Start API Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 5. Failure Recovery & Troubleshooting

1. **Interrupted Ingestion**:
   - Re-running `provision-static` is safe and idempotent. Existing records with identical natural keys are preserved or updated without generating duplicate rows.
   - Any incomplete downloads in `backend/data/cache/*.part` are automatically discarded and re-streamed safely.
2. **Missing Input File**:
   - The CLI validates file paths upfront and exits with code 1 before modifying the database.
3. **AFAD TLS Trust**:
   - AFAD client uses Python's standard library `ssl.create_default_context()` to load system trust certificates while maintaining strict certificate and hostname verification. No insecure flags (`verify=False`) are permitted.
4. **Missing PostGIS Extension**:
   - Alembic migration `001_initial_postgis_schema.py` ensures `CREATE EXTENSION IF NOT EXISTS postgis`. Verify your PostgreSQL user has `SUPERUSER` or sufficient privileges to load extensions.
