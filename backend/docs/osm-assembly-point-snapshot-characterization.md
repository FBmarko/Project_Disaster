# AFET360 — OSM Türkiye Emergency Assembly-Point Snapshot Characterization (TASK 10B-1)

**Characterization Date:** 2026-09-04
**Status:** COMPLETE / EMPIRICAL BASELINE
**Milestone:** TASK 10B-1 (Data Characterization Prior to Model/API Implementation)

---

## 1. Snapshot Acquisition & Manifest

A reproducible Türkiye-wide OpenStreetMap snapshot for `emergency=assembly_point` was acquired using a controlled Overpass API query.

### Overpass Query
```overpass
[out:json][timeout:180];

area
  ["ISO3166-1"="TR"]
  ["admin_level"="2"]
  ->.turkey;

(
  node["emergency"="assembly_point"](area.turkey);
  way["emergency"="assembly_point"](area.turkey);
  relation["emergency"="assembly_point"](area.turkey);
);

out body geom;
```

### Snapshot Manifest
| Property | Value |
|---|---|
| **Retrieval UTC Timestamp** | `2026-09-04T08:49:10.757167+00:00` |
| **Overpass Instance** | `https://overpass-api.de/api/interpreter` |
| **HTTP Status** | `200 OK` |
| **Content-Type** | `application/json` |
| **External Cache Path** | `%LOCALAPPDATA%\AFET360\assembly-cache\osm_turkey_emergency_assembly_point_20260904T084910Z.json` |
| **Raw Byte Size** | `179,012 bytes` (~174.8 KB) |
| **SHA-256 Checksum** | `23b86cfc29f30a47ca49c4e0037c4bcf914066870d06d234d53b64be2a46c340` |
| **JSON Validity** | `True` (strictly valid RFC 8259 JSON) |
| **Overpass API Version** | `0.6` |
| **Overpass Generator** | `Overpass API 0.7.62.11 87bfad18` |
| **OSM Data Timestamp (`timestamp_osm_base`)** | `2026-09-04T08:48:11Z` |
| **OSM Areas Timestamp (`timestamp_areas_base`)** | `2026-09-03T10:22:36Z` |
| **Licensing Notice in Payload** | *"The data included in this document is from www.openstreetmap.org. The data is made available under ODbL."* |

*(Note: Snapshot retrieval time `2026-09-04T08:49:10Z` is distinct from the underlying OSM database base timestamp `2026-09-04T08:48:11Z`).*

---

## 2. Element Inventory & Identity Integrity

### Element Counts
- **Total Elements:** **678** (matches preliminary count exactly; difference = 0)
- **Node Elements (Points):** **650** (95.87%)
- **Way Elements (Polygons):** **28** (4.13%)
- **Relation Elements:** **0** (0.00%)

### Identity Integrity
- Evaluated uniqueness of composite natural key `(type, id)` across all 678 elements.
- **Duplicate Identities:** **0** (100% unique natural element identities).
- Future source identity format `f"{type}/{id}"` (e.g. `node/5049895124`, `way/226421064`) is completely collision-free.

---

## 3. Coordinate & Geometry Characterization

### Node Coordinates
- **Missing Coordinates:** 0 (all 650 nodes provide valid `lat` and `lon`).
- **Invalid Coordinate Range:** 0 (all coordinates lie strictly within valid geographic bounds).
- **Node Coordinate Extents:**
  - Latitude: `[36.524818, 41.684354]`
  - Longitude: `[26.512911, 41.145864]`
  *(Note: Reflects spatial bounds of mapped assembly points; does not represent the constitutional boundaries of Türkiye).*

