# GEM GSHM v2026.1 Artifact Verification, Grid Characterization, and PostgreSQL/PostGIS Ingestion (Phase 8B)

**Status:** Implemented & Verified Foundation Document (Phase 8B-1, Phase 8B-2, and Phase 8B-3)<br>
**Date:** 2026-09-04<br>
**Context:** AFET360 Natural Disaster Information & Preparedness Web Platform<br>
**Branch:** `feature/backend-hazard-ingestion`

---

## 1. Executive Summary & Status Classification

This document records the complete research, verification, schema design, and operational implementation for the **GEM Global Seismic Hazard Map (v2026.1)** within AFET360.

All findings and implementation components are organized into explicit categories:

### A. VERIFIED (Empirically Measured & Implemented in Phase 8B)
- **Official Artifact:** `gshm_v2026_1_vector.zip` (935,540,326 bytes).
- **Cryptographic Checksum:** MD5 `7470e54534f4a4307a7310aa766ab11b` (verified against Zenodo record in 1.2s).
- **Extracted GeoPackage Size:** `gem_gshm_v2026.1.gpkg` is exactly **1,761,116,160 bytes**.
- **Coordinate Reference System:** **EPSG:4326** (WGS 84 2D geographic coordinates).
- **Spatial Layer / Table:** `"v2026"`.
- **Geometry Type:** **`POINT`** (2D WKB Point geometry in column `"geom"`).
- **Spatial Indexing:** **GeoPackage RTree index `rtree_v2026_geom` exists and is registered in `gpkg_extensions`**.
- **Exact Global Row Count:** **`14,117,882` rows** (queried in 5.45s).
- **Exact Global Extents:** Longitude `[-179.999990°, +179.999959°]`, Latitude `[-89.977200°, +89.977200°]`.
- **Global Data Quality:** 0 coordinate nulls, 0 out-of-bounds coordinates, 0 PGA nulls, 0 negative PGA, 0 zero PGA. Global PGA range: `[0.001000 g, 3.349810 g]`.
- **Exact Türkiye-Context Row Count:** **`54,291` rows** for bbox $[24.0^\circ\text{E}..46.0^\circ\text{E}, 34.0^\circ\text{N}..44.0^\circ\text{N}]$.
- **Türkiye Data Quality:** 0 nulls, 0 negative, 0 zeros, **0 duplicate (lon, lat) pairs**. PGA range: `[0.020443 g, 0.767226 g]` (mean: `0.209288 g`).
- **Measured Point Spacing:** Representative nearest-neighbor spacing across Türkiye ranges from **~6.47 km to 6.90 km** (mean ~6.65 km).
- **Broad Bbox Coverage:** All 220 individual $1^\circ \times 1^\circ$ degree bins in the $22^\circ \times 10^\circ$ bbox are populated with source points.
- **Implemented Database Models:** `HazardDataset` and `EarthquakeHazardPoint` managed via Alembic migration `0004_create_hazard_tables`.
- **First Live Import Performance:** Ingested 54,291 rows in **8.83 seconds** (**6,145 rows/second**).
- **Second Live Idempotent Import Performance:** Verified 54,291 unchanged rows (0 inserted, 0 conflicts) in **1.81 seconds** (**29,982 rows/second**).
- **Measured PostgreSQL Storage:** Table `7.13 MB`, Indexes `8.31 MB`, Total `15.11 MB` ("15 MB").
- **PostGIS GiST Index Participation:** Confirmed via EXPLAIN (`Index Scan using idx_earthquake_hazard_points_geometry`).
- **Data Integrity Validation:** Zero geometry mismatches (`ST_X(geom) == lon` and `ST_Y(geom) == lat`), zero coordinate nulls, zero out-of-bounds values.
- **Regression Conservation:** `fault_segments = 722`, `earthquake_events = 84` conserved with zero corruption or modification.

