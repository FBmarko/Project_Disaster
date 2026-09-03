# Veri Kaynakları / Data Sources

## Türkiye il sınırları (`src/data/turkey-provinces.geojson`)

| | |
| --- | --- |
| **Kaynak / Source** | `alpers/Turkey-Maps-GeoJSON` |
| **Repository** | https://github.com/alpers/Turkey-Maps-GeoJSON |
| **Dosya / File** | `tr-cities.json` (yalnızca Türkiye — KKTC/Kıbrıs dahil değil) |
| **Lisans / License** | Apache License 2.0 |
| **Lisans metni** | https://github.com/alpers/Turkey-Maps-GeoJSON/blob/master/LICENSE |
| **İndirilme tarihi** | 2026-09-03 |
| **SHA-256** | `8fe1cf3fbac8fab8a5fe7ebfc588dd01d62802ca994bf959f715c991a8382e11` |

Dosya, indirildiği hâliyle (byte-for-byte) saklanmaktadır; koordinatlar üzerinde
hiçbir değişiklik yapılmamıştır.

### Neden bu kaynak?

- **Apache-2.0** — izin veren (permissive) bir lisans. geoBoundaries ADM1 (TUR)
  değerlendirildi, ancak OpenStreetMap kaynaklı olduğu için
  **CC BY-SA 2.0** ile dağıtılıyor; ShareAlike koşulu bu proje için gereksiz bir
  yük getiriyor.
- Tam olarak **81 feature** içeriyor; her il tek bir feature.
- Ayrıntı düzeyi (5.990 koordinat, 241 KB) statik SVG tematik harita için yeterli
  ve tarayıcıya makul bir yük bindiriyor.
- Yalnızca Türkiye illerini içeren varyantı (`tr-cities.json`) mevcut; havalimanı
  ve KKTC/Kıbrıs eklentileri olan varyantlar bu sayfa için gereksiz.

### Doğrulama / Verification

`npm run validate:provinces` betiği veri setini programatik olarak denetler:

- geçerli bir `FeatureCollection` olduğunu,
- feature sayısının 81 olduğunu,
- her feature'ın `Polygon` veya `MultiPolygon` geometrisi taşıdığını,
- 81 resmî ilin tamamının çözümlendiğini,
- Türkçe/ASCII karakter farkından doğan yinelenen ya da eksik il olmadığını,
- koordinat sınırlarının Türkiye ile uyumlu olduğunu,
- dosyada çalıştırılabilir/şüpheli içerik bulunmadığını

kontrol eder. Son çalıştırma sonucu: **81/81 il doğrulandı, eksik ve yinelenen yok.**

### İsim eşleme / Name mapping

Veri setindeki iki isim resmî adlandırmadan ayrılıyor ve
`src/constants/provinces.ts` içindeki eşleme katmanında karşılanıyor:

| Veri setindeki ad | Kanonik ad |
| --- | --- |
| `Afyon` | `Afyonkarahisar` |
| `Hakkari` | `Hakkâri` |

Kalan 79 il, Türkçe karakterler katlandıktan sonra (`İ/I/ı → i`, `ş → s`, `ğ → g`
vb.) kanonik listeyle bire bir örtüşüyor.

### Çalışma zamanı davranışı

GeoJSON, Vite tarafından **derleme sırasında** paket içine gömülür
(`?raw` importu). Uygulama çalışırken herhangi bir üçüncü taraf servisten
coğrafi veri indirilmez.

## Aktif faylar (`src/data/turkey-active-faults.geojson`)

- **Dataset:** GEM Global Active Faults Database (GEM GAF-DB), GEM Foundation.
- **Repository:** https://github.com/GEMScienceTools/gem-global-active-faults
- **Pinned revision:** `56816508ad92fd6846dad1163b1c8c01376a2cd1` (current master checked 2026-09-03).
- **Exact original file:** https://raw.githubusercontent.com/GEMScienceTools/gem-global-active-faults/56816508ad92fd6846dad1163b1c8c01376a2cd1/geojson/gem_active_faults.geojson
- **License at that revision:** https://github.com/GEMScienceTools/gem-global-active-faults/blob/56816508ad92fd6846dad1163b1c8c01376a2cd1/LICENSE.txt
- **License:** Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0), https://creativecommons.org/licenses/by-sa/4.0/.
- **Local full license:** `docs/licenses/GEM-CC-BY-SA-4.0.txt`. The derived fault dataset and its rendered fault layer are distributed under CC BY-SA 4.0. Retain attribution, license and change notices when redistributing or adapting them. No endorsement by GEM is implied. The data is provided as-is, without warranties, as stated in the included license.
- **Accessed:** 2026-09-03.
- **Citation:** Styron, Richard, and Marco Pagani. “The GEM Global Active Faults Database.” Earthquake Spectra 36, no. 1_suppl (2020), 160–180. https://doi.org/10.1177/8755293020944182.
- **Constituent catalog used:** EMME. Danciu et al. (2018), “The 2014 Earthquake Model of the Middle East: seismogenic sources,” https://doi.org/10.1007/s10518-017-0096-8. See the GEM repository's constituent-dataset attribution.

