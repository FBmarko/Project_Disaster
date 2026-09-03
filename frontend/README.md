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

## Klasör Yapısı

```
src/
├── api/                 backend istemcisi (ileride)
├── assets/brand/        AFET360 logosu
├── components/
│   ├── common/          BrandLogo, PageContainer
│   ├── layout/          AppLayout, Navbar, Sidebar
│   ├── map/             harita bileşenleri (ileride)
│   └── simulation/      simülasyon bileşenleri (ileride)
├── constants/           colors.ts, routes.ts
├── hooks/
├── pages/               5 sayfa bileşeni
├── services/
└── types/
```

`@/` alias'ı `src/` dizinine karşılık gelir.

## Rotalar

| Yol                  | Sayfa                  |
| -------------------- | ---------------------- |
| `/`                  | Ana Sayfa              |
| `/fault-lines`       | Fay Hatları            |
| `/simulation`        | Deprem Simülasyonu     |
| `/simulation-results`| Simülasyon Sonuçları   |
| `/about`             | Hakkında               |

## Tasarım Referansları

`docs/ui-reference/` altındaki görseller yalnızca tasarım referansıdır; uygulama
içinde `<img>` olarak kullanılmaz.

## Sınırlar

Frontend yalnızca UI/UX katmanından sorumludur. AFAD, GEM veya benzeri harici
servislere doğrudan bağlanmaz; deprem/fay verisi ileride proje backend'i
üzerinden sağlanacaktır. Risk hesaplama ve simülasyon algoritmaları backend
tarafındadır.