### B. PROPOSED (Architecture for TASK 09 Public API)
- **Future Geodesic Nearest-Node Query Architecture:** Two-stage query combining degree GiST candidate retrieval with exact geodesic re-ranking via `ST_Distance(geom::geography, query_point::geography) ORDER BY distance LIMIT 1`.
- **Public Disclosures:** Mandatory display of source node coordinates, modeled PGA in $g$, geodesic distance in km, and non-causal reference rock disclaimers.

### C. UNRESOLVED (Deferred Beyond Ingestion Foundation)
- **Formal Mesh Topology / Cell Geometry:** The source contains discrete POINT records without polygonal or cell definitions.
- **Nearest-Node Acceptance / Distance Cutoff:** No arbitrary cutoff (such as 10 km or 15 km) is hardcoded into persistence. Public query acceptance semantics will be finalized in TASK 09.

---

# PART I: SOURCE CHARACTERIZATION & VALIDATION

## 2. Provenance & Checksum Verification

- **Official Title:** Global Seismic Hazard Map (version 2026.1)
- **Publisher:** Global Earthquake Model (GEM) Foundation (Pavia, Italy)
- **Version DOI:** **`10.5281/zenodo.20735384`** (Primary identifier for the exact ingested artifact)
- **Concept / Family DOI:** **`10.5281/zenodo.8409646`** (Dataset family identifier across all versions)
- **Download URL:** `https://zenodo.org/api/records/20735384/files/gshm_v2026_1_vector.zip/content`
- **External Cache Location:** `%LOCALAPPDATA%\AFET360\hazard-cache\` (outside Git repository)
- **Downloaded File:** `gshm_v2026_1_vector.zip`
- **Exact File Size:** `935,540,326` bytes
- **Integrity Checksum:** MD5 `7470e54534f4a4307a7310aa766ab11b` (verified in 1.2s; used solely for artifact integrity matching against Zenodo metadata, not as a security primitive).

## 3. ZIP Security & Selective Extraction

The local ZIP archive contains exactly 7 entries:
1. `gshm_v2026_1_vector/` (directory, 0 B)
2. `gshm_v2026_1_vector/gshm-v2026_1-epsg3857.sld` (16,618 B)
3. `gshm_v2026_1_vector/gshm-v2026_1.cpt` (381 B)
4. `gshm_v2026_1_vector/gshm-v2026_1-epsg3857.qml` (59,220 B)
5. `gshm_v2026_1_vector/gem_gshm_v2026.1.gpkg` (1,761,116,160 B)
6. `gshm_v2026_1_vector/README.txt` (2,784 B)
7. `gshm_v2026_1_vector/LICENSE-CC_BY-NC-SA.txt` (20,850 B)

All members were audited against path traversal, absolute paths, and executables. Extracted selectively to external cache; verified extracted GeoPackage size: exactly **`1,761,116,160` bytes**.

## 4. GeoPackage Metadata & Spatial Indexing Analysis

- Table `"v2026"` DDL:
  ```sql
  CREATE TABLE "v2026" (
      "fid" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
      "geom" POINT,
      "lon" REAL,
      "lat" REAL,
      "pga" REAL
  );
  ```
- **CRS:** EPSG:4326 (WGS 84).
- **Spatial Index:** GeoPackage virtual table `rtree_v2026_geom` is present and indexed in `gpkg_extensions`. No B-tree indexes exist on `lon`/`lat`.
- **RTree Extraction Efficiency:** Querying through `rtree_v2026_geom` subquery completes in **0.144s** (direct RTree scan in **0.003s**), avoiding a 14.12M row table scan.

## 5. Point Distribution & Spatial Sampling Characterization

- **Non-Rectilinear Point Mesh Structure:** The source does **not** use an axis-aligned rectilinear grid in EPSG:4326.
- **Grid-Delta Reality:** *"No single constant $\Delta\text{lon}/\Delta\text{lat}$ defines the source point distribution in EPSG:4326."* Across the 54,291 Türkiye points, there are 54,291 unique latitude values.
- **Measured Nearest-Neighbor Spacing:**
  - 36°N (Mediterranean): `min = 6.80 km, max = 6.90 km, avg = 6.83 km`
  - 39°N (Central Anatolia): `min = 6.60 km, max = 6.77 km, avg = 6.63 km`
  - 42°N (Black Sea): `min = 6.47 km, max = 6.63 km, avg = 6.51 km`
  - Mean spacing across Türkiye: **~6.65 km**.
- **Coverage Status:** **`BROAD COVERAGE VERIFIED; FINE-GRAINED GAP-FREE TOPOLOGY NOT PROVEN`**. All 220 individual $1^\circ \times 1^\circ$ degree bins in the $22^\circ \times 10^\circ$ bbox are populated with source points (min: 227, max: 283, avg: 246.8 points per bin).

---

# PART II: IMPLEMENTED POSTGRESQL/POSTGIS INGESTION

## 6. Database Architecture & Alembic Migration 0004

### 6.1 Schema Implementation
Implemented in `app/models/hazard_dataset.py` and `app/models/earthquake_hazard_point.py`:

```sql
CREATE TABLE hazard_datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(50) NOT NULL,
    source_version VARCHAR(20) NOT NULL,
    model_name VARCHAR(150) NOT NULL,
    hazard_metric VARCHAR(20) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    return_period_years INTEGER NOT NULL,
    exceedance_probability DOUBLE PRECISION NOT NULL,
    time_horizon_years INTEGER NOT NULL,
    reference_vs30_mps DOUBLE PRECISION NOT NULL,
    reference_ground VARCHAR(50) NOT NULL,
    version_doi VARCHAR(100) NOT NULL,
    concept_doi VARCHAR(100) NOT NULL,
    license VARCHAR(100) NOT NULL,
    attribution TEXT NOT NULL,
    source_artifact VARCHAR(100) NOT NULL,
    source_artifact_size_bytes BIGINT NOT NULL,
    source_checksum_algorithm VARCHAR(20) NOT NULL,
    source_checksum_value VARCHAR(64) NOT NULL,
    ingest_scope VARCHAR(50) NOT NULL,
    scope_min_longitude DOUBLE PRECISION NOT NULL,
    scope_min_latitude DOUBLE PRECISION NOT NULL,
    scope_max_longitude DOUBLE PRECISION NOT NULL,
    scope_max_latitude DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_hazard_datasets_natural_key UNIQUE (
        source, source_version, hazard_metric, return_period_years, ingest_scope
    )
);

