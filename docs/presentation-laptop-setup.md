# AFET360 — Presentation Laptop Setup & Demo Runbook

This runbook guides team members through setting up and running AFET360 on a presentation laptop (Windows 10/11 x64).

AFET360 runs **completely standalone** on your machine. It does **not** depend on the developer's computer, local network sharing, tunnels (ngrok/SSH), developer database, or external developer credentials.

---

## 1. System Prerequisites

Install the following software on your Windows laptop prior to running the setup script:

1. **Git for Windows**: [git-scm.com](https://git-scm.com/)
2. **Python 3.12 x64**: [python.org](https://www.python.org/downloads/) (ensure *"Add Python to PATH"* is checked during installation)
3. **Node.js 22 LTS**: [nodejs.org](https://nodejs.org/) (includes `npm`)
4. **Docker Desktop**: [docker.com](https://www.docker.com/products/docker-desktop/) (must be running for PostgreSQL/PostGIS)
5. **Ollama**: [ollama.com](https://ollama.com/) (runs the local AI preparedness guide)

> [!NOTE]
> **Disk Space Notice**:
> Initial setup acquires official seismic datasets and local AI models. Ensure at least **10 GB of free disk space** for:
> - GEM GSHM Hazard Map: ~935 MB compressed archive, ~1.76 GB extracted GeoPackage
> - Qwen 2.5 2B Model: ~1.9 GB in Ollama
> - Python virtual environment & Node modules: ~1 GB

---

## 2. One-Time Setup (First Time Only)

### Step 2.1: Clone the Repository
Open PowerShell and clone the repository to your chosen directory:

```powershell
git clone https://github.com/FBmarko/Project_Disaster.git
cd Project_Disaster
```

### Step 2.2: Configure Google Maps Browser API Key
The interactive map requires a restricted Google Maps JavaScript API key.

1. Navigate to the `frontend/` directory and create `.env.local` (copied from `.env.example`):
   ```powershell
   Copy-Item frontend\.env.example frontend\.env.local
   ```
2. Open `frontend\.env.local` in an editor and set your key:
   ```ini
   VITE_GOOGLE_MAPS_API_KEY=AIzaSyYourRestrictedBrowserKeyHere
   ```

> [!IMPORTANT]
> **Key Security & Restrictions**:
> - This key is client-side and loaded by the user's browser.
> - In Google Cloud Console, restrict this key to **HTTP referrers** (e.g., `http://localhost:*` and `http://127.0.0.1:*`).
> - Restrict API scope to **Maps JavaScript API**.
> - **Never** place backend secrets, database passwords, or Google Gemini API keys in `frontend/.env.local`.

*(If you run without this key, the application starts normally with a graceful fallback UI, but interactive map tiles will not render.)*

### Step 2.3: Run the Automated Setup Script
Ensure **Docker Desktop** and **Ollama** are running, then run:

```powershell
.\scripts\demo\setup.ps1 -PullModel
```

#### What `setup.ps1` Does:
- **Validates Prerequisites**: Checks Git, Python 3.12, Node.js, npm, Docker daemon, and Ollama.
- **Sets Up Python Environment**: Creates `backend/.venv` and installs all backend dependencies (`pip install .`).
- **Installs Frontend Packages**: Runs `npm ci` from the committed `package-lock.json`.
- **Starts Database Container**: Launches PostgreSQL 16 with PostGIS 3.4 (`afet360_db`) via Docker Compose.
- **Runs Migrations**: Executes `alembic upgrade head` to configure tables, spatial columns, and PostGIS indexes.
- **Provisions Authoritative Datasets**:
  - Downloads GEM active faults (Turkey scope).
  - Streams GEM Global Seismic Hazard Map (GSHM v2026.1) from official Zenodo (record `20735384`), verifies MD5 checksum (`7470e54534f4a4307a7310aa766ab11b`), extracts, and ingests.
  - Fetches official OpenStreetMap emergency assembly areas for Turkey via Overpass API.
  - Synchronizes rolling 10-year $M \ge 4.5$ earthquake catalog from AFAD over verified HTTPS.
- **Pulls Local AI Model**: Downloads `qwen3.5:2b-q4_K_M` into your local Ollama instance (when `-PullModel` is used). If `-PullModel` is omitted and the model is not installed, setup will halt with an error and instructions.
- **Verifies Readiness Gate**: Runs `python -m app.scripts.provision_datasets status --check` ensuring all tables are `[READY]`.

> [!TIP]
> `setup.ps1` is completely **idempotent**. If your connection drops or setup is interrupted, simply rerun `.\scripts\demo\setup.ps1`. Downloaded caches are MD5-verified and reused.

---

## 3. Presentation Day: Daily Demo Workflow

On presentation day, you **do not** need to redownload data, re-pull models, or rerun installations. Startup is fast and controlled.

### Step 3.1: Start AFET360
Ensure Docker Desktop and Ollama are open, then run:

```powershell
.\scripts\demo\start.ps1
```

#### What `start.ps1` Does:
1. Verifies Docker daemon and ensures the database container is healthy.
2. Runs a fast read-only dataset readiness check (`status --check`).
3. Confirms local Ollama and the `qwen3.5:2b-q4_K_M` model are ready.
4. Checks ports `8000` and `5173` for conflicting processes.
5. Launches FastAPI backend on `http://127.0.0.1:8000` (logged to `%LOCALAPPDATA%\AFET360\demo\logs\backend.log`).
6. Launches Vite frontend on `http://127.0.0.1:5173` (logged to `%LOCALAPPDATA%\AFET360\demo\logs\frontend.log`).
7. Bounded health check waits up to 30 seconds for both services and the API proxy to return `HTTP 200 OK`.
8. Opens `http://127.0.0.1:5173` in your default browser.

### Step 3.2: Presentation URLs
- **Web Application**: [http://127.0.0.1:5173](http://127.0.0.1:5173)
- **Interactive Swagger API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Runtime Logs**: `%LOCALAPPDATA%\AFET360\demo\logs\`

### Step 3.3: Stop AFET360 After the Presentation
When the presentation or testing session is complete, run:

```powershell
.\scripts\demo\stop.ps1
```

#### What `stop.ps1` Does:
- Identifies the exact PIDs of the backend and frontend processes tracked during `start.ps1`.
- Verifies process identity to prevent accidentally killing unrelated processes.
- Terminates the backend and frontend process trees cleanly.
- **Preserves PostgreSQL data**: The database container remains intact so your provisioned data survives.

---

## 4. Useful Helper Commands

### Check Runtime Status
Check if AFET360 processes are currently active without launching anything:
```powershell
.\scripts\demo\start.ps1 -Status
```

### Start Without Opening Browser
```powershell
.\scripts\demo\start.ps1 -NoBrowser
```

---

## 5. Troubleshooting & FAQ

| Problem | Cause | Solution |
| :--- | :--- | :--- |
| `Docker Desktop or Docker daemon is not running` | Docker service not started | Open Docker Desktop from the Windows Start Menu, wait for the whale icon to stabilize, then rerun script. |
| `Port 8000 is already in use` | Another process is occupying port 8000 | The script identifies the PID occupying port 8000. Stop that application or close previous terminal windows. |
| `Local Ollama is not responding` | Ollama daemon is closed | Run `ollama run qwen3.5:2b-q4_K_M` in PowerShell or start Ollama from the Windows system tray. |
| `Google Maps shows "Missing Key" banner` | `VITE_GOOGLE_MAPS_API_KEY` not configured | Verify `frontend/.env.local` contains a valid key and restart via `.\scripts\demo\stop.ps1` followed by `.\scripts\demo\start.ps1`. |
| `Dataset readiness check failed` | Datasets were not provisioned | Run `.\scripts\demo\setup.ps1` to complete initial dataset ingestion. |
