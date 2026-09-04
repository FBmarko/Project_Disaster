# Earthquake Hazard Source, Access, Licensing, and Architecture Validation (Phase 8A)

**Status:** Completed Research Document (Corrected & Precision-Reviewed)  
**Date:** 2026-09-03  
**Context:** AFET360 Natural Disaster Information & Preparedness Web Platform  
**Branch:** `feature/backend-hazard-source-validation`

---

## 1. Executive Summary

Seismic hazard information is a foundational component of earthquake resilience. However, before designing domain models, database tables, or REST endpoints for earthquake hazard, AFET360 must establish an unassailable legal, scientific, and technical foundation.

This Phase 8A investigation rigorously evaluates:
1. The official Turkish national seismic hazard product: **T.C. İçişleri Bakanlığı AFAD Türkiye Deprem Tehlike Haritası (TDTH)**.
2. Official Turkish spatial data distribution channels, including **TUCBS** (Ulusal Coğrafi Bilgi Platformu) and **Coğrafi Bilgi Sistemleri Genel Müdürlüğü Coğrafi Veri Talep Portalı**.
3. Open-access scientific alternatives, specifically the **Global Earthquake Model (GEM) Global Seismic Hazard Map (GSHM v2026.1)** and **EFEHR ESHM20**.

### Key Findings & Compliance Policy:
- **AFAD TDTH** is the sole official regulatory hazard reference in Türkiye (enacted under TBDY 2018). As of the 2026-09-03 review, **no publicly documented or discoverable TDTH REST, WMS, WFS, WMTS, or machine-readable bulk hazard service was found in the reviewed official AFAD/TUCBS channels**. It operates behind mandatory **e-Devlet authentication** for single-point PDF reports. The TDTH legal notice explicitly requires written AFAD permission for electronic reproduction, distribution, or publication; therefore, AFET360 treats TDTH database ingestion and API redistribution as **blocked unless written permission or an official data protocol is obtained**.
- **GEM Global Seismic Hazard Map (v2026.1)** provides continuous global map coverage including Türkiye and surrounding offshore areas, assembled from multiple national, regional, and GEM-developed hazard models. Released via Zenodo, the verified open artifact is `gshm_v2026_1_vector.zip` (~935.5 MB), distributed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)** dataset license (distinct from the AGPL-3.0 software license of the OpenQuake engine).
- **Nominal Exceedance Equivalence (Not Interchangeable Values):** The GEM v2026.1 PGA layer and AFAD/TBDY DD-2 share the **same nominal exceedance level** (10% probability of exceedance in 50 years, ~475-year return period). However, they are **not interchangeable datasets or values** due to differing input models, regional seismotectonic zoning, and reference site conditions (GEM reference $V_{S,30} = 800\text{ m/s}$ vs AFAD TDTH reference $V_{S,30} = 760\text{ m/s}$).
- **Recommended Policy:**
  - **AFAD TDTH:** `CONDITIONAL / BLOCKED FOR REDISTRIBUTION WITHOUT WRITTEN PERMISSION` (Official Türkiye regulatory reference).
  - **GEM GSHM v2026.1 open layer:** `APPROVED FOR NON-COMMERCIAL AFET360 DEVELOPMENT/COMPETITION` under CC BY-NC-SA 4.0 and its attribution/ShareAlike conditions.
  - **TUCBS:** `CONDITIONAL` (No openly discoverable TDTH hazard layer found during this review; formal institutional request path remains available via `cografiveri.gov.tr`).

---

## 2. Review of Prior Project Decisions (Phase 3 Baseline)

In Phase 3, AFET360 established ADR 0001 (`backend/docs/adr/0001-geospatial-data-sources.md`) and the Geospatial Architecture (`backend/docs/geospatial-data-architecture.md`). 
Section 3 of ADR 0001 recorded:
- **Authority:** AFAD Türkiye Deprem Tehlike Haritası (TDTH) under TBDY 2018.
- **Status:** *UNRESOLVED / REQUIRES FURTHER AUTHORIZATION OR OFFICIAL DATA ACCESS REVIEW*.
- **Findings:** Data is controlled by AFAD. Legal notice restricts unauthorized reproduction/distribution. No documented anonymous bulk REST API exists. Automated bulk scraping is prohibited.
- **Decision:** No hazard data ingestion or database modeling will occur until programmatic access rights are formally clarified.

