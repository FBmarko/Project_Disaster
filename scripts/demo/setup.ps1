# scripts/demo/setup.ps1
# AFET360 — Presentation Laptop One-Time Setup Script
# Orchestrates prerequisite validation, environment setup, database migrations,
# dataset provisioning, and readiness checks on a clean Windows machine.

[CmdletBinding()]
param(
    [switch]$PullModel,
    [switch]$SkipDataProvisioning
)

$ErrorActionPreference = "Stop"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "          AFET360 Presentation Laptop One-Time Setup           " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""

# -----------------------------------------------------------------------------
# 1. Resolve Repository Paths
# -----------------------------------------------------------------------------
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"

Write-Host "[INFO] Repository Root: $RepoRoot" -ForegroundColor Gray
Write-Host "[INFO] Backend Path:    $BackendDir" -ForegroundColor Gray
Write-Host "[INFO] Frontend Path:   $FrontendDir" -ForegroundColor Gray
Write-Host ""

# -----------------------------------------------------------------------------
# 2. Prerequisite Checks
# -----------------------------------------------------------------------------
Write-Host "--- Step 1: Checking System Prerequisites ---" -ForegroundColor Yellow

# Git Check
try {
    $gitVer = (git --version 2>&1).Trim()
    Write-Host "[OK] Git detected: $gitVer" -ForegroundColor Green
} catch {
    Write-Error "Git is not installed or not found in PATH. Please install Git for Windows."
    exit 1
}

# Python 3.12 Check
try {
    $pyVerRaw = (python --version 2>&1).Trim()
    if ($pyVerRaw -match "Python (\d+)\.(\d+)\.(\d+)") {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        if ($major -eq 3 -and $minor -eq 12) {
            Write-Host "[OK] Python 3.12 detected: $pyVerRaw" -ForegroundColor Green
        } else {
            Write-Error "Python 3.12 is required (found $pyVerRaw). Please install Python 3.12 x64."
            exit 1
        }
    } else {
        Write-Error "Unable to parse Python version string: $pyVerRaw. Python 3.12 is required."
        exit 1
    }
} catch {
    Write-Error "Python is not installed or not found in PATH. Please install Python 3.12 x64."
    exit 1
}

# Node.js Check
try {
    $nodeVerRaw = (node --version 2>&1).Trim()
    if ($nodeVerRaw -match "v(\d+)\.") {
        $nodeMajor = [int]$matches[1]
        if ($nodeMajor -eq 22) {
            Write-Host "[OK] Node.js 22 LTS detected: $nodeVerRaw" -ForegroundColor Green
        } elseif ($nodeMajor -ge 20) {
            Write-Warning "Node.js $nodeVerRaw detected. Node 22 LTS is canonical, but $nodeVerRaw will be used."
        } else {
            Write-Error "Node.js 20+ (preferably 22 LTS) is required. Found: $nodeVerRaw."
            exit 1
        }
    }
} catch {
    Write-Error "Node.js is not installed or not found in PATH. Please install Node.js 22 LTS."
    exit 1
}

# npm Check
try {
    $npmVer = (npm --version 2>&1).Trim()
    Write-Host "[OK] npm detected: v$npmVer" -ForegroundColor Green
} catch {
    Write-Error "npm is not installed or not found in PATH."
    exit 1
}

# Docker & Docker Compose Check
try {
    $dockerVer = (docker --version 2>&1).Trim()
    $composeVer = (docker compose version 2>&1).Trim()
    Write-Host "[OK] Docker CLI detected: $dockerVer ($composeVer)" -ForegroundColor Green
} catch {
    Write-Error "Docker or Docker Compose is not installed or not found in PATH."
    exit 1
}

# Docker Daemon Reachability Check
$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker Desktop or Docker daemon is not running. Please start Docker Desktop normally, then rerun setup."
    exit 1
}
Write-Host "[OK] Docker daemon is running and reachable." -ForegroundColor Green

# Ollama Executable & Service Check
$ollamaInstalled = $false
try {
    $ollamaVer = (ollama --version 2>&1).Trim()
    Write-Host "[OK] Ollama CLI detected: $ollamaVer" -ForegroundColor Green
    $ollamaInstalled = $true
} catch {
    Write-Error "Ollama CLI was not found in PATH. Please install Ollama from https://ollama.com/ and ensure it is in PATH."
    exit 1
}

