# AFET360 Geospatial & Earthquake Data Architecture

## 1. Scope

This document defines the data architecture, authoritative data sources, licensing constraints, and technical design for AFET360's geospatial domain services:
- **Active Fault Lines**: MTA 2026 reference dataset and GEM development dataset
- **Earthquake Events & Major Earthquakes ($M \ge 5.0$)**: AFAD Event Web Service (`/apiv2/event/filter`)
- **Earthquake Hazard Reference Data**: AFAD Türkiye Deprem Tehlike Haritası (TDTH)
- **Spatial Association Methodology**: Non-causal geodesic proximity between epicenters and mapped fault traces
- **API Contracts & GeoJSON Specifications**: RFC 7946 compliant models for the React + TypeScript frontend map
- **Data Ingestion, Synchronization, and Storage Strategy**: PostgreSQL + PostGIS normalization

> [!IMPORTANT]
> **Scientific Integrity & Causality Disclaimer**:
> Spatial proximity between an earthquake epicenter and a mapped fault trace **does not establish geological or seismological causation**.
> Earthquakes nucleate at hypocentral depth (typically 5–30 km in the Anatolian plate), while mapped fault traces represent surface or sub-surface projections with variable 3D dip angles ($\Delta X = H / \tan \delta$).
> AFET360 terminology must strictly adhere to non-causal descriptors (e.g., *"nearby mapped fault"*, *"nearest fault segment"*, *"distance to nearest mapped trace"*), accompanied by explicit user-facing disclaimers, unless an authoritative agency or published focal mechanism explicitly attributes the rupture to a specific fault.

---

## 2. Authoritative Data Source Analysis

### Data Source Matrix