Phase 8A fulfills this mandate by conducting exhaustive source-validation before any code or database migration is created.

---

## 3. Official AFAD Hazard Product Analysis: Türkiye Deprem Tehlike Haritası (TDTH)

### 3.1 Product Identity & Legal Enactment
- **Official Name:** Türkiye Deprem Tehlike Haritası (TDTH)
- **Legal Document Title:** *Türkiye Deprem Tehlike Haritası ve Parametre Değerleri Hakkında Karar*
- **Authority:** T.C. İçişleri Bakanlığı Afet ve Acil Durum Yönetimi Başkanlığı (AFAD) — Deprem Dairesi Başkanlığı
- **Development Context:** Updated under the National Earthquake Research Program (UDAP-Ç-13-06, *"Türkiye Deprem Tehlike Haritasının Güncellenmesi Projesi"*) with leading Turkish seismologists and earthquake engineers.
- **Council of Ministers Decision Date:** 22 January 2018
- **Council of Ministers Decision Number:** **2018/11275**
- **Publication Date:** 18 March 2018 (Resmî Gazete Sayı: 30364 Mükerrer)
- **Effective Date:** 1 January 2019, concurrently entering into force with the Türkiye Bina Deprem Yönetmeliği (TBDY 2018).
- **Historical Significance:** TDTH officially abolished the obsolete 1996 "Türkiye Deprem Bölgeleri Haritası" (which assigned arbitrary 1st through 5th degree earthquake zones). Instead, TDTH provides continuous, probabilistic, coordinate-specific ground motion values across Türkiye.

### 3.2 Scientific Definition & Reference Site Conditions
- **Assessment Methodology:** Probabilistic Seismic Hazard Assessment (PSHA).
- **Reference Ground Condition:** Standard reference rock condition with shear wave velocity $V_{S,30} = 760\text{ m/s}$ (Site Class ZB in TBDY 2018 / NEHRP B/C boundary).
- **Local Soil Effects:** Site-specific geotechnical amplifications ($F_s, F_1$) are calculated separately by design engineers using local borehole/geophysical data (Site Classes ZA, ZB, ZC, ZD, ZE, ZF). The raw map values represent reference rock shaking only.

### 3.3 Earthquake Ground Motion Levels (Deprem Yer Hareketi Düzeyleri)
TDTH defines four distinct earthquake ground motion levels based on statistical probability of exceedance:
1. **DD-1 (Çok Seyrek Deprem Yer Hareketi):** 50 yılda aşılma olasılığı %2 (Tekrarlanma periyodu 2475 yıl).
2. **DD-2 (Seyrek / Standart Tasarım Depremi):** 50 yılda aşılma olasılığı %10 (Tekrarlanma periyodu 475 yıl). Standard regulatory design basis for conventional structures.
3. **DD-3 (Sık Deprem Yer Hareketi):** 50 yılda aşılma olasılığı %50 (Tekrarlanma periyodu 72 yıl).
4. **DD-4 (Çok Sık / Servis Depremi):** 50 yılda aşılma olasılığı %68 (Tekrarlanma periyodu 43 yıl).

### 3.4 Spectral Acceleration & Hazard Parameters
At any given coordinate, TDTH models four key seismic parameters for each ground motion level:
- **PGA ($g$):** Peak Ground Acceleration (En Büyük Yer İvmesi)
- **PGV ($\text{cm/s}$):** Peak Ground Velocity (En Büyük Yer Hızı)
- **$S_s$ (dimensionless):** Kısa periyot harita spektral ivme katsayısı ($T = 0.2\text{ s}$)
- **$S_1$ (dimensionless):** 1.0 saniye periyot için harita spektral ivme katsayısı ($T = 1.0\text{ s}$)