$ollamaReachable = $false
$modelInstalled = $false
try {
    $tagsResponse = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 3 -ErrorAction Stop
    $ollamaReachable = $true
    Write-Host "[OK] Ollama daemon is reachable on localhost:11434." -ForegroundColor Green

    if ($tagsResponse -and $tagsResponse.models) {
        $modelNames = $tagsResponse.models | ForEach-Object { $_.name }
        if ($modelNames -contains "qwen3.5:2b-q4_K_M" -or ($modelNames -match "qwen3.5:2b-q4_K_M")) {
            $modelInstalled = $true
            Write-Host "[OK] Required model 'qwen3.5:2b-q4_K_M' is installed in Ollama." -ForegroundColor Green
        }
    }
} catch {
    Write-Error "Ollama daemon is not reachable at http://127.0.0.1:11434. Please start Ollama before running setup."
    exit 1
}

if (-not $modelInstalled) {
    if ($PullModel) {
        Write-Host "[INFO] Pulling model 'qwen3.5:2b-q4_K_M' via Ollama (~1.9 GB)..." -ForegroundColor Cyan
        & ollama pull qwen3.5:2b-q4_K_M
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Successfully pulled 'qwen3.5:2b-q4_K_M'." -ForegroundColor Green
            $modelInstalled = $true
        } else {
            Write-Error "Failed to pull 'qwen3.5:2b-q4_K_M'. Run manually: ollama pull qwen3.5:2b-q4_K_M"
            exit 1
        }
    } else {
        Write-Error "Required model 'qwen3.5:2b-q4_K_M' is not installed in Ollama.`nTo install, run: ollama pull qwen3.5:2b-q4_K_M`nOr rerun setup with the -PullModel switch: .\scripts\demo\setup.ps1 -PullModel"
        exit 1
    }
}

# Map Visualization Check: MapLibre GL JS + OpenFreeMap requires no API keys
Write-Host "[OK] Map visualization: MapLibre GL JS + OpenFreeMap (no API key required)." -ForegroundColor Green
Write-Host ""


# -----------------------------------------------------------------------------
# 3. Python Virtual Environment & Dependencies
# -----------------------------------------------------------------------------
Write-Host "--- Step 2: Setting up Python Virtual Environment ---" -ForegroundColor Yellow

$VenvDir = Join-Path $BackendDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[INFO] Creating Python 3.12 virtual environment at $VenvDir..." -ForegroundColor Cyan
    & python -m venv $VenvDir
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPython)) {
        Write-Error "Failed to create Python virtual environment at $VenvDir."
        exit 1
    }
    Write-Host "[OK] Virtual environment created successfully." -ForegroundColor Green
} else {
    Write-Host "[OK] Existing virtual environment found at $VenvDir." -ForegroundColor Green
}

Write-Host "[INFO] Installing backend dependencies into virtual environment (pip install .)..." -ForegroundColor Cyan
Push-Location $BackendDir
try {
    & $VenvPython -m pip install --quiet --upgrade pip
    & $VenvPython -m pip install .
    if ($LASTEXITCODE -ne 0) {
        Write-Error "pip install failed for backend dependencies."
        exit 1
    }
    Write-Host "[OK] Backend dependencies installed." -ForegroundColor Green
} finally {
    Pop-Location
}

Write-Host ""

# -----------------------------------------------------------------------------
# 4. Frontend Dependencies
# -----------------------------------------------------------------------------
Write-Host "--- Step 3: Installing Frontend Dependencies ---" -ForegroundColor Yellow
Write-Host "[INFO] Running 'npm ci' from package-lock.json..." -ForegroundColor Cyan

Push-Location $FrontendDir
try {
    & npm ci
    if ($LASTEXITCODE -ne 0) {
        Write-Error "npm ci failed for frontend dependencies."
        exit 1
    }
    Write-Host "[OK] Frontend dependencies installed successfully." -ForegroundColor Green
} finally {
    Pop-Location
}

Write-Host ""

# -----------------------------------------------------------------------------
# 5. Database Startup & Readiness Loop
# -----------------------------------------------------------------------------
Write-Host "--- Step 4: Starting PostgreSQL/PostGIS Database ---" -ForegroundColor Yellow
Write-Host "[INFO] Starting database container 'afet360_db' via Docker Compose..." -ForegroundColor Cyan

Push-Location $RepoRoot
try {
    & docker compose up -d db
    if ($LASTEXITCODE -ne 0) {
        Write-Error "docker compose up -d db failed."
        exit 1
    }
} finally {
    Pop-Location
}