### Way Geometries & Polygon Validity
All 28 way elements were evaluated for geometry closure and PostGIS polygon validity:
- **Total Ways:** 28
- **Closed Ways:** **28 (100.0%)** (first coordinate equals last coordinate in all 28 ways).
- **Open Ways:** **0** (0.0%).
- **Degenerate Ways (<3 coordinates):** **0** (0.0%). Coordinate counts range from 5 to 15 nodes per way.
- **PostGIS Polygon Validity:**
  - Each closed way was converted into WKT `POLYGON` and evaluated using PostGIS `ST_IsValid()` and `ST_IsSimple()`:
  - **Valid Polygons:** **28 (100.0%)**
  - **Invalid / Problematic Polygons:** **0 (0.0%)**
  - All 28 closed ways represent simple, uncorrupted, non-self-intersecting polygonal areas (e.g. parks, open plazas, and facility grounds).
  - **Recommendation:** PostGIS `GEOMETRY(Geometry, 4326)` should preserve these 28 features as true `POLYGON` geometries rather than degrading them to centroids.

### Relations
- **Total Relations:** **0**. No multipolygon or relation-based assembly areas exist in the current Türkiye snapshot.

---

## 4. Complete Source Tag Inventory & Distribution

There are **33 unique tag keys** across the entire 678-element snapshot. The complete frequency inventory sorted deterministically by count descending, then key ascending:

| Tag Key | Feature Count | % of 678 | Category / Notes |
|---|---|---|---|
| `emergency` | 678 | 100.00% | Primary tag (`emergency=assembly_point`) |
| `name` | 492 | 72.57% | Public name of assembly space |
| `operator` | 332 | 48.97% | Managing or contributing entity |
| `source` | 251 | 37.02% | Source citation / municipal portal URL |
| `ref` | 119 | 17.55% | Official reference code / signboard ID |
| `name:en` | 39 | 5.75% | English translation of name |
| `leisure` | 9 | 1.33% | Associated land use (`park`, `sports_centre`) |
| `website` | 8 | 1.18% | Institutional / municipal website |
| `addr:housenumber` | 5 | 0.74% | Address house number |
| `addr:street` | 5 | 0.74% | Address street |
| `highway` | 4 | 0.59% | Linear association (`footway`) |
| `amenity` | 3 | 0.44% | Facility amenity (`parking`, etc.) |
| `building` | 3 | 0.44% | Associated building structure |
| `addr:city` | 2 | 0.29% | City name |
| `building:levels` | 2 | 0.29% | Building storeys |
| `building:units` | 2 | 0.29% | Building units |
| `description` | 2 | 0.29% | General text description |
| `addr:country` | 1 | 0.15% | Country code |
| `addr:district` | 1 | 0.15% | District name |
| `addr:neighbourhood` | 1 | 0.15% | Neighborhood name |
| `addr:postcode` | 1 | 0.15% | Postal code |
| `addr:province` | 1 | 0.15% | Province name |
| `addr:subdistrict` | 1 | 0.15% | Subdistrict name |
| `area` | 1 | 0.15% | Area indicator tag |
| `education` | 1 | 0.15% | Educational facility indicator |
| `fee` | 1 | 0.15% | Access fee (`fee=no`) |
| `height` | 1 | 0.15% | Physical height descriptor |
| `indoor` | 1 | 0.15% | Indoor indicator |
| `note` | 1 | 0.15% | Public mapping note |
| `opening_hours:emergency` | 1 | 0.15% | Emergency hours specification |
| `opening_hours:marketplace` | 1 | 0.15% | Market hours specification |
| `parking` | 1 | 0.15% | Parking lot type (`parking=surface`) |
| `shop` | 1 | 0.15% | Commercial shop indicator |

### Specifically Checked Attributes
- `access`: **0 (0.0%)** (completely unpopulated)
- `capacity`: **0 (0.0%)** (completely unpopulated)
- `check_date`: **0 (0.0%)** (completely unpopulated)