---

## 4. Crucial Scientific Distinction: Hazard $\ne$ Risk

AFET360 backend architecture strictly enforces the distinction between seismic hazard and seismic risk:

$$\text{Risk} = \text{Hazard} \times \text{Exposure} \times \text{Vulnerability}$$

1. **Hazard (Deprem Tehlikesi):** The physical probability of natural ground shaking (PGA, $S_s, S_1$) exceeding a threshold at a given location and reference soil condition within a specified return period. It is independent of whether a human structure or population exists at that location.
2. **Risk (Deprem Riski):** The expected human casualties, structural damage, or economic losses resulting from ground shaking impacting specific structures of known age, construction quality, occupancy, and soil-structure interaction.

### Prohibited Claims in AFET360 API & UI:
- *"Your building is safe from earthquakes"* (structural engineering and local site investigation are required).
- *"This district has X% earthquake risk"* (unless exposure and fragility curves are mathematically integrated).
- *"You will experience X acceleration in the next earthquake"* (hazard is probabilistic, not a deterministic prediction).
- Inventing naive *"Low / Moderate / High Risk"* categories based on raw reference rock PGA.

### Approved Safe Scientific Terminology:
- *"Probabilistic Seismic Ground Shaking Hazard on Reference Rock ($V_{S,30} = 760\text{–}800\text{ m/s}$)"*
- *"Standard Design Ground Motion Nominal Level (475-year return period, 10% exceedance in 50 years)"*
- *"Reference Rock Peak Ground Acceleration (PGA)"*
- Mandatory disclaimer: Ground motion values reflect regional reference rock shaking probabilities and do not represent individual building safety, structural vulnerability, or site-specific soil amplification.

---

## 5. TDTH Access Model & Legal Notice

### 5.1 Public Interface & Authentication Requirements
- **Web Portal:** `https://tdth.afad.gov.tr/`
- **Anonymous Access:** **None.** The interactive map application cannot be navigated or queried without authentication.
- **Authentication Method:** Requires user login via the Republic of Türkiye e-Government Gateway (**e-Devlet Kapısı**; T.C. Kimlik Numarası + password or mobile/electronic signature).
- **Service Capabilities:** Inside the authenticated session, an authorized user can click a map coordinate or enter latitude/longitude, specify a soil class and ground motion level, and download an individual PDF report (*"Deprem Tehlike Raporu"*).
- **Public Developer Services:** As of the 2026-09-03 review, **no publicly documented/discoverable TDTH REST, WMS, WFS, WMTS, or machine-readable bulk hazard service was found in the reviewed official AFAD/TUCBS channels.**
- **Bulk Machine-Readable Dataset:** No open public downloads of the complete calculation grid (as CSV, GeoTIFF, GeoPackage, or Shapefile) are advertised for anonymous public access.

### 5.2 Official Legal Notice Analysis
The official terms of use displayed on `tdth.afad.gov.tr` state:
> *"Telif Hakkı: Uygulamada sunulan verilerin, şekillerin, harita, bilgi ve belgelerin her hakkı Afet ve Acil Durum Yönetimi Başkanlığı'na (AFAD) aittir.*  
> *Kullanım ve İzin: Verilerin tamamının veya bir bölümünün kaynakça belirtilmeden kullanılması; AFAD’ın yazılı izni alınmadan elektronik, optik, mekanik veya diğer yollarla çoğaltılması, dağıtılması, satılması, basılması veya yayımlanması durumunda yasal yollara başvurulacaktır.*  
> *MTA Verileri: Uygulamada yer alan Türkiye Diri Fay verileri, Maden Tetkik ve Arama Genel Müdürlüğü (MTA) tarafından üretilmiştir ve her hakkı MTA'ya aittir. Bu verilerin kullanılması veya görüntülenmesi durumunda kaynakça gösterilmesi zorunludur.*  
> *Sorumluluk Reddi: Sunulan raporlar bilgi amaçlı olup resmi belge niteliği taşımaz. Teknik çalışmalarda referans olarak kullanımlarından doğacak sorumluluk AFAD'a ait değildir."*

