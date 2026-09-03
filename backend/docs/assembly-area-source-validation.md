# AFET360 — Assembly Area Data Source Validation and Geospatial Architecture (TASK 10A)

**Research Date:** 2026-09-04
**Status:** VALIDATED / ARCHITECTURE SPECIFICATION
**Target Milestone:** TASK 10B (Split into TASK 10B-1 Characterization and TASK 10B-2 Implementation)

---

## 1. Executive Summary & Problem Context

AFET360 aims to provide disaster-affected citizens and emergency responders with immediate geospatial discovery of **emergency assembly areas** (*"Afet ve Acil Durum Toplanma Alanları"*). Following an earthquake, designated open public spaces (parks, school quadrangles, sports grounds, public squares) serve as temporary gathering points immediately after shaking ceases to avoid structural collapse, falling facade hazards, and panicking crowds before formal evacuation to relief shelter areas (*"geçici barınma alanları / çadırkentler"*).

### Critical Safety & Product Semantics
1. **No False Official Authority:** The platform must never present community-mapped or unofficial points as official AFAD-certified gathering zones unless derived from an authorized official registry.
2. **No Guaranteed Safety Claims:** Proximity does not equate to real-time safety. A physically nearest assembly area may be inaccessible due to road blockages, fallen utility lines, damaged retaining walls, or localized hazards. The system must display clear non-causal discovery language (*"nearby mapped assembly areas"*), not *"safest area"* or *"recommended evacuation route"*.
3. **Public Product Naming:** For OpenStreetMap records, neutral terminology must be used:
   - English: *"community-mapped emergency assembly points"*
   - Turkish: *"OSM'de işaretlenmiş acil durum toplanma noktaları"*
   - The phrase *"AFAD Toplanma Alanları"* must **never** be used for OSM-derived records.
4. **Engineering Anti-Scraping Policy:** AFET360 maintains a strict engineering policy:
   - **DO NOT** scrape e-Devlet.
   - **DO NOT** bypass authentication.
   - **DO NOT** automate CAPTCHA.
   - **DO NOT** reverse-engineer hidden or private endpoints.
   - **DO NOT** capture or reuse private session tokens.

---

## 2. Research Findings by Candidate Source

### A. Official AFAD & e-Devlet Source
- **Official Service:** AFAD provides the citizen-facing inquiry service via the e-Devlet Kapısı:
  `https://www.turkiye.gov.tr/afad-acil-toplanma-alani-sorgulama`
  and inside the mobile application *"AFAD Acil"*.
- **API Availability:** **NOT PUBLICLY DOCUMENTED / UNRESOLVED**. No publicly documented machine-readable national assembly-area REST API, WFS, WMS, or bulk dataset was identified in the reviewed official AFAD channels as of the research date.
- **Bulk Download:** No open national GeoJSON, Shapefile, or CSV bulk archive exists for unauthenticated public download.
- **Access Architecture:** e-Devlet provides an interactive citizen lookup web service requiring form parameters (İl, İlçe, Mahalle, Cadde/Sokak) or real-time device location, protected by Türksat security controls and user session cookies.
- **Rights & Licensing Findings:** No explicit open-data redistribution license suitable for AFET360 bulk ingestion was identified for the national AFAD/e-Devlet assembly-area service in the reviewed official sources.
- **Verdict:** **BLOCKED FOR UNCREDENTIALED INGESTION**. Ingestion of official AFAD data requires a formal bilateral institutional protocol (*"e-Devlet Yazılım Entegrasyonu için Siber Güvenlik İsterleri"*).

### B. Türkiye Ulusal Coğrafi Bilgi Sistemi (TUCBS) & National Open Data
- **Platform:** TUCBS Portal (`tucbs.gov.tr`) and Ulusal Coğrafi Bilgi Platformu (UCBP - `ucbp.tucbs.gov.tr`), coordinated by the Ministry of Environment, Urbanisation and Climate Change (Çevre, Şehircilik ve İklim Değişikliği Bakanlığı).
- **Layer Catalog:** TUCBS catalogues a spatial theme:
  `"AADVS - ACİL DURUM TOPLANMA ALANLARI"`.
