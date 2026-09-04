# AFET360 Frontend

AFET360 kullanıcı arayüzü.

## Teknoloji

- React 19 + TypeScript
- Vite
- Tailwind CSS v4
- React Router
- lucide-react (ikonlar)

## Kurulum

```bash
npm install
cp .env.example .env.local   # değerleri doldurun
npm run dev
```

## Komutlar

| Komut             | Açıklama                          |
| ----------------- | --------------------------------- |
| `npm run dev`     | Geliştirme sunucusu               |
| `npm run build`   | Tip kontrolü + production build   |
| `npm run preview` | Build çıktısını yerelde çalıştırır |
| `npm run lint`    | oxlint                            |
| `npm run validate:provinces` | 81 il ve SVG projeksiyonu |
| `npm run validate:faults` | Gerçek fay verisi, kaynak bütünlüğü ve ortak projeksiyon |
| `npm run validate:simulation` | Simülasyon taslağı doğrulama ve durum geçişleri |
| `npm run validate:preparedness` | Hazırlık profili doğrulama ve durum geçişleri |
| `npm run validate:assembly` | Toplanma alanı, arama ve konum doğrulama |
| `npm run validate:api` | API yanıtları, kimlik eşleme ve geometri doğrulama |

## Klasör Yapısı

```
src/
├── api/                 HTTP istemcisi ve sözleşme eşleyicileri
├── assets/brand/        AFET360 logosu
├── components/
│   ├── common/          BrandLogo, PageContainer
│   ├── layout/          AppLayout, Navbar, Sidebar
│   ├── map/             SVG harita bileşenleri
│   └── simulation/      simülasyon bileşenleri
├── constants/           colors.ts, routes.ts
├── hooks/
├── pages/               6 sayfa bileşeni
└── types/
```

`@/` alias'ı `src/` dizinine karşılık gelir.

## Rotalar

| Yol                  | Sayfa                  |
| -------------------- | ---------------------- |
| `/`                  | Ana Sayfa              |
| `/fault-lines`       | Fay Hatları            |
| `/simulation`        | Deprem Simülasyonu     |
| `/preparedness-guide`| Hazırlık Rehberi        |
| `/assembly-areas`    | Toplanma Alanları      |
| `/about`             | Hakkında               |

## Tasarım Referansları

`docs/ui-reference/` altındaki görseller yalnızca tasarım referansıdır; uygulama
içinde `<img>` olarak kullanılmaz.

## Entegrasyon dokümantasyonu

Mevcut backend sözleşmeleri, özellik bazında kullanılabilirlik, ortam değişkenleri
ve doğrulama sonuçları: [backend-integration.md](docs/backend-integration.md).

## Sınırlar

Frontend yalnızca UI/UX katmanından sorumludur. AFAD, GEM veya benzeri harici
servislere doğrudan bağlanmaz; fay, yakın deprem ve toplanma noktası verilerini
proje backend'i üzerinden alır. Simülasyon hesaplama servisi mevcut değildir.

## Fay Hatları

`/fault-lines`, backend'in döndürdüğü GEM GAF segmentlerini mevcut il haritasıyla
aynı SVG projeksiyonunda gösterir. Harita üzerinden veya seçim
listesinden bir segment seçilebilir; Tab, Enter ve Boşluk klavye kullanımını
destekler. Seçim kalıcı vurgulanır ve bilgi panelini günceller.

Kaynak adları ve kimlikleri korunur. Yakındaki deprem kayıtları backend'in
coğrafi yakınlık sorgusundan gelir; nedensel fay ilişkisi olarak sunulmaz.
Şehir ilişkisi bulunmadığından türetilmez. HomePage geliştirme verisi aynıdır.
Kaynak, lisans, tekrar üretim ve filtreleme ayrıntıları: [data-sources.md](docs/data-sources.md).

## Deprem Simülasyonu — Step 4

`/simulation`, `@vis.gl/react-google-maps` ile Google Maps JavaScript API'yi
gösterir. Kullanıcı haritaya tıkladığında tek bir konum işaretçisi tutulur ve
koordinatlar yalnızca gösterimde dört ondalık basamağa yuvarlanır. Ayarlar
4.0–8.0 Mw büyüklük kaydırıcısı, 5/10/20/30 km derinlik seçenekleri ve
25/50/100/150 km inceleme yarıçapı sunar.

Gerçek anahtarı hiçbir zaman repoya eklemeyin. `.env.local` içinde:

```env
VITE_GOOGLE_MAPS_API_KEY=...
VITE_GOOGLE_MAPS_MAP_ID=... # isteğe bağlı; üretim için önerilir
```

Tarayıcı tabanlı Google Maps anahtarları istemciye teslim edildiği için Google
Cloud Console'da HTTP referrer ve yalnızca Maps JavaScript API kısıtlarıyla
sınırlandırılmalıdır. Anahtar yoksa sayfa harita isteği yapmadan açık bir
yapılandırma durumu gösterir. Harita yalnızca `roadmap`, tıklama ve tek bir
AdvancedMarker kullanır; Places, Geocoding, Directions, geolocation ve benzeri
servisler çağrılmaz.

Başlat düğmesi yerel taslağı doğrular ve sadece backend entegrasyonu bekleniyor
mesajını gösterir. Bir endpoint çağrılmaz, sonuç üretilmez ve veri saklanmaz.
Uygulama/dogrulama ayrıntıları: [simulation-validation.md](docs/simulation-validation.md).