### 5.3 Compliance Policy for AFET360 Use Cases
| Use Case | Classification | Compliance Policy Rationale |
|---|---|---|
| **A. Show an official hyperlink to TDTH in UI** | **Clearly Permitted** | Standard navigational link to `https://tdth.afad.gov.tr/` with official attribution. |
| **B. Quote/reference AFAD hazard methodology & TBDY 2018** | **Clearly Permitted** | Academic and legal citation of published national regulations. |
| **C. Reproduce a static AFAD hazard map image in the app** | **Permission Required** | The legal notice requires written AFAD permission for electronic reproduction/distribution. |
| **D. Store AFAD point hazard values in AFET360 database** | **Blocked without Written Permission** | Creating a derivative database from TDTH requires explicit written authorization. |
| **E. Expose AFAD hazard values through AFET360 REST API** | **Blocked without Written Permission** | Electronic redistribution through a third-party API without written protocol violates terms. |
| **F. Bulk redistribute full AFAD hazard layers** | **Blocked without Written Permission** | Prohibited by TDTH legal terms without formal inter-agency or institutional protocol. |

---

## 6. Official Geographic Data Channels: TUCBS & Open Data Portals

An exhaustive search was conducted across official Turkish geographic information platforms:
1. **Ulusal Coğrafi Bilgi Platformu (TUCBS - `tucbs.gov.tr`):**
   - AFAD registers emergency infrastructure layers on TUCBS:
     - Acil Durum Toplanma Alanları (Emergency Assembly Areas)
     - AFAD Lojistik Depoları (Logistics Warehouses)
     - Afet ve Acil Durum Yönetim Merkezleri (Disaster Management Centers)
     - Arama Kurtarma Birlikleri (Search & Rescue Units)
     - Geçici Barınma Alanları (Temporary Shelter Areas)
     - Siren Sistemleri (Warning Sirens)
   - As of the 2026-09-03 review, **no openly discoverable TDTH hazard layer was found on TUCBS** as an open dataset or public OGC service.
2. **Coğrafi Bilgi Sistemleri Genel Müdürlüğü — Coğrafi Veri Talep Portalı (`cografiveri.gov.tr`):**
   - Provides an institutional protocol mechanism for universities, research institutes, and public agencies to formally request spatial datasets.
   - **Verdict:** Status is `CONDITIONAL`. This provides a legitimate institutional path for future academic cooperation, but requires a formal administrative application that cannot be automated or assumed open today.
3. **Resmî Gazete Publication (18 March 2018 / 30364 Mükerrer):**
   - Publishes regulatory formulas and an overview map image, but not the multi-million-node numerical calculation database. Official regulatory publication does not constitute an open CC-style public domain grant for automated bulk redistribution.
4. **Static PDF/Poster Sampling Prohibition:**
   - AFAD distributes high-resolution graphic posters (PDF/JPG) of the map.
   - Attempting to sample pixel RGB values to derive numeric PGA is scientifically invalid (color gradients produce substantial non-linear calculation errors) and technically fragile. AFET360 strictly rejects pixel-sampling or OCR reverse-engineering.

---

## 7. AFAD Programmatic Access Decision

**Decision:** **NO.**  
As of the 2026-09-03 review, **no publicly documented/discoverable TDTH REST/WMS/WFS/WMTS or machine-readable bulk hazard service was found in the reviewed official AFAD/TUCBS channels that AFET360 can legally consume and redistribute through its own API today without written permission.**

In adherence to project rules, **no automated scraping, session emulation, or e-Devlet authentication bypass will be attempted.**

---

## 8. Open-Access Scientific Alternative: GEM Global Seismic Hazard Map

Because AFAD programmatic redistribution is blocked without written permission, AFET360 evaluated open scientific alternatives for development, staging, and competition needs.