### Name & Ref Characteristics
- **Name Presence:** 492 features (72.57%) have a `name` tag.
  - **Unique Names:** 191
  - **Duplicate Names:** 301. Highly repetitive generic Turkish emergency naming:
    - `"Geçici Toplanma Alanı"`: 232 occurrences
    - `"Afet ve Acil Durum Toplanma Alanı"`: 19 occurrences
    - `"AFAD Toplanma Alanı"`: 18 occurrences
    - `"Acil Toplanma Alanı"`: 14 occurrences
    - Specific park / place names: e.g. `"Mehmet Bulur Parkı"`, `"Cevahir AVM Açık Otopark"`, `"Athletic Center"`.
  - **Missing Names:** 186 features (27.43%) have no name tag.
  - **Measured String Lengths (492 values):**
    - Min length: **7 characters**
    - Max length: **77 characters** (e.g. `"KARŞIYAKA İLÇESİ ŞEMİKLER MAHALLESİ 3 NO'LU AFET VE ACİL DURUM TOPLANMA ALANI"`)
    - Median length: **21.0 characters**
    - 95th percentile length: **41.0 characters**
- **Reference Code (`ref`) Presence:** 119 features (17.55%) have an official reference code:
  - **Unique Refs:** 113
  - **Duplicate Refs:** 6 (multi-node complexes sharing a signboard code).
  - Format matches Turkish municipal/AFAD numbering schemes (e.g. `5902-007-07`).
  - **Measured String Lengths (119 values):**
    - Min length: **1 character**
    - Max length: **21 characters** (e.g. `"Hacıevhat Mahallesi_2"`)
    - Median length: **11.0 characters**
    - 95th percentile length: **19.1 characters**