CREATE TABLE earthquake_hazard_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL REFERENCES hazard_datasets(id) ON DELETE CASCADE,
    source_record_id BIGINT,
    longitude DOUBLE PRECISION NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    pga_g DOUBLE PRECISION NOT NULL,
    geometry GEOMETRY(Point, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_hazard_points_dataset_coords UNIQUE (dataset_id, longitude, latitude),
    CONSTRAINT chk_hazard_points_longitude CHECK (longitude >= -180.0 AND longitude <= 180.0),
    CONSTRAINT chk_hazard_points_latitude CHECK (latitude >= -90.0 AND latitude <= 90.0)
);

CREATE INDEX idx_earthquake_hazard_points_geometry ON earthquake_hazard_points USING GIST (geometry);
CREATE INDEX idx_earthquake_hazard_points_dataset_id ON earthquake_hazard_points (dataset_id);
```

### 6.2 Alembic Migration Status
- Migration: `0004_create_hazard_tables`
- Parent Revision: `0003_create_earthquake_events`
- Status: **`0004_create_hazard_tables (head)`**
- Full downgrade and upgrade roundtrip verified cleanly.

## 7. Importer Implementation & Operational Behavior

### 7.1 Integration Components
- `app/integrations/gem/hazard_constants.py`: Scientific constants and verified artifact specifications.
- `app/integrations/gem/hazard_reader.py`: GeoPackage metadata validator and streaming RTree point generator.
- `app/repositories/earthquake_hazard.py`: SQLAlchemy Core bulk insertion and coordinate lookup caching.
- `app/services/hazard_import.py`: Idempotent orchestration and conflict detection.
- `app/scripts/import_gem_hazard.py`: Developer CLI tool.

### 7.2 Idempotency & Conflict Semantics
- **Identity Key:** `UNIQUE (dataset_id, longitude, latitude)`.
- **First Import:** Inserts all 54,291 valid points into PostgreSQL.
- **Second Import:** Reuses existing `HazardDataset`, checks existing coordinates, reports 54,291 unchanged records, inserts 0, raises 0 conflicts.
- **Interrupted Import:** Recovers cleanly by identifying missing coordinates and inserting only the unpersisted points.
- **Conflict Handling:** If an incoming record has identical coordinates to an existing point but a differing PGA value ($>10^{-4}$), a `ValueError` is raised immediately.

## 8. Live Ingestion Measurements & Benchmarks

Executed on local PostgreSQL/PostGIS environment using external cache:

| Metric | First Import (Clean Run) | Second Import (Idempotent Run) |
|---|---|---|
| **Source Rows Processed** | 54,291 | 54,291 |
| **Rows Inserted** | 54,291 | **0** |
| **Rows Unchanged** | 0 | **54,291** |
| **Conflicts** | 0 | 0 |
| **Total Ingestion Time** | **8.83 seconds** | **1.81 seconds** |
| **Throughput** | **6,145 rows/sec** | **29,982 rows/sec** |
| **Database Total for Dataset** | 54,291 | 54,291 |

## 9. Live Database Integrity & Storage Footprint

### 9.1 Data Quality Validation
- `hazard_datasets` count: **1**
- `earthquake_hazard_points` count: **54,291**
- Duplicate coordinate pairs: **0**
- Coordinate & PGA null counts: **0**
- Out-of-bounds coordinates: **0**
- Observed PGA range: `min = 0.020443 g`, `max = 0.767226 g`, `avg = 0.209288 g`
- Coordinate consistency: **0 mismatches** between PostGIS geometry (`ST_X`, `ST_Y`) and numeric table columns (`longitude`, `latitude`).

### 9.2 Measured Storage Footprint
Measured via PostgreSQL administrative functions:
- `pg_relation_size('earthquake_hazard_points')`: `7,299,072` bytes (**7.13 MB**)
- `pg_indexes_size('earthquake_hazard_points')`: `8,511,488` bytes (**8.31 MB**)
- `pg_total_relation_size('earthquake_hazard_points')`: `15,843,328` bytes (**15.11 MB / ~15 MB**)

### 9.3 PostGIS GiST Index Verification
EXPLAIN query confirms active GiST index participation:
```text
Limit  (cost=0.28..66.43 rows=5 width=40)
  ->  Index Scan using idx_earthquake_hazard_points_geometry on earthquake_hazard_points  (cost=0.28..719136.17 rows=54351 width=40)
        Order By: (geometry <-> '0101000020E6100000CDCCCCCCCC6C4040D7A3703D0AF74340'::geometry)