### 8.1 GEM Global Seismic Hazard Map (GSHM v2026.1)
- **Authority:** Global Earthquake Model (GEM) Foundation (Pavia, Italy).
- **Current Version:** **v2026.1** (June 2026 release, archived on Zenodo).
- **Coverage:** Continuous global map coverage including Türkiye and surrounding offshore areas, assembled from multiple national, regional, and GEM-developed hazard models.
- **Scientific Hazard Metric:** Mean Peak Ground Acceleration (PGA) in units of $g$ ($1\text{ }g \approx 9.81\text{ m/s}^2$).
- **Nominal Exceedance Level:** 10% probability of exceedance in 50 years (~475-year return period).
- **Reference Soil Condition:** Standard reference rock, $V_{S,30} = 800\text{ m/s}$.
- **Resource Distinction (Product Description vs Verified Artifact):**
  - GEM product documentation describes open vector and raster map resources in general.
  - The **currently verified Zenodo artifact is `gshm_v2026_1_vector.zip` (~935.5 MB)**.
  - The internal file format and schema of this archive must be inspected prior to Phase 8B implementation.
  - Phase 8B ingestion architecture MUST NOT be finalized before archive inspection. (The archive is not downloaded during this research phase).
- **Separation of Dataset License vs Software License:**
  - **Hazard Dataset License:** **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)**.
  - **OpenQuake Engine Software License:** The software used to generate models is licensed under **GNU Affero General Public License v3.0 (AGPL-3.0)**. AGPL-3.0 is **not** the hazard dataset license.
- **Licensing Status Scoping for AFET360:**
  - **APPROVED — NON-COMMERCIAL DEVELOPMENT / COMPETITION**
  - *Conditions:* Attribution required; NonCommercial restriction applies; ShareAlike applies to covered adaptations/derived resources.
  - *Commercial / Production Deployment:* Requires separate licensing evaluation / commercial license from the GEM Foundation.

### 8.2 Scientific Comparison: Nominal Exceedance Equivalence vs Interoperability
- **Scientific Distinction:** GEM v2026.1 PGA and AFAD/TBDY DD-2 share the **same nominal exceedance-probability and time-horizon concept** (10% probability of exceedance in 50 years, ~475-year return period).
- **Not Interchangeable:** They are **not interchangeable datasets or values**, and must never be described as "identical hazard" or "equivalent values":
  1. *Reference Soil:* GEM uses $V_{S,30} = 800\text{ m/s}$; AFAD TDTH uses $V_{S,30} = 760\text{ m/s}$.
  2. *Underlying Seismotectonic Models:* Input active fault sources, ground motion prediction equations (GMPEs/GMMs), and regional seismicity catalogs differ.
  3. *Regulatory Authority:* AFAD TDTH is legally mandated for building design under Turkish law; GEM GSHM is a global scientific research model.

### 8.3 Secondary Open Alternative: ESHM20 (European Seismic Hazard Model 2020)
- **Authority:** EFEHR (European Facilities for Earthquake Hazard and Risk) / ETH Zurich consortium.
- **License:** **Creative Commons Attribution 4.0 International (CC BY 4.0)** (allows commercial and non-commercial reuse with citation).
- **Role:** Maintained as an open European scientific backstop.

---

## 9. Comprehensive Source Decision Matrix

