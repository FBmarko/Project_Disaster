# ADR 0002: Disaster Assembly Area Data Source and Architecture

## Status
**Proposed** (Date: 2026-09-04)

## Context
AFET360 requires a geospatial capability enabling citizens and emergency responders to discover nearby **emergency assembly areas** (*"Afet ve Acil Durum Toplanma Alanları"*). Following an earthquake, designated open public spaces (parks, school quadrangles, sports grounds, public squares) serve as vital temporary gathering points immediately after shaking ceases before formal evacuation to relief shelters (*"geçici barınma alanları / çadırkentler"*).

Before implementing database models, migrations, and APIs in TASK 10B, authoritative sources, licensing terms, accessibility boundaries, semantic fitness, and geospatial data architectures must be established.

---

## Decision Drivers
1. **Legal & Licensing Compliance:** Data must be legally distributable for development, non-commercial research, and university competition presentations without copyright infringement.
2. **Access Security & Anti-Scraping Policies:** The platform must strictly avoid scraping interactive government services (e-Devlet) or bypassing authentication tokens.
3. **National vs Local Scope:** The solution should provide geographic distribution across Türkiye rather than being confined to a single municipality.
4. **Offline & Demo Reliability:** Ingestion must not introduce runtime network dependencies on third-party public services (e.g. Overpass API) during end-user requests.
5. **Semantic Fitness & Non-Causal Semantics:** The system must recognize that OpenStreetMap `emergency=assembly_point` is semantically broader than official AFAD disaster gathering areas, explicitly disclaiming route safety and real-time operational guarantees.

---

## Evaluated Options

### Option A: Official National Government Source (AFAD / e-Devlet / TUCBS)
- **Status:** **NOT PUBLICLY DOCUMENTED / UNRESOLVED FOR UNCREDENTIALED BULK INGESTION**.
- **Findings:** AFAD operates an interactive citizen inquiry service on e-Devlet (`turkiye.gov.tr/afad-acil-toplanma-alani-sorgulama`) and inside the *AFAD Acil* mobile app. No publicly documented national REST API, WFS/WMS endpoint, or downloadable bulk archive was identified in reviewed official channels. No explicit open-data redistribution license suitable for AFET360 bulk ingestion was identified. TUCBS coordinates geospatial data sharing under the Coğrafi Veri Paylaşım Matrisi; a publicly downloadable, openly licensed national AADVS dataset was not verified in reviewed public interfaces.
- **Verdict:** Requires an official bilateral institutional data-sharing protocol. Blocked for immediate automated ingestion.

### Option B: Municipal Open Data Portals (e.g. İzmir Açık Veri Portalı)
- **Status:** **LEGALLY PERMISSIVE (CC BY 4.0), BUT GEOGRAPHICALLY ISOLATED**.
- **Findings:** İzmir Metropolitan Municipality publishes a verified gathering area dataset (*"Afet ve Acil Durum Toplanma Alanları"*) with API, CSV, and XLSX resources licensed under CC BY 4.0. However, coverage is strictly limited to İzmir province. Istanbul (İBB) and Ankara (ABB) do not publish open machine-readable assembly area datasets.
- **Verdict:** High-quality authorized municipal data under CC BY 4.0, but cannot fulfill AFET360's national scope requirement. Retained as an authorized municipal candidate for future regional expansion and benchmark validation.

### Option C: OpenStreetMap (OSM) as Open Development / Community Source
- **Status:** **APPROVED FOR TASK 10B-1 CHARACTERIZATION SUBJECT TO SEMANTIC FITNESS AND ODBL CONTROLS**.
- **Findings:** OSM uses standardized emergency tagging (`emergency=assembly_point`). Distributed across Türkiye under the **Open Data Commons Open Database License 1.0 (ODbL 1.0)**, subject to attribution and applicable database/share-alike obligations.
- **Semantic Nuance:** `emergency=assembly_point` broadly designates gathering points for emergencies, evacuations, or fire drills (including facility/office muster points). It is broader than AFAD disaster gathering areas.
- **Compliance Position:** The OpenStreetMap Foundation (OSMF) permits use for personal, educational, community, commercial, and governmental purposes under ODbL terms. University competition use is compatible in principle. Systematic extraction of all assembly points across Türkiye (~678 features in the measured snapshot) is treated conservatively as potentially/likely substantial. Because AFET360 exposes machine-readable records via a public GeoJSON REST API, TASK 10B will satisfy ODbL database attribution and public-use/share-alike access obligations rather than relying solely on Produced Work attribution.

---

## Decisions

### 1. Phased Execution Strategy for TASK 10B
To address semantic breadth and data quality before writing persistence code, TASK 10B is split into two sequential phases:
1. **TASK 10B-1: OSM Türkiye Assembly-Point Snapshot Characterization**
   - Capture ONE reproducible snapshot from Overpass.
   - Characterize exact feature counts, node vs way distribution, and polygon closure for all 28 ways.
   - Quantify supplemental disaster suitability tags (`assembly_point:earthquake`, `fire`, `flood`, `tsunami`).
   - Categorize features into generic building muster points vs public emergency gathering areas using transparent source-tag rules (no opaque AI guessing).
   - Evaluate whether earthquake-specific filtering is viable.