Write-Host "[INFO] Waiting for PostgreSQL/PostGIS to accept connections (up to 60s)..." -ForegroundColor Cyan
$dbReady = $false
$timeout = [DateTime]::UtcNow.AddSeconds(60)
while ([DateTime]::UtcNow -lt $timeout) {
    $probe = docker compose exec db pg_isready -U afet360 -d afet360 2>&1
    if ($LASTEXITCODE -eq 0) {
        $dbReady = $true
        break
    }
    Start-Sleep -Seconds 2
}

if (-not $dbReady) {
    Write-Error "PostgreSQL/PostGIS failed to become ready within 60 seconds."
    exit 1
}
Write-Host "[OK] PostgreSQL/PostGIS database is ready." -ForegroundColor Green

Write-Host ""

# -----------------------------------------------------------------------------
# 6. Database Migrations (Alembic)
# -----------------------------------------------------------------------------
Write-Host "--- Step 5: Applying Database Migrations ---" -ForegroundColor Yellow
Write-Host "[INFO] Running 'alembic upgrade head'..." -ForegroundColor Cyan

Push-Location $BackendDir
try {
    & $VenvPython -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Database migrations failed."
        exit 1
    }
    Write-Host "[OK] Database migrations applied to head." -ForegroundColor Green
} finally {
    Pop-Location
}

Write-Host ""

# -----------------------------------------------------------------------------
# 7. Dataset Provisioning & AFAD Synchronization
# -----------------------------------------------------------------------------
Write-Host "--- Step 6: Dataset Provisioning & Synchronization ---" -ForegroundColor Yellow

if ($SkipDataProvisioning) {
    Write-Host "[INFO] Skipping dataset acquisition (-SkipDataProvisioning was specified)." -ForegroundColor Yellow
} else {
    Write-Host "[NOTICE] Static dataset provisioning will download:" -ForegroundColor Cyan
    Write-Host "         1. GEM Active Faults (GAF GeoJSON)" -ForegroundColor Cyan
    Write-Host "         2. GEM Global Seismic Hazard Map (GSHM v2026.1 from Zenodo: ~935 MB archive, ~1.76 GB GeoPackage)" -ForegroundColor Cyan
    Write-Host "         3. OSM Emergency Assembly Areas (Overpass API snapshot)" -ForegroundColor Cyan
    Write-Host "         Please be patient; download and checksum verification may take several minutes." -ForegroundColor Cyan
    Write-Host ""

    Push-Location $BackendDir
    try {
        & $VenvPython -m app.scripts.provision_datasets provision-static --download-all
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Static dataset provisioning failed. You can safely rerun .\scripts\demo\setup.ps1 to resume."
            exit 1
        }
        Write-Host "[OK] Static datasets provisioned and verified." -ForegroundColor Green

        Write-Host "[INFO] Synchronizing initial AFAD earthquake catalog (M >= 4.5 rolling window)..." -ForegroundColor Cyan
        & $VenvPython -m app.scripts.sync_afad_earthquakes --min-magnitude 4.5 --scope turkey-context
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Initial AFAD earthquake sync failed. Check network connection and rerun setup."
            exit 1
        }
        Write-Host "[OK] Initial AFAD earthquake catalog synchronized." -ForegroundColor Green
    } finally {
        Pop-Location
    }
}

Write-Host ""

# -----------------------------------------------------------------------------
# 8. Dataset Readiness Gate
# -----------------------------------------------------------------------------
Write-Host "--- Step 7: Final Dataset Readiness Check ---" -ForegroundColor Yellow

Push-Location $BackendDir
try {
    & $VenvPython -m app.scripts.provision_datasets status --check
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Dataset readiness check failed. Not all required datasets are ready."
        exit 1
    }
    Write-Host "[OK] All required datasets are READY in PostgreSQL/PostGIS." -ForegroundColor Green
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "=================================================================" -ForegroundColor Green
Write-Host "         ONE-TIME SETUP COMPLETED SUCCESSFULLY!                  " -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps for presentation:" -ForegroundColor White
Write-Host "  1. Ensure local Ollama is running with qwen3.5:2b-q4_K_M:" -ForegroundColor Gray
Write-Host "     ollama run qwen3.5:2b-q4_K_M" -ForegroundColor Gray
Write-Host "  2. Start the application simply using:" -ForegroundColor White
Write-Host "     .\scripts\demo\start.ps1" -ForegroundColor Yellow
Write-Host "  3. Stop the application after presentation using:" -ForegroundColor White
Write-Host "     .\scripts\demo\stop.ps1" -ForegroundColor Yellow

Write-Host ""