| Data Domain | Source Authority | Service / Endpoint | Machine-Readable Format | Access & Licensing Status | AFET360 Architecture Strategy |
|---|---|---|---|---|---|
| **Fault Lines (Official Production Target)** | Maden Tetkik ve Arama Genel Müdürlüğü (MTA) | [yerbilimleri.mta.gov.tr](https://yerbilimleri.mta.gov.tr) | Vector (GIS database) | All rights reserved by MTA. Electronic reproduction/distribution requires written permission. Original vector data available via institutional/paid procurement. | **Production Target**: Procure official vector dataset through formal application. No web scraping. |
| **Fault Lines (Development & Staging)** | GEM (Global Earthquake Model Foundation) | GEM Global Active Faults Database (GAF) | GeoJSON / Shapefile / Geopackage | Open Data (CC BY-SA 4.0). Requires attribution and ShareAlike for derivatives. | **Development/Staging**: Preferred open dataset. Expose source attribution clearly. Do not label as official Turkish data. |
| **Earthquake Events** | AFAD Deprem Dairesi Başkanlığı | [deprem.afad.gov.tr](https://deprem.afad.gov.tr) (`/apiv2/event/filter`) | Native JSON, GEOJSON, XML, CSV, KML | Public web service. Attribution required (*AFAD Deprem Dairesi*). Rate limiting and WAF active. | **Ingestion Source**: Scheduled background ingestion into PostgreSQL + PostGIS with event deduplication. |
| **Earthquake Hazard** | AFAD / TBDY 2018 | [tdth.afad.gov.tr](https://tdth.afad.gov.tr) | Calculation grid (PGA, PGV, $S_s, S_1$) | Controlled by AFAD. Legal notice restricts unauthorized distribution/publication. No documented anonymous bulk REST API. | **Status: UNRESOLVED**. Requires further authorization/review. No bulk scraping or ingestion in Phase 3/4. |

---

## 3. Active Fault-Line Data Source Analysis

### 3.1 Official Reference: MTA 2026 Türkiye Diri Fay Haritası
The current authoritative scientific and cartographic reference for active faults in Türkiye is:

> **Elmacı, H., Kürçer, A., Özalp, S., Altuntaş, G., Avcı, H.O., Aydoğan, H., Yüce, A.A., Öztürker, A.R., Karayazı, O., Bayrak, A., Özdemir, E., Çal, Ç., Güven, C., Yalvaç, O., 2026.**  
> *Türkiye Diri Fay Haritası.*  
> Maden Tetkik ve Arama Genel Müdürlüğü, Özel Yayın Serisi-60, Ankara.

*(Historical Context: The previous 1:1.250.000 scale series was published by Emre et al., 2013, Special Publication Series No. 30. The 2026 publication represents the current official standard).*

### 3.2 MTA Data Rights & Legal Notice
- **Ownership**: MTA Genel Müdürlüğü retains all intellectual property and data rights for the maps and figures displayed on the *Yerbilimleri Harita Görüntüleyicisi*.
- **Distribution & Permission**: According to MTA's legal notice, any electronic reproduction, digital republication, or distribution requires proper citation and prior written permission from MTA.
- **Original Vector Datasets**: MTA does not offer anonymous bulk vector GIS downloads (Shapefile/GeoJSON) via open APIs. Original vector datasets are made available through institutional request, formal protocol, or paid acquisition via MTA Döner Sermaye İşletmesi.
- **Scraping Prohibition**: AFET360 must **not** scrape, reverse-engineer, or intercept internal tile/vector layers from the `yerbilimleri.mta.gov.tr` web viewer.

### 3.3 GEM Global Active Faults Database (Development Dataset)
- **Role**: Preferred open-access dataset for development, testing, and staging environments.
- **License**: **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**.
- **Requirements**:
  - Full attribution to GEM Foundation and contributing researchers must be maintained in the UI and API responses.
  - Derivative database transformations must remain under ShareAlike terms.
  - GEM data must **not** be presented as "official Turkish government data". The UI and API must explicitly distinguish between MTA official traces and GEM open scientific traces.

### 3.4 European Fault Databases Note
- **EDSF13 (European Database of Seismogenic Faults 2013)**: Identified as **deprecated**. Its service explicitly recommends the updated **EFSM20 (European Fault-Source Model 2020)** for current seismogenic knowledge. EDSF13 is **not** recommended for AFET360.

---

## 4. AFAD Earthquake Event Web Service Analysis

### 4.1 Official Architecture & Endpoint
- **Authority**: T.C. İçişleri Bakanlığı AFAD — Deprem Dairesi Başkanlığı.
- **Official Endpoint**: `/apiv2/event/filter` (hosted on `https://deprem.afad.gov.tr`).
- **Base URL**: `https://deprem.afad.gov.tr/apiv2/event/filter`

### 4.2 Query Filter Concepts
The AFAD Event Web Service natively supports comprehensive query parameters:
- `start`: Start timestamp filter (e.g. `2026-01-01 00:00:00`).
- `end`: End timestamp filter.
- `minmag`: Minimum magnitude threshold (e.g., `minmag=5.0` for major events).
- `maxmag`: Maximum magnitude threshold.
- `magtype`: Magnitude scale filter (`Mw`, `ML`, `Md`, etc.).
- `minlat`, `maxlat`, `minlon`, `maxlon`: Geographic bounding box coordinates (WGS84).
- `lat`, `lon`, `maxradius`: Radial geographic search around a center coordinate.
- `mindepth`, `maxdepth`: Focal depth range in kilometers.
- `orderby`: Result ordering (e.g., `time`, `time-asc`, `magnitude`, `magnitude-asc`).
- `limit`: Maximum count of returned records.
- `offset`: Pagination offset.
- `eventid`: Direct lookup by AFAD event identifier.

### 4.3 Native Output Format Support
AFAD natively supports multiple output formats via query parameter or Accept header:
- **JSON**
- **GEOJSON**
- **XML**
- **CSV**
- **KML**

> [!NOTE]
> AFET360 is not required to manually convert AFAD responses from JSON to GeoJSON; native GeoJSON from AFAD may be consumed directly when helpful. However, for internal persistence, indexing, and spatial joins with fault lines, AFET360 normalizes incoming events into its own PostGIS `EarthquakeEvent` schema.

### 4.4 Timestamp and Timezone Semantics
- AFAD's public catalog interfaces display origin times in both UTC and Turkish Local Time (TSI, UTC+3).
- **Architecture Rule**: AFET360 must **not** assume incoming timestamps are UTC without verification. The ingestion adapter must inspect the format string (e.g., presence of `Z` or offset), document the source timezone, and normalize to UTC only upon verified parsing.
- PostgreSQL storage will use timezone-aware timestamps: `DateTime(timezone=True)`.

---

## 5. AFAD Earthquake Hazard Data (TDTH) Analysis

- **System**: Türkiye Deprem Tehlike Haritaları İnteraktif Web Uygulaması ([tdth.afad.gov.tr](https://tdth.afad.gov.tr)).
- **Legal Framework**: Enacted under the Turkish Building Earthquake Code (TBDY 2018; Official Gazette No. 30364, 18 March 2018).
- **Verified Status**:
  - The hazard dataset is owned and controlled by AFAD.
  - AFAD's legal notice restricts unauthorized reproduction, distribution, or digital publication.
  - No documented, open, anonymous bulk REST API for the continuous national calculation grid exists.
  - Programmatic and bulk redistribution rights remain **unresolved**.
  - AFET360 will **not** scrape private interfaces or bypass authentication mechanisms.
- **Classification**: **UNRESOLVED / REQUIRES FURTHER AUTHORIZATION OR OFFICIAL DATA ACCESS REVIEW**. Hazard data ingestion will not be implemented in Phase 4.

---

## 6. Proposed Domain Models (Design Only)

### 6.1 `FaultSegment` Model Concept
```python
class FaultSegment(Base):
    """Mapped fault segment geometry and geological metadata."""

    __tablename__ = "fault_segments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "MTA_2026" or "GEM_GAF"
    source_id: Mapped[str | None] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(
        String(200), index=True, nullable=False
    )  # Fault system/zone name
    segment_name: Mapped[str | None] = mapped_column(String(200))
    fault_type: Mapped[str | None] = mapped_column(
        String(100)
    )  # e.g., "Strike-Slip", "Normal", "Thrust"
    activity_status: Mapped[str | None] = mapped_column(
        String(100)
    )  # "Holocene", "Quaternary"
    geometry: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="MULTILINESTRING", srid=4326),
        nullable=False,
    )
    source_reference: Mapped[str] = mapped_column(
        String(255)
    )  # Citation / publication reference
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
```

### 6.2 `EarthquakeEvent` Model Concept
```python
class EarthquakeEvent(Base):
    """Seismic event record synchronized from authoritative monitoring networks."""

    __tablename__ = "earthquake_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(
        String(50), default="AFAD", nullable=False
    )
    source_event_id: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    geometry: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=False,
    )
    depth_km: Mapped[float] = mapped_column(Float, nullable=False)
    magnitude: Mapped[float] = mapped_column(Float, index=True, nullable=False)
    magnitude_type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # "Mw", "ML", "Md"
    location_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Derived AFET360 metadata (not claimed as raw AFAD source fields)
    is_major: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True
    )  # Derived: magnitude >= 5.0
    province_derived: Mapped[str | None] = mapped_column(
        String(100), index=True
    )
    district_derived: Mapped[str | None] = mapped_column(String(100))

    # Ingestion metadata
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
```

---

## 7. Major Earthquake ($M \ge 5.0$) Architecture

1. **Catalog Filtering**:
   - AFET360 utilizes AFAD's native filter (`minmag=5.0`) to ingest and isolate major events.
   - Incoming events with `magnitude >= 5.0` are classified with `is_major = True` to accelerate query performance.
2. **Scientific Magnitude Handling**:
   - Event listings must **always expose `magnitude_type`** (`Mw`, `ML`, `Md`).
   - The UI can present the consumer feature as *"Magnitude 5.0 and above earthquakes"*, but the API and UI must clearly indicate the magnitude scale used (e.g. $5.2\text{ M}_\text{w}$ or $5.0\text{ M}_\text{L}$) without implying all seismic scales are mathematically or physically equivalent.

---

## 8. Fault-Earthquake Spatial Association Methodology

### 8.1 Non-Causal Proximity Design
- Research confirms that **no universal distance threshold exists** that proves fault rupture causation purely from 2D coordinates.
- Therefore, **no hardcoded distance cutoff (such as 20 km) will be enforced as a scientific boundary**.
- Instead:
  - The API exposes `max_distance_km` as a **configurable query parameter**.
  - Any default radius chosen by the frontend is treated strictly as a **visualization/display limit**, never as a causality proof.
  - Association results return:
    - `association_type = "spatial_proximity"`
    - `nearest_fault_name`
    - `distance_to_fault_km`
    - Mandatory non-causal disclaimer.

### 8.2 PostGIS Geodesic Calculations
Spatial distance is evaluated geodesically on the WGS84 spheroid using PostGIS `geography`:
```sql
-- Nearest mapped fault query template
SELECT
    f.id AS nearest_fault_id,
    f.name AS fault_name,
    f.segment_name,
    f.fault_type,
    ROUND((ST_Distance(e.geometry::geography, f.geometry::geography) / 1000.0)::numeric, 2) AS distance_to_fault_km
FROM fault_segments f
ORDER BY f.geometry::geography <-> e.geometry::geography
LIMIT 1;
```

---

## 9. Proposed API Contracts

### 9.1 `GET /api/v1/earthquakes/recent-major`
- **Description**: Returns recent major earthquakes ($M \ge 5.0$) with nearest mapped fault proximity.
- **Parameters**: `limit` (default: 20, max: 100), `days` (default: 30), `max_distance_km` (default: 25.0, configurable).
- **Response**:
```json
{
  "count": 1,
  "filter": {
    "min_magnitude": 5.0,
    "days": 30,
    "max_distance_km": 25.0
  },
  "disclaimer": "Deprem merkez üssü ile fay hattı arasındaki mesafe yalnızca coğrafi yakınlığı ifade eder ve depremin ilgili fay üzerinde gerçekleştiğini kanıtlamaz.",
  "items": [
    {
      "id": "c3d4e5f6-7890-4abc-def1-234567890abc",
      "source_event_id": "612345",
      "occurred_at": "2026-08-15T14:32:10Z",
      "magnitude": 5.3,
      "magnitude_type": "Mw",
      "depth_km": 10.4,
      "location_name": "Malatya - Yeşilyurt",
      "coordinates": [38.2541, 38.3125],
      "nearest_mapped_fault": {
        "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
        "name": "Doğu Anadolu Fay Zonu",
        "segment_name": "Erkenek Segmenti",
        "distance_to_fault_km": 6.8,
        "association_method": "spatial_proximity"
      }
    }
  ]
}
```

### 9.2 `GET /api/v1/fault-lines/{fault_id}/earthquakes`
- **Description**: Lists earthquakes spatially proximate to a specific fault segment.
- **Parameters**: `min_magnitude` (default: 5.0), `max_distance_km` (configurable, default: 20.0, max: 100.0), `limit` (default: 50).
- **Response**:
```json
{
  "fault": {
    "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
    "name": "Kuzey Anadolu Fay Zonu",
    "segment_name": "Gölcük Segmenti",
    "fault_type": "Doğrultu Atımlı (Sağ Yanal)",
    "source": "GEM_GAF"
  },
  "search_parameters": {
    "min_magnitude": 5.0,
    "max_distance_km": 20.0,
    "association_method": "spatial_proximity"
  },
  "disclaimer": "Bu listedeki depremler fay hattına belirtilen yarıçap dahilinde mekânsal olarak yakın olan sarsıntıları gösterir. Nedensellik ilişkisi içermez.",
  "earthquakes": [
    {
      "id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "source_event_id": "598712",
      "occurred_at": "2026-04-10T08:12:00Z",
      "magnitude": 5.1,
      "magnitude_type": "Mw",
      "depth_km": 8.5,
      "location_name": "Kocaeli - Gölcük",
      "distance_to_fault_km": 4.3,
      "coordinates": [29.8821, 40.7154]
    }
  ]
}
```

---

## 10. GeoJSON Standards for Frontend Map (RFC 7946)

> [!CAUTION]
> **Coordinate Order Standard**: All coordinates must strictly adhere to `[longitude, latitude]` format (X, Y in WGS84 / EPSG:4326).
> Placing latitude first is non-compliant with RFC 7946 and will invert geometries.

### `GET /api/v1/fault-lines`
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "geometry": {
        "type": "MultiLineString",
        "coordinates": [
          [
            [29.8512, 40.7123],
            [29.9214, 40.7245],
            [30.0142, 40.7389]
          ]
        ]
      },
      "properties": {
        "name": "Kuzey Anadolu Fay Zonu",
        "segment_name": "Gölcük Segmenti",
        "fault_type": "Strike-Slip",
        "activity_status": "Holocene",
        "source": "GEM_GAF",
        "source_license": "CC BY-SA 4.0"
      }
    }
  ]
}
```

---

## 11. Spatial Index Strategy

Alembic migrations will define the following PostGIS GiST and B-tree indexes:
1. `CREATE INDEX idx_fault_segments_geom ON fault_segments USING GIST (geometry);`
2. `CREATE INDEX idx_earthquake_events_geom ON earthquake_events USING GIST (geometry);`
3. `CREATE INDEX idx_earthquakes_mag_time ON earthquake_events (magnitude DESC, occurred_at DESC);`
4. `CREATE INDEX idx_earthquakes_major ON earthquake_events (is_major, occurred_at DESC);`

---

## 12. Earthquake Synchronization Strategy

### Architecture: Configurable Scheduled Background Synchronization
- **No Hardcoded Interval**: The polling interval will be defined via `Settings` (e.g., `EARTHQUAKE_SYNC_INTERVAL_SECONDS`, default: 300 seconds), finalized after evaluating AFAD rate-limit characteristics.
- **Resilience Features**:
  - Incremental polling using `start` timestamp based on last successful ingestion.
  - Deduplication enforced by PostgreSQL `UNIQUE INDEX on source_event_id`.
  - Exponential backoff on connection timeout or HTTP error (e.g. initial 10s, max 300s).
  - Rate-limit & WAF compliance: User-Agent identification and conservative query limits.
  - Source timestamp verification and timezone-aware normalization.

---

## 13. Implementation Roadmap

1. **Phase 4**: Domain models (`FaultSegment`, `EarthquakeEvent`) & Alembic migrations with GiST spatial indexes.
2. **Phase 5**: Seed pipeline for GEM Active Faults open vector dataset with proper attribution.
3. **Phase 6**: Robust AFAD Event synchronization service with deduplication, backoff, and logging.
4. **Phase 7**: REST & GeoJSON API endpoints (`/fault-lines`, `/earthquakes`, `/earthquakes/recent-major`, proximity joins).
5. **Phase 8**: React + TypeScript frontend map integration.
