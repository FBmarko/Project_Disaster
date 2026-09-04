# ADR 0001: Geospatial and Earthquake Data Source Strategy

## Status
**Proposed** (Date: 2026-09-03)

## Context
AFET360 is an AI-assisted natural disaster preparedness and geospatial information web platform.
A core capability of AFET360 is providing interactive map visualization of:
1. Active fault lines across Türkiye
2. Recent and historical major earthquake events ($M \ge 5.0$)
3. Spatial proximity analysis between earthquake epicenters and mapped fault segments
4. Seismic hazard reference data

Before creating domain models and database tables, authoritative sources, licensing boundaries, data formats, and ingestion architectures must be formally established.

---

## Decisions

### 1. Active Fault Line Strategy: Two-Tier Development & Production Model

- **Development & Staging Fault Source**:
  - **Dataset**: **GEM Global Active Faults Database (GAF)**
  - **License**: **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**
  - **Rationale**: Provides verified machine-readable vector geometries (GeoJSON/Shapefile) under an open scientific license. Attribution must be displayed in UI and API responses. Must not be represented as official Turkish government data.
  - **Note on European Datasets**: EDSF13 is recognized as **deprecated** (its consortium recommends EFSM20 for current seismogenic knowledge) and is not selected.

- **Official Production Fault Target**:
  - **Dataset**: **MTA 2026 Türkiye Diri Fay Haritası**
  - **Reference**: Elmacı, H., Kürçer, A., Özalp, S., Altuntaş, G., Avcı, H.O., Aydoğan, H., Yüce, A.A., Öztürker, A.R., Karayazı, O., Bayrak, A., Özdemir, E., Çal, Ç., Güven, C., Yalvaç, O., 2026. *Türkiye Diri Fay Haritası*. Maden Tetkik ve Arama Genel Müdürlüğü, Özel Yayın Serisi-60, Ankara.
  - **Condition**: Use only if formal data rights and written licensing permission are procured from MTA Genel Müdürlüğü. Scraping or reverse-engineering the MTA web viewer is strictly prohibited.

### 2. Primary Earthquake Event Source: AFAD Event Web Service

- **Authority**: T.C. İçişleri Bakanlığı AFAD — Deprem Dairesi Başkanlığı
- **Official Service**: AFAD Event Web Service (`https://deprem.afad.gov.tr/apiv2/event/filter`)
- **Capabilities**: Supports filtering by `start`, `end`, `minmag`, `maxmag`, `magtype`, bounding box, radial distance, depth, and ordering.
- **Output Formats**: Natively supports JSON, GEOJSON, XML, CSV, and KML.
- **Ingestion Strategy**: Scheduled background ingestion into local PostgreSQL + PostGIS with event deduplication on `source_event_id`. Polling interval is configurable (with exponential backoff and timeout safeguards), to be finalized after observing AFAD rate-limit performance.
- **Timestamp Semantics**: Do not assume UTC without verification; catalog UI exposes UTC and local time (TSI). The ingestion worker will verify source timezone format before normalizing to timezone-aware UTC in PostgreSQL.

### 3. Earthquake Hazard Data Source: Two-Tier Development & Production Model

- **Status**: **PROPOSED / VALIDATED IN PHASE 8A** (See `backend/docs/earthquake-hazard-source-validation.md`)
- **Official Production Target**: **AFAD Türkiye Deprem Tehlike Haritası (TDTH)**
  - **Authority**: T.C. İçişleri Bakanlığı AFAD (Enacted via *Türkiye Deprem Tehlike Haritası ve Parametre Değerleri Hakkında Karar*, Decision No. 2018/11275, dated 22 January 2018, published in Resmî Gazete No. 30364 Mükerrer on 18 March 2018, effective 1 January 2019 under TBDY 2018).
  - **Findings**: Data is controlled by AFAD. As of the 2026-09-03 review, no publicly documented TDTH REST/WMS/WFS/WMTS or bulk hazard service was found in reviewed official AFAD/TUCBS channels. Legal notice explicitly requires written AFAD permission for electronic reproduction, distribution, or publication. Automated scraping is prohibited.
  - **Status & Access Path**: **CONDITIONAL / BLOCKED FOR REDISTRIBUTION WITHOUT WRITTEN PERMISSION**. Redistribution requires an official institutional protocol (e.g. via Coğrafi Veri Talep Portalı `cografiveri.gov.tr`). UI will provide direct links to `https://tdth.afad.gov.tr/` for official reports.