### Verification and choice

The repository describes active fault traces of seismogenic concern, with source
catalogs and geological attributes, rather than decorative lines. Its actual
license permits sharing and adaptation, including commercial use, conditional on
attribution and ShareAlike. The source offers GeoJSON as its version of record,
which allows a small local SVG asset without another map library or runtime API.
We inspected the downloaded schema, coordinates, IDs and Turkey coverage before
implementation. The global file has 16,195 features, all LineStrings.

### Exact subset recipe; preserved geometry

`scripts/import-faults.ts` is our own offline importer. Download the pinned source
above to a temporary local file and run from `frontend/`:

```sh
node scripts/import-faults.ts <path-to-gem_active_faults.geojson>
npm run validate:faults -- <path-to-gem_active_faults.geojson>
```

The importer verifies the original byte SHA-256:
`603513086b4693de6008e3444959995c34683b30dac291856340522a76d8505e`.
It selects original features where `catalog_name === 'EMME'`, `catalog_id`
starts with `ME_TR`, and **at least one original vertex** falls inside the
inclusive bounding box computed from the existing 81-province asset:

- west: 25.665136337280273; east: 44.83383941650408
- south: 35.815425872802905; north: 42.1054115295413

Of 323 matching catalog records, 321 meet the viewport criterion. All 321 whole
features are retained, in original order, with 3,787 positions, all LineStrings.
All original properties and numerical coordinate values are preserved. Only
JSON serialization and feature membership change. No clipping, simplification,
rounding, resampling, hand-drawn coordinates or scientific name grouping occurs
in the stored data. SVG projection rounds display coordinates to the existing
two-decimal precision; the stored longitude/latitude values remain unchanged.
The SVG viewport hides portions extending beyond its rectangular viewBox.

This is a **Turkey-focused catalog/viewport subset**, not an exact national-border
intersection or a complete official inventory. Offshore and cross-border parts
of retained segments remain. No fault-to-province intersection is calculated.
Other catalogs, including overlapping SHARE records and Bird plate boundaries,
are excluded by the explicit EMME/catalog-ID selection.

The source features use unique `catalog_id` values (e.g. `ME_TRCS001`), which
become stable application IDs without renumbering. None of these 321 records
has a source `name`; they display “Adsız Fay Segmenti” plus the original ID.
The adapter supports safe source names when present, and both LineString and
MultiLineString geometry. It never infers a named regional fault system.
Raw geological attributes are retained for provenance but are not turned into
UI danger scores, city lists or earthquake histories.

### Integrity, runtime and details

`src/data/turkey-active-faults.manifest.json` records the source revision, URL,
hash, filter, bounds, count and canonical subset SHA-256. The canonical hash
ignores JSON whitespace/line-ending changes. `npm run validate:faults` uses the
same parser and projection as the UI, checks all 321 features, finite coordinates,
nondegenerate open paths, IDs, safe names, Turkey scope and multipart handling.
It also compares the complete HomePage map output (all paths, centers, dimensions)
to its hash captured before the shared projection change. An optional source
argument checks every retained feature for deep equality with the original.

Vite embeds the local GeoJSON through a `?raw` import. The application makes no
third-party fault-data request. Source and license links are attribution links
only, followed solely when the user clicks them.

**REAL:** province boundaries, active-fault source geometry and catalog metadata.
**BACKEND-PENDING:** cities crossed by a selected fault and associated historical
earthquakes. No details fixtures or realistic invented records are included.
The detail components only render supplied arrays; their interface carries the
fault ID and a pending/development/ready status for later backend integration.
Any future development detail response gets a visible development-data notice.