- **Access Status:** TUCBS contains and coordinates geospatial data sharing under the Coğrafi Veri Paylaşım Matrisi (*"TUCBS Veri Paylaşım Matrisi"*). Public access depends on each layer's restriction classification and the data owner's permissions. A publicly downloadable, openly licensed national AADVS dataset suitable for AFET360 ingestion was not verified in the reviewed public interfaces.
- **National Open Data Portal (`veri.gov.tr`):** Does not publish a national assembly-area dataset as of the research date.
- **Verdict:** **NOT PUBLICLY DOWNLOADABLE**. Requires institutional data-sharing protocols.

### C. Municipal Open Data Portals
Investigated representative major metropolitan municipalities:

1. **Istanbul Metropolitan Municipality (İBB - `data.ibb.gov.tr`):**
   - No open assembly-area dataset is published on `data.ibb.gov.tr`. Municipal portals redirect citizens to AFAD's e-Devlet service.
2. **Ankara Metropolitan Municipality (ABB - `acikveri.ankara.bel.tr`):**
   - No emergency assembly area dataset is indexed or published on the portal.
3. **İzmir Metropolitan Municipality (İzBB - `acikveri.bizizmir.com`):**
   - **Dataset Title:** *"Afet ve Acil Durum Toplanma Alanları"* (created 2020-11-09, updated 2026-08-07).
   - **Publisher:** İzBB Akıllı Şehir ve Kent Bilgi Sistemleri Dairesi Başkanlığı.
   - **Documented Machine-Readable Resources:** API (`https://openapi.izmir.bel.tr/api/ibb/cbs/afetaciltoplanmaalani`), CSV (`https://openfiles.izmir.bel.tr/100104/docs/izbb-afet-ve-acil-durum-toplanma-alanlari.csv`), and XLSX formats exist on the portal.
   - **License:** Portal terms state that materials are licensed under **Creative Commons Attribution 4.0 International (CC BY 4.0)** unless otherwise stated.
   - **Update Frequency:** *düzensiz* (irregular).
   - **Geographic Scope:** Strictly localized to İzmir metropolitan boundaries (not national).
   - **Technical Reachability Note:** While machine-readable resources are officially published on the portal, specific download host subdomains (`openfiles.izmir.bel.tr`, `openapi.izmir.bel.tr`) may experience external DNS resolution or network reachability variations depending on external client network routing.
- **Verdict:** Verified as a strong, authorized municipal alternative under CC BY 4.0, but geographically limited to İzmir. Retained as a validation benchmark for comparing community features against an official municipal baseline.

### D. OpenStreetMap (OSM) — Semantic Fitness & Licensing Analysis

#### 1. Critical Semantic Limitations & Broader Meaning
- The OpenStreetMap tag **`emergency=assembly_point`** does **NOT** equate to *"official Turkish AFAD disaster gathering area"* and does **NOT** exclusively represent neighborhood-scale disaster areas.
- Official OSM documentation describes `emergency=assembly_point` broadly as a designated place or area where people such as employees, passengers, or crowds gather during an emergency, evacuation, or fire drill (including office building courtyards, school fire muster points, industrial staging areas, and airport assembly areas).
- Newer OSM community proposals explore civil-protection / waiting-area tags to distinguish large-scale disaster gathering grounds from localized facility muster points; however, these proposals are not established OSM standards.
- **Architectural Conclusion:** `emergency=assembly_point` alone is semantically broader than AFET360's earthquake disaster-preparedness concept. Therefore, the measured count of **678 features** in the Türkiye snapshot must strictly be interpreted as *"678 OSM features tagged emergency=assembly_point in the measured Türkiye snapshot"*, not as 678 official or certified earthquake evacuation grounds.

#### 2. Supplemental Disaster-Suitability Tags
OSM documents supplemental tags indicating suitability for specific disaster types:
- `assembly_point:earthquake=*` (`yes` / `no`)
- `assembly_point:fire=*` (`yes` / `no`)
- `assembly_point:flood=*` (`yes` / `no`)
- `assembly_point:tsunami=*` (`yes` / `no`)