### Operator Characteristics
- 332 features (48.97%) have an `operator` tag, covering 8 distinct values:
  - `TBB`: 250 features (sourced from *Tekirdağ Büyükşehir Belediyesi Afet Yönetimi*)
  - `AFAD`: 75 features (e.g. *Bandırma 37 No'lu Toplanma Alanı*)
  - `AFAD;Sarıyer Belediyesi`: 2 features
  - `Afad`: 1 feature
  - `Karşıyaka Belediyesi`: 1 feature
  - `Trakya Dent`: 1 feature (private dental health center)
  - `Marmara Üniversitesi`: 1 feature (university campus)
  - `Afet ve Acil Durum Yönetimi Başkanlığı (AFAD)`: 1 feature
  - **Measured String Lengths (332 values):**
    - Min length: **3 characters**
    - Max length: **45 characters** (e.g. `"Afet ve Acil Durum Yönetimi Başkanlığı (AFAD)"`)
    - Median length: **3.0 characters**
    - 95th percentile length: **4.0 characters**
- **Officiality Policy:** Contributor-entered `operator` tags do NOT convert an OSM feature into official government data. All features remain classified as `community_open_data`.

### Source Feature ID (`source_feature_id`) Lengths
- Evaluated across all 678 elements (`f"{type}/{id}"`):
  - Min length: **13 characters**
  - Max length: **16 characters** (e.g. `node/4284118948`, `way/1489204204`)
  - No element exceeds 16 characters in the current snapshot.

### String-Type & Storage Bounds Recommendation
- Current conceptual schema snippets (e.g. `VARCHAR(256)`, `VARCHAR(64)`, `VARCHAR(128)`) are strictly **PROPOSED / CONCEPTUAL** and do not represent finalized migration DDL.
- TASK 10B-2 will select either `Text` or generously bounded `VARCHAR` based on this measured empirical evidence and future source evolution considerations, avoiding artificially restrictive bounds.

---

## 5. Disaster Suitability Tag Analysis & Architecture Decision

Evaluation of all documented disaster suitability sub-tags across the snapshot:

| Tag | Yes | No | Missing (`UNKNOWN`) | Unexpected Values |
|---|---|---|---|---|
| `assembly_point:earthquake` | **0 (0.0%)** | **0 (0.0%)** | **678 (100.0%)** | None |
| `assembly_point:fire` | **0 (0.0%)** | **0 (0.0%)** | **678 (100.0%)** | None |
| `assembly_point:flood` | **0 (0.0%)** | **0 (0.0%)** | **678 (100.0%)** | None |
| `assembly_point:tsunami` | **0 (0.0%)** | **0 (0.0%)** | **678 (100.0%)** | None |

### Data-Driven Architecture Decision
1. **No Dedicated Initial Suitability Columns:** Because **0 out of 678 features (0.0%)** contain any disaster suitability tags, TASK 10B-2 should **NOT** normalize `earthquake_suitability`, `fire_suitability`, `flood_suitability`, or `tsunami_suitability` into dedicated database columns. Creating four columns that would be 100% `NULL` adds schema surface without providing usable data.
2. **Tri-State Semantics Remains a Domain Rule:** The conceptual domain rule (`yes -> true`, `no -> false`, `missing -> unknown`) is retained for future source integrations. If future sources or fresh snapshots introduce disaster tags, dedicated columns can be added via an Alembic migration.
3. **No Earthquake-Specific Filter:** Because coverage is 0.0%, exposing an `earthquake_suitable=true` filter would return zero results nationwide.

---

## 6. Privacy & Personal Contact Review

An expanded screening was performed across all 33 observed tag keys using case-insensitive regex patterns for personal contact concepts:
`\b(phone|mobile|email|contact|person|fax)\b`

- **Contact-Related Keys Detected:** **0** (none of the 33 keys contain phone numbers, email addresses, personal names, or contact fields).
- **TASK 10B-2 Ingestion Allowlist vs Denylist Policy:**
  Rather than blindly persisting raw tags into `source_properties`, the importer enforces an **allowlist-first policy** coupled with an **explicit denylist for defense-in-depth**. Normalized fields (`name`, `ref`, `operator`) are already stored in dedicated columns and are omitted from `source_properties` to prevent redundancy.

  #### A. Currently Observed & Approved Keys (22 Keys)
  - Core / Context: `emergency`, `name:en`, `source`, `website`, `area`, `indoor`, `opening_hours:emergency`
  - Land-use / Spatial: `leisure`, `amenity`, `building`, `parking`, `highway`, `fee`
  - Specifically Observed Address Keys (No broad `addr:*` wildcard):
    `addr:city`, `addr:district`, `addr:neighbourhood`, `addr:subdistrict`, `addr:province`, `addr:country`, `addr:postcode`, `addr:street`, `addr:housenumber`

  #### B. Domain-Relevant Approved Keys Currently Absent (Deliberate Exception — 4 Exact Keys)
  Accepted even though absent (0.0%) from the 2026-09-04 snapshot to preserve domain-critical tags if future OSM updates include them:
  - `assembly_point:earthquake`
  - `assembly_point:fire`
  - `assembly_point:flood`
  - `assembly_point:tsunami`
  *(Note: An unrestricted wildcard `assembly_point:*` is strictly forbidden; only these 4 reviewed disaster keys are permitted).*

  #### C. Explicitly Excluded Keys (Defense-in-Depth Denylist & Low-Value Exclusion)
  - Personal contact / PII keys: `phone`, `mobile`, `email`, `fax`, `contact:*`, `contact:person`, `contact:name`
  - Contributor free-text fields (risk of sensitive / unformatted text): `note`, `description`
  - Low-value / unneeded metadata: `building:levels`, `building:units`, `height`, `opening_hours:marketplace`, `shop`, `education`
  - Any unknown / unreviewed tag appearing in future snapshots will be dropped by default.

  *(API Exposure Policy: `source_properties` is strictly an internal audit field and must NOT be exposed through the public REST API by default).*

---

## 7. Semantic Fitness & Facility-Muster Assessment

### Objective Semantic Groups (Mutually Exclusive Precedence)
- **Group 1 (`explicit_earthquake_yes`):** **0 (0.0%)**
- **Group 2 (`explicit_earthquake_no`):** **0 (0.0%)**
- **Group 3 (`other_disaster_explicit_yes`, without eq=yes):** **0 (0.0%)**
- **Group 4 (`generic_or_unknown_semantics`):** **678 (100.0%)**

### Facility-Muster vs Public Disaster Gathering Analysis
Manual inspection of representative records confirmed that:
1. Some records represent public emergency assembly spaces (e.g. municipal feeds, public parks like *"Mehmet Bulur Parkı"*).
2. Other records represent facility-specific muster points (e.g. private clinic *"Trakya Dent"*, university campus *"Marmara Üniversitesi"*, shopping mall parking *"Cevahir AVM Açık Otopark"*).
3. However, because `access` is **100% missing** (0/678), programmatic discrimination between private facility muster points and public gathering spaces is **UNRESOLVED FROM OSM TAGS ALONE**.

---

## 8. Geographic Distribution & Sparsity Analysis

### Reproducible Spatial Grid Definition
To evaluate spatial distribution reproducibly without external geocoding dependencies:
- **Latitude Span:** `[35.0, 43.0]` (8 bands of 1.0° height: `[35,36), [36,37), ..., [42,43)`)
- **Longitude Span:** `[25.0, 45.0]` (20 bands of 1.0° width: `[25,26), [26,27), ..., [44,45)`)
- **Cell Size:** 1.0° × 1.0° (~85 km × 111 km at mid-latitudes)
- **Exact Total Analysis Grid Cells:** $8 \times 20 = \mathbf{160\text{ cells}}$
- **Boundary Inclusion Rule:** The analysis grid is defined explicitly as half-open intervals:
  - $\text{latitude} \ge 35.0 \text{ AND } \text{latitude} < 43.0$
  - $\text{longitude} \ge 25.0 \text{ AND } \text{longitude} < 45.0$
  - Cell indices are derived deterministically using floor values: `cell_lat = floor(lat)`, `cell_lon = floor(lon)`.
- **Out-of-Grid Analytical Coordinates:** **0** (verified: every one of the 678 analytical representative coordinates falls strictly inside the defined $[35.0, 43.0) \times [25.0, 45.0)$ grid; zero coordinates were dropped).
- **Polygon Analytical Representative Coordinate (PostGIS `ST_PointOnSurface`):**
  - Rather than using the arithmetic mean of vertices, a deterministic interior representative point was computed for each of the 28 closed polygons using PostGIS `ST_PointOnSurface(geometry)`.
  - This representative point is strictly for coarse analytical binning and will **never** be persisted or used for nearest-distance queries.
  - Runtime queries in TASK 10B-2 will execute `ST_Distance(assembly_geometry::geography, query_point::geography)` directly against the actual source polygon boundaries.
- **Occupancy Recomputation Results:**
  - **Occupied Analysis Cells:** **27 of 160 cells (16.88%)**
  - **Empty Analysis Cells:** **133 of 160 cells (83.12%)**
  - **Consistency Confirmation:** Transitioning from the vertex-average method to PostGIS `ST_PointOnSurface` yielded the exact same 27 occupied cells and 133 empty cells. The more robust interior representative point method confirms and preserves the aggregate spatial result without alteration.

### Top Concentrated Spatial Cells
| Spatial Cell | Feature Count | % of 678 | Geographic Cluster Description |
|---|---|---|---|
| `[lat 41..42, lon 27..28)` | 220 | 32.45% | Eastern Thrace / Tekirdağ-Kırklareli cluster |
| `[lat 40..41, lon 27..28)` | 107 | 15.78% | Southern Marmara / Çanakkale-Balıkesir cluster |
| `[lat 41..42, lon 28..29)` | 77 | 11.36% | Istanbul European side cluster |
| `[lat 41..42, lon 29..30)` | 60 | 8.85% | Istanbul Asian side / Kocaeli cluster |
| `[lat 40..41, lon 30..31)` | 54 | 7.96% | Sakarya cluster |
| `[lat 40..41, lon 29..30)` | 24 | 3.54% | Bursa / Yalova cluster |
| `[lat 36..37, lon 28..29)` | 20 | 2.95% | Southwestern Aegean Coast / Muğla cluster |
| `[lat 38..39, lon 27..28)` | 20 | 2.95% | Central Aegean / İzmir cluster |
| `[lat 40..41, lon 28..29)` | 16 | 2.36% | Southern Marmara Sea coastal cluster |
| `[lat 39..40, lon 32..33)` | 14 | 2.06% | Central Anatolia / Ankara cluster |

### Geographic Sparsity Conclusion
- **Cluster Density:** Over **76%** of all features in Türkiye are concentrated in northwestern spatial cells around the Sea of Marmara and Thrace.
- **Wording Rule:** Specific administrative province counts were removed because official administrative boundaries were not used to partition the data. Instead:
  > *"The measured OSM emergency=assembly_point snapshot is strongly clustered in a limited set of spatial cells, particularly in western / northwestern Türkiye. Large areas of Central, Eastern, and Southeastern Anatolia and the Black Sea region contain no mapped features in the analyzed spatial cells. Absence of an assembly point in a spatial cell does NOT imply absence of an official emergency area on the ground."*

---

## 9. Final Recommendations for TASK 10B-2

### 1. Final Source Decision: OUTCOME A
- **Ingest all 678 OSM emergency=assembly_point records as community-sourced emergency assembly points under neutral terminology.**
- Do **not** expose an earthquake-specific suitability filter (as coverage is 0.0%).
- Preserve semantic uncertainty and disclose that community data may include private/facility muster points.

### 2. Public Product Terminology
- English: *"community-mapped emergency assembly points"*
- Turkish: *"OSM'de işaretlenmiş acil durum toplanma noktaları"*
- Disclose: community-sourced, geographically incomplete, may include facility muster points, not AFAD-certified, not guaranteed safe/open/reachable/current.
- The phrase *"AFAD Toplanma Alanları"* must **never** be used for OSM-derived records.

### 3. Recommended Initial Normalized Database Schema (PROPOSED / CONCEPTUAL)
Based on actual snapshot support, the initial `assembly_areas` table should normalize only observed, useful fields:
- `id` (UUID PK)
- `dataset_id` (UUID FK -> `assembly_area_datasets.id`)
- `source_feature_id` (VARCHAR / Text, e.g. `node/5049895124`, `way/226421064`; observed max: 16 chars)
- `name` (VARCHAR / Text, nullable; observed max: 77 chars)
- `ref` (VARCHAR / Text, nullable; observed max: 21 chars)
- `operator` (VARCHAR / Text, nullable; observed max: 45 chars)
- `geometry` (PostGIS `GEOMETRY(Geometry, 4326)` with GiST index)
- `source_properties` (JSONB, sanitized allowlisted metadata)
- `created_at`, `updated_at` (TIMESTAMPTZ)

*(Note: This schema recommendation is strictly **PROPOSED / CONCEPTUAL** and does not represent finalized migration DDL. The column type bounds are provisional; TASK 10B-2 will select either `Text` or generously bounded `VARCHAR` based on empirical evidence and source evolution considerations. Dedicated columns for `access`, `capacity`, `check_date`, and the 4 disaster suitability tags are omitted initially because they are 100% unpopulated in this dataset; tri-state suitability domain semantics remain active and can be normalized via future migrations if supported by future datasets).*

### 4. Idempotency & Update Strategy
- Natural key `(dataset_id, source_feature_id)` provides 100% collision-free idempotent upsert.
- Future snapshot updates can use complete snapshot replacement or idempotent upsert given the small scale (678 features).

### 5. Known Limitations & Future-Required Items
1. **Facility/private-vs-public semantic discrimination remains unresolved from OSM tags alone:** OSM source tags do not permit reliable programmatic distinction between facility/private muster points and general-public assembly points because `access` metadata is 100% absent in the authoritative snapshot.
2. **Final public-deployment ODbL compliance review remains required:** While community data is licence-compatible in principle, compliance controls (frontend attribution, data export/download provisions, database separation) must be reviewed prior to production deployment.

*(Neither limitation blocks TASK 10B-2 development).*
