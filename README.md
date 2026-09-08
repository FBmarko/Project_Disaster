# AFET360

AFET360, doğal afetlere karşı hazırlık ve farkındalık sağlamayı amaçlayan yapay zekâ destekli web platformudur.

## Proje Yapısı

- `frontend/` — React + TypeScript kullanıcı arayüzü
- `backend/` — API, veritabanı, yapay zekâ ve servis katmanı

## Ekip

Proje 3 kişilik bir ekip tarafından geliştirilmektedir.

### Görev Dağılımı

- Kişi 1 — Frontend / UI / UX
- Kişi 2 — Harita / Afet Simülasyonu
- Kişi 3 — Backend / API / Database / AI

## Durum

Proje geliştirme aşamasındadır.

## Sunum & Demo Kurulumu (Presentation Setup)

Ekip üyelerinin kendi bilgisayarlarında AFET360'ı bağımsız olarak kurup sunabilmesi için hazırlanmış kılavuz ve scriptler:

- **Runbook**: [`docs/presentation-laptop-setup.md`](docs/presentation-laptop-setup.md)
- **İlk Kurulum**: `.\scripts\demo\setup.ps1`
- **Demo Başlat**: `.\scripts\demo\start.ps1`
- **Demo Durdur**: `.\scripts\demo\stop.ps1`

## Canlı Sunucu & Production Kurulumu (Production Deployment)

AFET360'ın bağımsız bir Linux sunucusunda Caddy ters vekili (reverse proxy), Docker Compose ve PostGIS ile canlıya alınması için hazırlanmış kılavuz:

- **Production Runbook**: [`docs/production-deployment.md`](docs/production-deployment.md)
- **Production Compose**: `docker-compose.prod.yml`
- **Environment Şablonu**: `deploy/.env.production.example`