| Dataset & Authority | Official TR Status | Machine-Readable Format | Public Anonymous Access | Auth Required | License Clarity | Redistribution Allowed | AFET360 Status | Architecture Policy |
|---|---|---|---|---|---|---|---|---|
| **AFAD TDTH (TBDY 2018)** | Official National Standard | No (interactive portal / single PDF) | No | Yes (e-Devlet) | High (All rights reserved) | No (Written permission required) | **CONDITIONAL / BLOCKED FOR REDISTRIBUTION WITHOUT WRITTEN PERMISSION** | **Production Regulatory Target.** Requires written protocol. UI provides direct link to `tdth.afad.gov.tr`. |
| **TUCBS / Coğrafi Veri Talep Portalı** | Official National Platform | Yes (for facilities; restricted for hazard grid) | No (for hazard layer) | Yes (institutional) | High (TUCBS matrix) | Requires formal protocol | **CONDITIONAL** | **Institutional Channel.** Formal request path available via `cografiveri.gov.tr` for university project. |
| **GEM GSHM (v2026.1)** | International Research Model | Verified artifact: `gshm_v2026_1_vector.zip` (~935.5 MB) | Yes (Zenodo) | No | Clear (**CC BY-NC-SA 4.0**) | Yes (Non-commercial with attribution) | **APPROVED — NON-COMMERCIAL DEVELOPMENT / COMPETITION** | **Development & Demo Source.** Provides open ~475-year reference rock PGA layer under CC BY-NC-SA 4.0. |
| **EFEHR ESHM20** | Pan-European Scientific Model | Yes (GitLab, NRML, Shapefile) | Yes | No | Clear (**CC BY 4.0**) | Yes (commercial & non-commercial) | **APPROVED** | **Secondary Scientific Reference.** Pan-European research benchmark. |

---

## 10. Architectural Recommendation for AFET360

### Two-Tier Hybrid Policy:
1. **Development, Staging & Competition Backend:**
   - Ingest and normalize the open **GEM Global Seismic Hazard Map (v2026.1)** verified vector resource.
   - Expose reference rock PGA ($V_{S,30} = 800\text{ m/s}$, nominal 475-year return period) through a source-agnostic schema.
   - Display mandatory attribution to the GEM Foundation (`CC BY-NC-SA 4.0`) and explicit disclaimers that this is an open research model, not the official Turkish regulatory TBDY 2018 dataset.
2. **Production Regulatory Target:**
   - Maintain AFAD TDTH as the production target.
   - If AFET360 proceeds to municipal or commercial deployment, execute a formal institutional data protocol through the Coğrafi Veri Talep Portalı / AFAD Başkanlığı.
3. **Citizen Navigation in UI:**
   - Provide an educational guide in the frontend distinguishing hazard from risk, with direct external links to `https://tdth.afad.gov.tr/` for downloading official e-Devlet building earthquake hazard reports.

---

## 11. Proposed Future Phase 8B Data & API Contracts (Not Implemented)

### 11.1 Phase 8B Permitted Metric Assumptions
Phase 8B v1 must expose **ONLY fields supported by the exact selected GEM open artifact**. Do NOT assume the open artifact contains PGV, $S_s$, $S_1$, or multiple return periods. The verified open base product is strictly:
- **PGA**
- **10% probability of exceedance in 50 years** (~475-year return period)
- **Reference $V_{S,30} = 800\text{ m/s}$**

Any additional metrics or return periods require separately verified GEM resources/licenses.

### 11.2 Proposed Source-Agnostic Schema (Conceptual)
```python
# Conceptual schema only — do not implement in Phase 8A
class EarthquakeHazardPoint:
    id: UUID
    source: str  # e.g. "GEM_GSHM"
    source_version: str  # e.g. "2026.1"
    model_name: str  # "GEM Global Seismic Hazard Map v2026.1"
    latitude: float
    longitude: float
    hazard_metric: str  # "PGA"
    hazard_value: float  # e.g., 0.384
    unit: str  # "g"
    return_period_years: int  # 475
    exceedance_probability: float  # 0.10
    time_horizon_years: int  # 50
    reference_vs30_mps: float  # 800.0
    reference_ground: str  # "Reference Rock"
    license: str  # "CC BY-NC-SA 4.0"
    attribution: str
    disclaimer: str
```

### 11.3 Proposed Future REST API Concept
- `GET /api/v1/earthquake-hazards/point?latitude=41.0&longitude=29.0&metric=PGA&return_period_years=475`
- Returns RFC 7946 GeoJSON Feature with Point geometry, normalized hazard properties, source metadata, and mandatory scientific non-causal disclaimers.

---

## 12. Conclusion & Verification Summary

Phase 8A source validation and precision corrections are complete. No application code was written, no database migrations were created, no remote archive was downloaded, and no protected systems were scraped.