**Important Tri-State Interpretation Rules:**
1. `assembly_point:earthquake=yes` records that the contributor explicitly tagged the location as intended for earthquake use.
2. **Absence of `assembly_point:earthquake=yes` does NOT mean unsuitable for earthquakes.** It simply indicates that the contributor did not supply that metadata. Missing tags must be treated as `UNKNOWN`, never coerced to `false`.
3. Even when `assembly_point:earthquake=yes` or `operator=AFAD` is present on an OSM record, the feature remains **`community_open_data`**. It must never be presented as AFAD-certified or government-approved without external verification against an official registry.

#### 3. License Terms & Allowed Use
- OpenStreetMap data is openly usable under the **Open Data Commons Open Database License (ODbL) 1.0**, subject to attribution and applicable database/share-alike obligations.
- The OpenStreetMap Foundation (OSMF) states that OSM data may be used for personal, community, educational, commercial, and governmental purposes under ODbL terms.
- Therefore, AFET360 university competition use is **compatible in principle**.
- **Licensing Position:** License compatibility in principle is **not** completed compliance. Full compliance requires fulfilling attribution, license notices, logical dataset separation, and machine-readable database access obligations in TASK 10B and upon public deployment.
- ODbL must **never** be described as "unencumbered", "no-restrictions", "license-free", or "public domain".

#### 4. Systematic / Substantial Extraction Analysis
- The measured Türkiye snapshot contains ~678 features tagged `emergency=assembly_point`.
- The planned extraction is systematic: retrieving all matching assembly-point features across the national territory of Türkiye.
- Under OSMF's Substantial guideline, while one-off small queries (<100 features) are typically insubstantial, systematic extraction of all features of a category across an entire nation is conservatively classified as:
  > *"Treat the AFET360 Türkiye assembly-area extraction as potentially / likely substantial for ODbL compliance purposes."*

#### 5. Public API & Derivative Database Implications
- Because AFET360 stores and exposes machine-readable OSM-derived assembly-point records through a public GeoJSON REST API (rather than solely rendering a static map image), TASK 10B must satisfy ODbL database attribution, share-alike, and public-use access requirements rather than relying only on Produced Work attribution:
  > *"Because AFET360 stores and exposes machine-readable OSM-derived assembly-point records, TASK 10B should satisfy the ODbL database attribution/share-alike/public-use requirements rather than relying only on Produced Work attribution."*

#### 6. Türkiye Empirical Coverage (Overpass Snapshot — 2026-09-03)
- **Measurement Details:**
  - Snapshot timestamp: `2026-09-03T21:59:36Z`
  - Overpass instance: `https://overpass-api.de/api/interpreter`
  - Query: `area["ISO3166-1"="TR"][admin_level=2] -> (node["emergency"="assembly_point"]; way["emergency"="assembly_point"]; relation["emergency"="assembly_point"];)`
- **Feature Breakdown:**
  - **Nodes (Points):** 650
  - **Ways:** 28
  - **Relations:** 0
  - **Total Features:** **678**
- **Way Polygon-Verification Status:** The snapshot contains 650 node features and 28 way features. Polygon closure and area validity for all 28 ways must be verified during TASK 10B-1 artifact inspection before treating them as polygonal geometries. Valid areas will be stored as actual polygons, never degraded to centroids.
- **Completeness & Coverage Limitations:** 678 OSM features across 81 provinces (~85M population) indicates **severe geographic sparsity**. Mapped points are clustered primarily in select districts of Istanbul, Izmir, Ankara, and post-2023 earthquake recovery zones. The absence of an assembly point on the map does NOT indicate absence of an official area on the ground.

---

## 3. Ingestion & Runtime Architecture

### Runtime Overpass Evaluation
**Public Overpass is not selected as AFET360's production/runtime dependency.**