2. **TASK 10B-2: Assembly-Area Persistence, Importer, and GeoJSON API**
   - Implement Alembic migration `0005_create_assembly_area_tables`.
   - Implement idempotent snapshot importer with PII sanitization.
   - Implement read-only REST endpoints with exact geodesic distance queries.
   - Implement required ODbL attribution and machine-readable data access controls.

### 2. Multi-Source Normalized Architecture & Data Separation
- The database schema is intentionally designed to keep OSM-derived, municipal, and future official source datasets **logically separable**, which may support Collective Database treatment where applicable. Final ODbL Collective-vs-Derivative classification depends on the actual combination and public deployment and must be reviewed before release.
- Community datasets (OSM) and future official/municipal datasets will **never** be silently merged or deduplicated into a single derived dataset.
- Each record retains its explicit `dataset_id`, `source`, `provider`, `source_classification`, `license`, and `attribution`.

### 3. Ingestion & Runtime Isolation (No Live Overpass Dependency)
- Public Overpass is not selected as AFET360's production/runtime dependency due to variable response latency, public server load, fair-use rate limits, and offline competition requirements.
- Data ingestion will occur via a scripted offline/developer snapshot workflow that loads records into local PostgreSQL/PostGIS.
- End-user API endpoints will query local PostGIS tables with sub-millisecond execution times and 100% offline demo reliability.

### 4. Geometry & Geodesic Distance Semantics
- Source geometries will be stored as PostGIS `GEOMETRY(Geometry, 4326)` to accommodate both Point (650 features) and closed Polygon ways (28 features).
- Proximity queries will utilize exact spheroidal distance (`ST_Distance` on geography in kilometers) with secondary tie-breaking on unique `id`.
- For Polygon features, distance is the minimum distance to the polygon boundary (points inside return `0.0 km`); centroid distance will not be used.

### 5. Non-Causal Safety & Discovery Semantics
- Responses will strictly use neutral discovery terminology: *"community-mapped emergency assembly points"* (*"OSM'de işaretlenmiş acil durum toplanma noktaları"*).
- System disclaimers will explicitly clarify that physical proximity does not guarantee structural safety, open access, or official AFAD certification.
- Default and maximum search radius values remain **UNRESOLVED** until data density and performance benchmarks are conducted in TASK 10B-1.
- Routing, evacuation navigation, and road closure analysis are strictly excluded from TASK 10.

---

## Data Source Matrix Update

| Layer | Source Authority | Selected Dataset | License / Access Terms | Status |
|---|---|---|---|---|
| **Fault Lines (Dev/Staging)** | Global Earthquake Model (GEM) | GEM Global Active Faults (GAF) | CC BY-SA 4.0 | Implemented |
| **Fault Lines (Production Target)** | MTA Genel Müdürlüğü | 2026 Türkiye Diri Fay Haritası | All rights reserved; institutional license required | Target pending license |
| **Earthquake Events** | AFAD Deprem Dairesi | AFAD Event Web Service | Public web service with attribution | Implemented |
| **Earthquake Hazard (Dev/Staging)** | GEM Foundation | GEM GSHM (v2026.1) | CC BY-NC-SA 4.0 | Implemented |
| **Earthquake Hazard (Production Target)** | AFAD / TBDY 2018 | Türkiye Deprem Tehlike Haritası (TDTH) | Controlled; institutional protocol required | Target pending protocol |
| **Assembly Areas (Dev/Staging)** | OpenStreetMap Contributors | OSM `emergency=assembly_point` | ODbL 1.0 (subject to compliance controls) | **APPROVED FOR TASK 10B-1 CHARACTERIZATION** |
| **Assembly Areas (Municipal Target)** | İzmir Büyükşehir Belediyesi | İzBB Afet ve Acil Durum Toplanma Alanları | CC BY 4.0 | Verified municipal alternative |
| **Assembly Areas (Official Production Target)** | AFAD / e-Devlet | Afet ve Acil Durum Toplanma Alanı Sorgulama | Controlled; institutional protocol required | Target pending protocol |

---

## Consequences & Next Steps for TASK 10B
1. **TASK 10B-1 Characterization Completed:** Successfully acquired and verified a reproducible Türkiye snapshot (678 elements: 650 nodes, 28 closed-way valid PostGIS polygons, 0 relations; 0% disaster suitability tags; see `backend/docs/osm-assembly-point-snapshot-characterization.md`).
2. **Execute TASK 10B-2 Next:** Define models (`AssemblyAreaDataset`, `AssemblyArea`), author Alembic migration `0005_create_assembly_area_tables` with data-driven initial fields (`source_feature_id`, `name`, `ref`, `operator`, `geometry`, `source_properties`), build idempotent snapshot importer with allowlisted metadata and PII exclusion, and expose read-only REST endpoints with ODbL attribution and public-use access provisions.
