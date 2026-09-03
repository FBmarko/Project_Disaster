# AFET360 Geospatial Datasets

## 1. Development Source: GEM Global Active Faults Database (GAF-DB)

For development and staging, AFET360 uses fault line data from the **GEM Global Active Faults Database**:

- **Organization**: Global Earthquake Model (GEM) Foundation
- **Repository**: [GEMScienceTools/gem-global-active-faults](https://github.com/GEMScienceTools/gem-global-active-faults)
- **Primary Citation**: Styron, R., and Pagani, M. (2020). The GEM Global Active Faults Database. *Earthquake Spectra*, 36(1_suppl), 160–180. doi:10.1177/8755293020944182
- **License**: Creative Commons Attribution-ShareAlike 4.0 International (**CC BY-SA 4.0**)
- **Format**: GeoJSON (EPSG:4326)
- **Attribution**: Visualizations and data derived from GEM GAF must include attribution to the Global Earthquake Model Foundation.
- **Notice**: GEM data is open scientific research data and must **not** be presented as official Turkish government data.

## 2. Boundary Dataset: Natural Earth 1:50m Generalized Türkiye Country Boundary

For geographic spatial intersection filtering of faults (`--turkey-only`), AFET360 uses the Natural Earth open country-boundary polygon:

- **File**: `backend/data/turkey_boundary.geojson`
- **Source**: [Natural Earth](https://www.naturalearthdata.com/) 1:50m Cultural Vectors (`ne_50m_admin_0_countries`, `ISO_A3 == 'TUR'`)
- **License**: **Public Domain** (dedicated to the public domain in all jurisdictions, free for any purpose)
- **Canonical CRS**: **EPSG:4326** (WGS 84 MultiPolygon)
- **Purpose**: Spatially filter active fault geometries using PostGIS `ST_Intersects` against the Natural Earth 1:50m generalized Türkiye country boundary polygon.
- **Notice**: Natural Earth is an open cartographic reference dataset and is **not** an official Turkish-government administrative boundary source. The resulting count (722 features) specifically represents GEM GAF fault features intersecting the Natural Earth 1:50m Türkiye polygon, and must **not** be described as the official number of fault lines in Türkiye.

## 3. Official Production Target: MTA 2026 Türkiye Diri Fay Haritası

- **Authority**: General Directorate of Mineral Research and Exploration (MTA)
- **Reference**: Elmacı, H., Kürçer, A., Özalp, S., Altuntaş, G., Avcı, H.O., Aydoğan, H., Yüce, A.A., Öztürker, A.R., Karayazı, O., Bayrak, A., Özdemir, E., Çal, Ç., Güven, C., Yalvaç, O., 2026. Türkiye Diri Fay Haritası. Maden Tetkik ve Arama Genel Müdürlüğü, Özel Yayın Serisi-60.
- **Access**: Requires formal institutional protocol / licensing from MTA before deployment to production.

## 4. Running the GEM Fault Import Pipeline

The CLI import command (`app.scripts.import_gem_faults`) supports explicit geographic filtering:

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

# Local file input is also supported:
python -m app.scripts.import_gem_faults --file path/to/faults.geojson --turkey-only
```