Reasons for this architectural decision:
1. **Availability:** Public Overpass instances do not offer guaranteed availability or high-availability SLAs.
2. **Server Load & Latency:** Public servers may become overloaded, resulting in variable response latency (800 ms to 30,000 ms).
3. **Rate & Resource Limits:** Fair-use rate limits (HTTP 429) and request queue constraints apply to public instances.
4. **Offline Demo Reliability:** University competition presentations require deterministic, zero-network-latency local execution.
5. **Architectural Separation:** Production user queries should be served directly from local PostgreSQL/PostGIS with sub-millisecond query execution.

### Overpass Ingestion Role
Using a public Overpass instance for a **controlled, one-time or periodic developer snapshot extraction** is acceptable within that instance's acceptable use policy. No live Overpass call will be executed during user API requests.

---

## 4. Source Priority & Provenance Model

The platform defines a 3-tier provenance classification:

```
[1. Official Government] (AFAD / TUCBS / e-Devlet)
         │ (Target pending formal institutional data-sharing protocol)
         ▼
[2. Municipal Open Data] (İzmir Açık Veri Portalı CC BY 4.0)
         │ (Verified local municipal fallback)
         ▼
[3. Community Open Data] (OpenStreetMap - ODbL 1.0)
           (Approved for TASK 10B-1 Characterization)
```

### Source Separation & Collective Database Architecture
- The database architecture is intentionally designed to keep OSM-derived, municipal, and future official source datasets **logically separable**, which may support Collective Database treatment where applicable. Final ODbL Collective-vs-Derivative classification depends on the actual combination and public deployment and must be reviewed before release.
- **No Automatic Cross-Source Merging:** Community datasets (OSM) and future official/municipal datasets will **never** be silently merged or deduplicated into a single derived dataset.
- Each record retains its explicit `dataset_id`, `source`, `provider`, `source_classification`, `license`, and `attribution`.
- ODbL obligations apply specifically to the OSM-derived dataset and do not automatically expand to unrelated official data.
- Source classification is strictly determined at the dataset level and is never inferred from user-submitted `operator` tags.

---

## 5. TASK 10B ODbL Compliance Checklist

This checklist tracks requirements across project phases:

| Requirement | Implementation Target | Compliance Status |
|---|---|---|
| **A. Dataset License Storage** | `assembly_area_datasets.license = 'ODbL 1.0'` | **REQUIRED / PLANNED FOR TASK 10B-2** |
| **B. Attribution Preservation** | `attribution = '© OpenStreetMap contributors'` | **REQUIRED / PLANNED FOR TASK 10B-2** |
| **C. Legal Reference Exposure** | Link to `https://www.openstreetmap.org/copyright` | **REQUIRED / PLANNED FOR TASK 10B-2** |
| **D. Documentation Attribution** | Record OSM provenance in `backend/README.md` | **REQUIRED / PLANNED FOR TASK 10B-2** |
| **E. Frontend Visible Attribution** | Display OSM attribution in map UI viewport | **REQUIRED BEFORE PUBLIC DISPLAY** |
| **F. Logical Dataset Separation** | Isolate OSM records from other data sources | **COMPLETED RESEARCH DECISION / PLANNED FOR TASK 10B-2** |
| **G. No Proprietary Relicensing** | Retain open ODbL terms on OSM-derived DB | **COMPLETED RESEARCH DECISION** |
| **H. Machine-Readable Access Plan** | Provide reproducible snapshot / export method | **REQUIRED BEFORE PUBLIC DEPLOYMENT** |
| **I. Final Deployment Review** | Verify all deployment licensing obligations | **REQUIRED BEFORE PUBLIC DEPLOYMENT** |

### Machine-Readable ODbL Access Strategy (for Public Deployment)
If AFET360 publicly distributes or publicly exposes an OSM-derived Derivative Database, the applicable database must remain available under ODbL terms. The planned compliance strategy:
1. Retain ODbL 1.0 on the OSM-derived assembly-area dataset.
2. Provide required attribution and clear ODbL license references.
3. Preserve the exact Overpass extraction query, snapshot timestamp, and transformation pipeline for complete reproducibility.
4. Provide a machine-readable copy/export of the applicable OSM-derived assembly-area database upon public deployment when required.
5. Publishing source code or extraction queries alone does not automatically satisfy all ODbL obligations; final deployment review is strictly **REQUIRED**.

---