```

## 10. Automated Testing & Regression Safety

### Test Suite Results:
- `tests/test_hazard_models.py`: 4 passed (model fields, unique constraints, check constraints)
- `tests/test_hazard_adapter.py`: 5 passed (archive verification, schema validation, synthetic streaming)
- `tests/test_hazard_integration.py`: 6 passed (table creation, idempotency, partial rerun, conflict detection, geometry consistency, database conservation)
- **Full backend test suite:** **104 passed** in 3.36s (100% passing).
- **Regression Conservation:** Live development database preserved intact:
  - `fault_segments = 722`
  - `earthquake_events = 84`
  - `hazard_datasets = 1`
  - `earthquake_hazard_points = 54,291`

## 11. External Cache Confirmation
- Path: `C:\Users\muham\AppData\Local\AFET360\hazard-cache`
- Retained: `gshm_v2026_1_vector.zip` (935.5 MB) and `gem_gshm_v2026.1.gpkg` (1.76 GB)
- Total size on disk: ~2.70 GB (zero bytes inside Git repository).

## 12. Scope Boundary for TASK 09
- Phase 8B-3 completes the database model, Alembic migration, and ingestion pipeline.
- Public API endpoint (`/api/v1/earthquake-hazards`) is **NOT** exposed in Phase 8B-3.
- Public nearest-node queries and API schemas are strictly designated for TASK 09.
