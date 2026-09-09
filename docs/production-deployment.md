# AFET360 — Production Web Deployment & Operations Runbook

This document provides the authoritative, step-by-step guide for deploying AFET360 to a self-hosted Linux production server using Docker Compose and the Caddy same-origin reverse proxy.

---

## 1. Production Architecture Overview

The production deployment consists of an isolated, containerized stack:

```text
Internet (Users / Browsers)
       │
  ports 80 / 443 (Public)
       ▼
┌─────────────────────────────────────────────────────────┐
│ Caddy Reverse Proxy & Web Server (web)                  │
│  - Automatic ACME TLS / HTTPS                           │
│  - Serves static React/Vite SPA bundle (HTML fallback)  │
│  - Same-origin routing:                                 │
│      /api/*        ──► FastAPI :8000                    │
│      /openapi.json ──► FastAPI :8000                    │
│      /docs*        ──► FastAPI :8000                    │
│      /redoc*       ──► FastAPI :8000                    │
└──────────────┬──────────────────────────────────────────┘
               │ Internal Docker Network (prod_network)
       ┌───────┴───────────────────┬──────────────────────┐
       ▼                           ▼                      ▼
┌──────────────┐            ┌──────────────┐       ┌──────────────┐
│ FastAPI :8000│            │PostGIS 16-3.4│       │Ollama :11434 │
│ (api)        │            │ (db)         │       │ (ollama)     │
│ - Rate limits│            │ - Persistent │       │ - Model cache│
│ - Security   │            │   storage    │       │   (optional  │
│ - OpenAPI 17 │            │ - Unexposed  │       │    profile)  │
└──────────────┘            └──────────────┘       └──────────────┘
```

### Network & Port Exposure Policy

| Service | Container Port | Host / Public Exposure | Access Control |
| :--- | :--- | :--- | :--- |
| **Caddy (`web`)** | 80, 443 | **Public (80, 443)** | Internet traffic |
| **FastAPI (`api`)** | 8000 | **Internal only** | Reachable only via `web` on `prod_network` |
| **PostGIS (`db`)** | 5432 | **Internal only** | Reachable only via `api` on `prod_network` |
| **Ollama (`ollama`)** | 11434 | **Internal only** | Reachable only via `api` on `prod_network` |

### TLS, HTTPS & HSTS Policy