## 6. Phased Execution Strategy for TASK 10B

To ensure rigorous data verification before creating database schemas or importers, TASK 10B is split into two sequential phases:

### Phase 1: TASK 10B-1 — OSM Türkiye Snapshot Characterization
Before implementing models or migrations, TASK 10B-1 will capture ONE reproducible Türkiye snapshot and perform complete structural and semantic characterization:
1. **Feature Totals:** Exact count of `emergency=assembly_point` nodes, ways, and relations.
2. **Way Geometry Verification:** Verify polygon closure for all 28 ways (closed vs open, valid polygon-capable vs problematic).
3. **Disaster Suitability Tag Counts:** Quantify presence of:
   - `assembly_point:earthquake` (`yes` / `no` / missing)
   - `assembly_point:fire` (`yes` / `no` / missing)
   - `assembly_point:flood` (`yes` / `no` / missing)
   - `assembly_point:tsunami` (`yes` / `no` / missing)
4. **Metadata Field Inventory:** Quantify presence of `name`, `ref`, `operator`, `access`, `capacity`, and `check_date`.
5. **Generic vs Disaster-Specific Classification:** Inspect representative records using transparent source-tag rules to categorize features into:
   - A. Generic building / facility muster points (e.g. office courtyards, school fire drill points)
   - B. Community-mapped public emergency gathering spaces
   - C. Explicitly earthquake-tagged assembly points
   - D. Other disaster-specific assembly points
   - Unclassifiable records will be categorized as `UNKNOWN / GENERIC OSM ASSEMBLY POINT`. No opaque AI guesswork will be used.
6. **Earthquake Filter Evaluation:** Determine whether `assembly_point:earthquake=yes` has sufficient coverage to support an earthquake-specific API filter.

### Phase 2: TASK 10B-2 — Persistence, Importer, and GeoJSON API
Based on TASK 10B-1 findings:
1. Author Alembic migration `0005_create_assembly_area_tables`.
2. Define SQLAlchemy models `AssemblyAreaDataset` and `AssemblyArea`.
3. Implement an idempotent snapshot importer with sanitization (stripping personal contact info).
4. Implement read-only REST endpoints (`GET /assembly-areas`, `GET /assembly-areas/nearby`, `GET /assembly-areas/{id}`).

---

## 7. Proposed Data Model Architecture (for TASK 10B-2)

### Table 1: `assembly_area_datasets`
```sql
CREATE TABLE assembly_area_datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(64) NOT NULL,              -- e.g. 'OSM'
    provider VARCHAR(128) NOT NULL,            -- e.g. 'OpenStreetMap Contributors'
    source_classification VARCHAR(32) NOT NULL,-- 'community_open_data' | 'municipal_open_data' | 'official_government'
    dataset_version VARCHAR(64),              -- e.g. '2026-09-03T21:59:36Z'
    license VARCHAR(64) NOT NULL,             -- e.g. 'ODbL 1.0'
    attribution TEXT NOT NULL,                -- e.g. '© OpenStreetMap contributors'
    source_reference TEXT NOT NULL,           -- e.g. 'https://www.openstreetmap.org/copyright'
    coverage_description TEXT NOT NULL,       -- e.g. 'Türkiye national community sample'
    retrieved_at TIMESTAMPTZ NOT NULL,
    source_updated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Table 2: `assembly_areas`
```sql
CREATE TABLE assembly_areas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL REFERENCES assembly_area_datasets(id) ON DELETE CASCADE,
    source_feature_id VARCHAR(128) NOT NULL,  -- e.g. 'node/123456' or 'way/876543'
    name VARCHAR(256),                        -- e.g. 'Demokrasi Parkı Toplanma Alanı'
    description TEXT,
    province VARCHAR(64),
    district VARCHAR(64),
    neighborhood VARCHAR(128),
    address TEXT,
    capacity INTEGER,
    -- Tri-state suitability flags (yes=TRUE, no=FALSE, unknown=NULL)
    earthquake_suitability BOOLEAN,           -- NULL indicates UNKNOWN (missing tag)
    fire_suitability BOOLEAN,
    flood_suitability BOOLEAN,
    tsunami_suitability BOOLEAN,
    geometry GEOMETRY(Geometry, 4326) NOT NULL, -- Point or Polygon in WGS84
    source_properties JSONB,                  -- Retained raw tags for audit (not publicly dumped)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_assembly_areas_source_feature UNIQUE (dataset_id, source_feature_id)
);

