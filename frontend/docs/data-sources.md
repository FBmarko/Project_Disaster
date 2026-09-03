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