- **Automatic ACME TLS & HTTPS Redirect**: When configured with an external domain name (`SITE_ADDRESS`), Caddy automatically provisions and renews ACME TLS certificates (Let's Encrypt / ZeroSSL) and automatically redirects inbound port 80 HTTP traffic to port 443 HTTPS.
- **HSTS (Strict-Transport-Security)**: **NOT CONFIGURED / DEFERRED**. HSTS is deliberately deferred until final public release domain and subdomain routing are selected. Automatic HTTPS must not be confused with HSTS. Unconditional HSTS headers should not be deployed prematurely during testing or staging to avoid locking domain names into browser HSTS preload caches.
- **Forwarded Header Trust Boundary**: FastAPI trusts reverse-proxy forwarded headers exclusively on the internal network boundary via Compose configuration (`FORWARDED_ALLOW_IPS=*`). Host port 8000 is never host-published.

---

## 2. Server Prerequisites

A Linux x86_64 server (Ubuntu 22.04 LTS or 24.04 LTS recommended) equipped with:

- **Docker Engine**: Version 24.0 or newer
- **Docker Compose**: Version 2.20 or newer (`docker compose` v2 syntax)
- **Git**: Installed and available in PATH
- **Network**: Inbound ports `80` (HTTP) and `443` (HTTPS) open on server firewall; outbound access for dataset downloads and API providers
- **DNS**: Fully Qualified Domain Name (FQDN) pointed to the server's public IPv4 address (e.g., `afet360.example.com`)

---

## 3. Deployment Steps

### Step 1: Clone the Canonical Repository

```bash
git clone https://github.com/FBmarko/Project_Disaster.git /opt/afet360
cd /opt/afet360
```

### Step 2: Configure Production Environment

Create the production environment file from the committed example:

```bash
cp deploy/.env.production.example deploy/.env.production
chmod 600 deploy/.env.production
```

Edit `deploy/.env.production` with your real production values:

```bash
nano deploy/.env.production
```

Required settings:
1. **Map Visualization (MapLibre GL JS + OpenFreeMap)**: No application API key, Google Cloud account, or billing setup is required. AFET360 renders vector map tiles directly from public OpenFreeMap (based on OpenStreetMap data). Note: Public OpenFreeMap is an external tile service without a commercial SLA guarantee; client internet access is required to fetch vector tiles.
2. **`POSTGRES_PASSWORD`**: Set a strong, randomly generated database password.
3. **`SITE_ADDRESS`**: Set your public HTTPS domain, e.g., `https://afet360.example.com`.
4. **`AI_PROVIDER`**: Choose `ollama` (default local) or `gemini` (cloud API).
   - If using `gemini`: set `GEMINI_API_KEY=your-gemini-key`.
   - If using `ollama`: keep `OLLAMA_BASE_URL=http://ollama:11434`.


> **Authoritative Configuration Loading:** Docker Compose natively loads configuration via the `--env-file deploy/.env.production` flag passed to all commands below. Do not export production secrets into your interactive shell environment, and do not copy or symlink production secrets to the repository root `.env`.

### Step 3: Build Production Images

```bash
# Build backend and frontend/web images
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml build
```

### Step 4: Start Database & Apply Migrations

Start PostGIS and the backend container:

```bash
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml up -d db api
```

The `api` container entrypoint (`backend/docker-entrypoint.sh`) automatically verifies database connectivity and applies all pending Alembic migrations (`alembic upgrade head`).

### Step 5: Provision Disaster Datasets (One-Time Operator Action)

Provision required static datasets (GEM Faults, Zenodo GSHM v2026.1, OSM Assembly Points) directly inside the running API container:

```bash
# Download and ingest static datasets
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml exec api \
    python -m app.scripts.provision_datasets provision-static --download-all

# Synchronize historical earthquake catalog (M >= 4.5, Turkey context)
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml exec api \
    python -m app.scripts.sync_afad_earthquakes --min-magnitude 4.5 --scope turkey-context

# Verify full dataset readiness
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml exec api \
    python -m app.scripts.provision_datasets status --check
```

Expected output: `Overall Status: READY` (exit code `0`).

### Step 6: Provision AI Model (If using local Ollama)

If `AI_PROVIDER=ollama` is selected, start the Ollama container and pull the required Qwen model:

```bash
# Start Ollama service using the compose profile
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml --profile ollama up -d ollama

# Explicitly pull the approved 2B Q4 model
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml exec ollama \
    ollama pull qwen3.5:2b-q4_K_M
```

### Step 7: Launch Full Stack

```bash
# If using Ollama:
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml --profile ollama up -d

# If using Gemini:
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml up -d
```

---

## 4. Operational Verification

1. **Backend Health Check**:
   ```bash
   curl -fsS https://afet360.example.com/api/v1/health
   # Expected: HTTP 200 OK
   # Response body: {"status": "ok", "service": "AFET360 API", "version": "0.1.0"}
   ```

2. **OpenAPI Schema Check**:
   ```bash
   curl -s https://afet360.example.com/openapi.json | grep -o '"paths":'
   # Expected: OpenAPI schema with 17 paths
   ```

3. **Interactive Documentation**:
   Navigate to `https://afet360.example.com/docs` in your browser.

4. **Frontend Root & SPA Fallback**:
   Navigate to `https://afet360.example.com/` and deep links like `https://afet360.example.com/scenario`. The React application should render without blank screens.

5. **Map Visualization Check**:
   Verify the interactive MapLibre map component renders OpenFreeMap dark vector tiles correctly in simulation and assembly areas. If the fallback placeholder appears, verify client internet access to `https://tiles.openfreemap.org`.


---

## 5. Maintenance & Safe Update Procedure

To update AFET360 to a new release without data loss:

```bash
cd /opt/afet360

# 1. Fetch latest release tag or approved commit
git fetch origin
git checkout <RELEASE_TAG_OR_COMMIT>

# 2. Rebuild images with new code
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml build

# 3. Apply updates with zero downtime / fast recreation
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml up -d
```

> **WARNING:** Never run `docker compose down -v`. The `-v` flag deletes named Docker volumes, destroying the PostGIS database, Caddy TLS certificates, and the dataset cache.

---

## 6. Database Backup & Restore

### Backup (Logical Dump)

```bash
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml exec -T db \
    sh -lc 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > /opt/backups/afet360_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Restore

```bash
gunzip -c /opt/backups/afet360_backup.sql.gz | \
    docker compose --env-file deploy/.env.production -f docker-compose.prod.yml exec -T db \
    sh -lc 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'
```

---

## 7. Troubleshooting

- **Check container status**:
  ```bash
  docker compose --env-file deploy/.env.production -f docker-compose.prod.yml ps
  ```
- **Inspect Caddy logs**:
  ```bash
  docker compose --env-file deploy/.env.production -f docker-compose.prod.yml logs -f web
  ```
- **Inspect API logs**:
  ```bash
  docker compose --env-file deploy/.env.production -f docker-compose.prod.yml logs -f api
  ```
- **Caddy Certificate Issues**:
  Ensure port `80` and `443` are reachable from the public internet. Let's Encrypt requires port `80` for HTTP-01 ACME challenges.