CREATE INDEX idx_assembly_areas_geometry ON assembly_areas USING GIST (geometry);
CREATE INDEX idx_assembly_areas_dataset_id ON assembly_areas (dataset_id);
```

### Geometry & Distance Semantics
- **Geometry Storage:** `GEOMETRY(Geometry, 4326)` stores both 2D `Point` and closed `Polygon` geometries.
- **Geodesic Distance Semantics:**
  ```sql
  ST_Distance(geometry::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) / 1000.0 AS distance_km
  ```
  - For `Point`: calculates exact spheroidal distance from query point to source node.
  - For `Polygon`: PostGIS calculates the minimum distance to the nearest polygon boundary edge; a coordinate situated inside the assembly polygon returns `0.0 km`.
  - Polygon centroid distance will **not** be used, as it misrepresents the nearest edge of large parks or sports complexes.

---

## 8. Privacy & PII Safeguards

- Assembly areas represent designated public parks, squares, stadium grounds, and schoolyards.
- During ingestion, raw source attributes must be sanitized to strip:
  - Personal phone numbers (`phone`, `contact:phone`)
  - Personal contact names and email addresses
  - Caretaker or building supervisor notes
- Only public administrative descriptors (`name`, `ref`, `addr:*`, `operator`) and spatial geometries are ingested into core columns.

---

## 9. Proposed API Surface (for TASK 10B-2)

1. **`GET /api/v1/assembly-areas`**
   - Query Parameters: `bbox` (min_lon, min_lat, max_lon, max_lat), `limit` (default 100, max 500), `offset` (default 0).
   - Response: RFC 7946 GeoJSON FeatureCollection with pagination metadata.
2. **`GET /api/v1/assembly-areas/nearby`**
   - Query Parameters: `lat`, `lon`, `radius_km` (default: **UNRESOLVED**, max: **UNRESOLVED**; to be established after data density benchmarks in TASK 10B-1), `limit`.
   - Response: GeoJSON FeatureCollection sorted by geodesic distance, with `distance_km` in properties.
   - **Important:** Radius caps represent query bounds to protect server performance; they must never be described as "safe evacuation walking distances".
3. **`GET /api/v1/assembly-areas/{id}`**
   - Response: Single GeoJSON Feature with complete dataset provenance and metadata.

### Non-Causal Safety Disclaimers
Every API response will include:
> *"Mapped assembly areas represent community-mapped emergency assembly points. Proximity does not imply real-time safety, structural safety of surrounding buildings, or open route conditions during an active disaster. Data is community/open-source; verify official AFAD/e-Devlet emergency announcements."*

### Routing Boundary
- **Discovery only:** Route optimization, street debris analysis, and turn-by-turn navigation are strictly out of scope for TASK 10.

---

## 10. Final Source Decision for TASK 10

1. **Primary TASK 10B Source:**
   **OpenStreetMap (`emergency=assembly_point`)**
   - Classification: `community_open_data`
   - License: ODbL 1.0
   - Status: **Approved as the TASK 10B-1 source for controlled snapshot characterization and as a potential community-data source for TASK 10B-2, subject to semantic fitness findings and ODbL compliance controls.**
2. **Verified Municipal Alternative:**
   **İzmir Büyükşehir Belediyesi (*"Afet ve Acil Durum Toplanma Alanları"* )**
   - Classification: `municipal_open_data`
   - License: CC BY 4.0 (portal terms)
   - Status: Retained as an authorized municipal candidate for future regional expansion and cross-comparison.
3. **Official National Target:**
   **AFAD / TUCBS National Assembly Area Registry**
   - Classification: `official_government`
   - Status: No openly redistributable national machine-readable dataset is currently available through reviewed public interfaces. Target pending formal institutional data-sharing protocol.