- **Development & Staging Source**: **GEM Global Seismic Hazard Map (GSHM v2026.1)**
  - **Authority**: Global Earthquake Model (GEM) Foundation.
  - **Verified Open Resource**: Zenodo artifact `gshm_v2026_1_vector.zip` (~935.5 MB). (Format/schema to be inspected prior to Phase 8B; software engine OpenQuake is AGPL-3.0).
  - **Dataset License**: **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)** (distinct from AGPL-3.0 engine license).
  - **Scientific Capabilities**: Continuous global coverage including Türkiye, assembled from multiple national/regional models. Exposes mean Peak Ground Acceleration (PGA) on reference rock ($V_{S,30} = 800\text{ m/s}$) for a nominal 10% exceedance in 50 years (~475-year return period). Shares the same nominal exceedance concept as AFAD DD-2, but datasets are NOT scientifically interchangeable.
  - **Status**: **APPROVED — NON-COMMERCIAL DEVELOPMENT / COMPETITION** under CC BY-NC-SA 4.0 conditions (attribution, non-commercial use, ShareAlike).

### 4. Spatial Proximity Association Methodology

- **Decision**: Strictly treat spatial association between earthquakes and fault lines as **geodesic proximity (`ST_Distance` on geography)**.
- **Configurable Boundary**: `max_distance_km` will be a configurable query parameter, not an arbitrary hardcoded constant.
- **Scientific Integrity**: Proximity must never be labeled as geological causation. Terminology is restricted to `"spatial_proximity"`, `"nearest_mapped_fault"`, and `"distance_to_fault_km"`, accompanied by clear non-causal disclaimers.

---

## Final Proposed Data Source Matrix

| Layer | Source Authority | Selected Dataset | License / Access Terms | Status |
|---|---|---|---|---|
| **Fault Lines (Dev/Staging)** | Global Earthquake Model (GEM) | GEM Global Active Faults Database (GAF) | CC BY-SA 4.0 (Open Data with Attribution) | **Selected & Implemented** |
| **Fault Lines (Production Target)** | MTA Genel Müdürlüğü | 2026 Türkiye Diri Fay Haritası (Özel Yayın No. 60) | All rights reserved; formal institutional licensing required | **Target pending license** |
| **Earthquake Events** | AFAD Deprem Dairesi | AFAD Event Web Service (`/apiv2/event/filter`) | Public web service with attribution; WAF/rate limits apply | **Selected & Implemented** |
| **Earthquake Hazard (Dev/Staging)** | Global Earthquake Model (GEM) | GEM Global Seismic Hazard Map (v2026.1) | CC BY-NC-SA 4.0 (Non-Commercial Open Data) | **APPROVED — NON-COMMERCIAL DEVELOPMENT / COMPETITION** |
| **Earthquake Hazard (Production Target)** | AFAD / TBDY 2018 | Türkiye Deprem Tehlike Haritası (TDTH) | Controlled; no open bulk API; formal institutional protocol required | **CONDITIONAL / BLOCKED WITHOUT WRITTEN PERMISSION** |

---

## Consequences & Next Steps
1. Phase 4 will introduce SQLAlchemy models (`FaultSegment`, `EarthquakeEvent`) and Alembic migrations with PostGIS GiST indexes without implementing hazard ingestion.
2. Coordinate order in all GeoJSON responses is strictly standard RFC 7946 `[longitude, latitude]`.
3. Ingestion adapters will verify timestamp timezone semantics and respect AFAD rate limits with backoff.
