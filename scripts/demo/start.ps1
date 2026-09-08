# scripts/demo/start.ps1
# AFET360 — Controlled Presentation Demo Start Script
# Starts PostgreSQL/PostGIS, verifies dataset readiness, launches backend and frontend
# with localized logging and process tracking, verifies health, and launches browser.

[CmdletBinding()]
param(
    [switch]$NoBrowser,
    [switch]$Status
)

$ErrorActionPreference = "Stop"

# -----------------------------------------------------------------------------
# 1. Resolve Paths & Runtime State Directory
# -----------------------------------------------------------------------------
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"

$VenvDir = Join-Path $BackendDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

$StateDir = Join-Path $env:LOCALAPPDATA "AFET360\demo"
$LogsDir = Join-Path $StateDir "logs"
$StateFile = Join-Path $StateDir "state.json"

if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

# -----------------------------------------------------------------------------
# 2. Strict Process Identity Verification Functions
# -----------------------------------------------------------------------------
function Test-BackendIdentity([int]$targetPid, [object]$state) {
    $proc = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
    if (-not $proc) {
        return $false
    }
    $cimProc = Get-CimInstance Win32_Process -Filter "ProcessId = $targetPid" -ErrorAction SilentlyContinue
    if (-not $cimProc) {
        return $false
    }
    $cmd = $cimProc.CommandLine
    if ([string]::IsNullOrWhiteSpace($cmd)) {
        return $false
    }

    # Must contain uvicorn and app.main:app
    $hasUvicorn = ($cmd -match "uvicorn") -and ($cmd -match "app\.main:app")

    # Must reference either the backend directory, python venv, or port 8000
    $hasPortOrDir = ($cmd -match "8000") -or ($cmd -match [regex]::Escape($state.backend_working_dir)) -or ($cmd -match "\.venv")

    # Process creation timestamp validation (within 15s tolerance)
    $timeMatches = $true
    if ($state.backend_start_time -and $cimProc.CreationDate) {
        try {
            $expectedTime = [DateTime]::Parse($state.backend_start_time).ToUniversalTime()
            $actualTime = $cimProc.CreationDate.ToUniversalTime()
            $diffSeconds = [Math]::Abs(($actualTime - $expectedTime).TotalSeconds)
            if ($diffSeconds -gt 15) {
                $timeMatches = $false
            }
        } catch {}
    }

    return ($hasUvicorn -and $hasPortOrDir -and $timeMatches)
}

function Test-FrontendIdentity([int]$targetPid, [object]$state) {
    $proc = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
    if (-not $proc) {
        return $false
    }
    $cimProc = Get-CimInstance Win32_Process -Filter "ProcessId = $targetPid" -ErrorAction SilentlyContinue
    if (-not $cimProc) {
        return $false
    }
    $cmd = $cimProc.CommandLine
    if ([string]::IsNullOrWhiteSpace($cmd)) {
        return $false
    }

    # Must match project-local npm run dev or vite launch
    $hasDevOrVite = ($cmd -match "npm" -and $cmd -match "dev") -or ($cmd -match "vite") -or ($cmd -match "5173")

    # Must match frontend directory, repo root, or port 5173
    $hasDir = ($cmd -match [regex]::Escape($state.frontend_working_dir)) -or ($cmd -match "frontend") -or ($cmd -match "5173")

    # Start time check
    $timeMatches = $true
    if ($state.frontend_start_time -and $cimProc.CreationDate) {
        try {
            $expectedTime = [DateTime]::Parse($state.frontend_start_time).ToUniversalTime()
            $actualTime = $cimProc.CreationDate.ToUniversalTime()
            $diffSeconds = [Math]::Abs(($actualTime - $expectedTime).TotalSeconds)
            if ($diffSeconds -gt 15) {
                $timeMatches = $false
            }
        } catch {}
    }

    return ($hasDevOrVite -and $hasDir -and $timeMatches)
}

function Stop-VerifiedProcessTree([int]$targetPid) {
    # Recursively stop children of the verified root process
    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $targetPid" -ErrorAction SilentlyContinue
    if ($children) {
        foreach ($child in $children) {
            Stop-VerifiedProcessTree -targetPid $child.ProcessId
        }
    }
    try {
        Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
    } catch {}
}

# -----------------------------------------------------------------------------
# 3. Status Mode (-Status)
# -----------------------------------------------------------------------------
if ($Status) {
    Write-Host "=== AFET360 Demo Runtime Status ===" -ForegroundColor Cyan
    if (Test-Path $StateFile) {
        try {
            $state = Get-Content $StateFile -Raw | ConvertFrom-Json
            $bAlive = $false
            $fAlive = $false
            if ($state.backend_pid) {
                $bAlive = Test-BackendIdentity -targetPid $state.backend_pid -state $state
            }
            if ($state.frontend_pid) {
                $fAlive = Test-FrontendIdentity -targetPid $state.frontend_pid -state $state
            }

            Write-Host "Started At:    $($state.started_at)" -ForegroundColor White
            Write-Host "Backend PID:   $($state.backend_pid) (Verified & Alive: $bAlive)" -ForegroundColor $(if ($bAlive) { "Green" } else { "Red" })
            Write-Host "Frontend PID:  $($state.frontend_pid) (Verified & Alive: $fAlive)" -ForegroundColor $(if ($fAlive) { "Green" } else { "Red" })
            Write-Host "Logs Location: $LogsDir" -ForegroundColor Gray

            # Test endpoints
            try {
                $bHealth = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health" -TimeoutSec 2 -ErrorAction Stop
                Write-Host "Backend API:   ONLINE (http://127.0.0.1:8000/api/v1/health)" -ForegroundColor Green
            } catch {
                Write-Host "Backend API:   OFFLINE / UNRESPONSIVE" -ForegroundColor Red
            }
            try {
                $fHealth = Invoke-WebRequest -Uri "http://127.0.0.1:5173/" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
                Write-Host "Frontend UI:   ONLINE (http://127.0.0.1:5173)" -ForegroundColor Green
            } catch {
                Write-Host "Frontend UI:   OFFLINE / UNRESPONSIVE" -ForegroundColor Red
            }
            exit 0
        } catch {
            Write-Warning "Could not read state file ${StateFile}: $_"
        }
    }
    Write-Host "AFET360 is not currently running." -ForegroundColor Yellow
    exit 0
}

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "             AFET360 Presentation Demo Launcher                 " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""

# -----------------------------------------------------------------------------
# 4. Check if Already Running (Idempotence with Process Verification)
# -----------------------------------------------------------------------------
if (Test-Path $StateFile) {
    try {
        $existingState = Get-Content $StateFile -Raw | ConvertFrom-Json
        $backendVerified = $false
        if ($existingState.backend_pid) {
            $backendVerified = Test-BackendIdentity -targetPid $existingState.backend_pid -state $existingState
        }

        if ($backendVerified) {
            try {
                $testResp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health" -TimeoutSec 2 -ErrorAction Stop
                if ($testResp.status -eq "ok") {
                    Write-Host "[INFO] AFET360 is already running and healthy!" -ForegroundColor Green
                    Write-Host "       Backend PID:  $($existingState.backend_pid)" -ForegroundColor White
                    Write-Host "       Frontend PID: $($existingState.frontend_pid)" -ForegroundColor White
                    Write-Host "       Frontend URL: http://127.0.0.1:5173" -ForegroundColor Yellow
                    Write-Host "       API Docs:     http://127.0.0.1:8000/docs" -ForegroundColor Yellow
                    exit 0
                }
            } catch {
                Write-Warning "State file exists and PID matched but backend is unresponsive. Cleaning stale state..."
            }
        } else {
            Write-Warning "State file exists but stored PID does not match AFET360 process identity. Discarding stale state."
        }
    } catch {
        Write-Warning "Existing state file could not be parsed. Removing..."
    }
    Remove-Item -Path $StateFile -Force -ErrorAction SilentlyContinue
}

# -----------------------------------------------------------------------------
# 5. Environment & Virtualenv Validation
# -----------------------------------------------------------------------------
if (-not (Test-Path $VenvPython)) {
    Write-Error "Python virtual environment not found at $VenvDir. Please run .\scripts\demo\setup.ps1 first."
    exit 1
}

# -----------------------------------------------------------------------------
# 6. Port Availability Guard
# -----------------------------------------------------------------------------
$port8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($port8000) {
    $owner = ($port8000 | Select-Object -First 1).OwningProcess
    Write-Error "Port 8000 is already in use by process PID $owner. Please terminate that process before starting AFET360."
    exit 1
}

$port5173 = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($port5173) {
    $owner = ($port5173 | Select-Object -First 1).OwningProcess
    Write-Error "Port 5173 is already in use by process PID $owner. Please terminate that process before starting AFET360."
    exit 1
}

# -----------------------------------------------------------------------------
# 7. Database Startup & Health
# -----------------------------------------------------------------------------
Write-Host "[1/6] Verifying PostgreSQL/PostGIS database..." -ForegroundColor Yellow

$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker Desktop is not running. Please start Docker Desktop before running the demo."
    exit 1
}

Push-Location $RepoRoot
try {
    & docker compose up -d db
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to start database container via docker compose up -d db."
        exit 1
    }
} finally {
    Pop-Location
}

# Bounded wait for DB health (up to 30s)
$dbReady = $false
$timeout = [DateTime]::UtcNow.AddSeconds(30)
while ([DateTime]::UtcNow -lt $timeout) {
    $probe = docker compose exec db pg_isready -U afet360 -d afet360 2>&1
    if ($LASTEXITCODE -eq 0) {
        $dbReady = $true
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $dbReady) {
    Write-Error "PostgreSQL/PostGIS database container failed to respond within 30 seconds."
    exit 1
}
Write-Host "      [OK] Database is healthy and listening on port 5432." -ForegroundColor Green

# -----------------------------------------------------------------------------
# 8. Fast Dataset Readiness Check
# -----------------------------------------------------------------------------
Write-Host "[2/6] Checking dataset readiness..." -ForegroundColor Yellow

Push-Location $BackendDir
try {
    & $VenvPython -m app.scripts.provision_datasets status --check
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Datasets are not ready. Please run .\scripts\demo\setup.ps1 to provision required datasets."
        exit 1
    }
    Write-Host "      [OK] Datasets (faults, hazard, assembly, earthquakes) are READY." -ForegroundColor Green
} finally {
    Pop-Location
}

# -----------------------------------------------------------------------------
# 9. Local Ollama & Model Verification
# -----------------------------------------------------------------------------
Write-Host "[3/6] Verifying local Ollama AI provider..." -ForegroundColor Yellow

$ollamaAvailable = $false
try {
    $tags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 3 -ErrorAction Stop
    $ollamaAvailable = $true
    $modelNames = $tags.models | ForEach-Object { $_.name }
    if ($modelNames -contains "qwen3.5:2b-q4_K_M" -or ($modelNames -match "qwen3.5:2b-q4_K_M")) {
        Write-Host "      [OK] Ollama is active with 'qwen3.5:2b-q4_K_M'." -ForegroundColor Green
    } else {
        Write-Warning "Ollama is active, but model 'qwen3.5:2b-q4_K_M' was not found. AI preparedness will return 503."
    }
} catch {
    Write-Warning "Local Ollama is not responding at http://127.0.0.1:11434. AI preparedness endpoints will return 503."
}

# -----------------------------------------------------------------------------
# 10. Google Maps Key Verification
# -----------------------------------------------------------------------------
Write-Host "[4/6] Checking Google Maps browser configuration..." -ForegroundColor Yellow

$frontendEnvLocal = Join-Path $FrontendDir ".env.local"
$mapsKeyFound = $false
if (Test-Path $frontendEnvLocal) {
    $lines = Get-Content $frontendEnvLocal -ErrorAction SilentlyContinue
    foreach ($line in $lines) {
        if ($line -match "^\s*VITE_GOOGLE_MAPS_API_KEY\s*=\s*(.+)$") {
            $val = $matches[1].Trim().Trim('"').Trim("'")
            if ($val -ne "" -and $val -ne "your_api_key_here") {
                $mapsKeyFound = $true
                break
            }
        }
    }
}

if ($mapsKeyFound) {
    Write-Host "      [OK] Google Maps browser key detected." -ForegroundColor Green
} else {
    Write-Warning "VITE_GOOGLE_MAPS_API_KEY is not set in frontend/.env.local. Maps will render fallback UI."
}

# -----------------------------------------------------------------------------
# 11. Launch Backend Service
# -----------------------------------------------------------------------------
Write-Host "[5/6] Launching backend API service (Uvicorn on 127.0.0.1:8000)..." -ForegroundColor Yellow

$backendLog = Join-Path $LogsDir "backend.log"
$backendErrLog = Join-Path $LogsDir "backend.err.log"

$procBackend = Start-Process -FilePath $VenvPython `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory $BackendDir `
    -RedirectStandardOutput $backendLog `
    -RedirectStandardError $backendErrLog `
    -PassThru

$BackendPid = $procBackend.Id
Write-Host "      [OK] Backend process started (PID: $BackendPid)." -ForegroundColor Green

# -----------------------------------------------------------------------------
# 12. Launch Frontend Service
# -----------------------------------------------------------------------------
Write-Host "[6/6] Launching frontend application (Vite on 127.0.0.1:5173)..." -ForegroundColor Yellow

$frontendLog = Join-Path $LogsDir "frontend.log"
$frontendErrLog = Join-Path $LogsDir "frontend.err.log"

$procFrontend = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", "npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173" `
    -WorkingDirectory $FrontendDir `
    -RedirectStandardOutput $frontendLog `
    -RedirectStandardError $frontendErrLog `
    -PassThru

$FrontendPid = $procFrontend.Id
Write-Host "      [OK] Frontend process started (PID: $FrontendPid)." -ForegroundColor Green

# -----------------------------------------------------------------------------
# 13. Health Check Wait Loop & Rollback on Failure
# -----------------------------------------------------------------------------
Write-Host ""
Write-Host "[INFO] Waiting for services to become healthy..." -ForegroundColor Cyan

$backendHealthy = $false
$frontendHealthy = $false
$proxyHealthy = $false

$healthTimeout = [DateTime]::UtcNow.AddSeconds(30)
while ([DateTime]::UtcNow -lt $healthTimeout) {
    # Check Backend Health
    if (-not $backendHealthy) {
        try {
            $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health" -TimeoutSec 1 -ErrorAction SilentlyContinue
            if ($resp.status -eq "ok") {
                $backendHealthy = $true
            }
        } catch {}
    }

    # Check Frontend Health
    if (-not $frontendHealthy) {
        try {
            $fResp = Invoke-WebRequest -Uri "http://127.0.0.1:5173/" -TimeoutSec 1 -UseBasicParsing -ErrorAction SilentlyContinue
            if ($fResp.StatusCode -eq 200) {
                $frontendHealthy = $true
            }
        } catch {}
    }

    # Check Vite Proxy Health
    if ($backendHealthy -and $frontendHealthy -and -not $proxyHealthy) {
        try {
            $pResp = Invoke-RestMethod -Uri "http://127.0.0.1:5173/api/v1/health" -TimeoutSec 1 -ErrorAction SilentlyContinue
            if ($pResp.status -eq "ok") {
                $proxyHealthy = $true
            }
        } catch {}
    }

    if ($backendHealthy -and $frontendHealthy -and $proxyHealthy) {
        break
    }
    Start-Sleep -Milliseconds 800
}

# Rollback if health checks failed
if (-not ($backendHealthy -and $frontendHealthy -and $proxyHealthy)) {
    Write-Error "Service health check failed within 30 seconds."
    Write-Host "  Backend Healthy:  $backendHealthy" -ForegroundColor $(if ($backendHealthy) { "Green" } else { "Red" })
    Write-Host "  Frontend Healthy: $frontendHealthy" -ForegroundColor $(if ($frontendHealthy) { "Green" } else { "Red" })
    Write-Host "  Proxy Healthy:    $proxyHealthy" -ForegroundColor $(if ($proxyHealthy) { "Green" } else { "Red" })
    Write-Host "[ROLLBACK] Stopping processes started by this invocation..." -ForegroundColor Red

    Stop-VerifiedProcessTree -targetPid $BackendPid
    Stop-VerifiedProcessTree -targetPid $FrontendPid

    Write-Host "Check error logs for details:" -ForegroundColor Gray
    Write-Host "  Backend Log:  $backendLog" -ForegroundColor Gray
    Write-Host "  Frontend Log: $frontendLog" -ForegroundColor Gray
    exit 1
}

# -----------------------------------------------------------------------------
# 14. Save Hardened Runtime Ownership State
# -----------------------------------------------------------------------------
$stateData = @{
    backend_pid          = $BackendPid
    backend_start_time   = (Get-Date -Date $procBackend.StartTime -Format "o")
    backend_command      = "uvicorn app.main:app --host 127.0.0.1 --port 8000"
    backend_working_dir  = $BackendDir
    backend_port         = 8000
    frontend_pid         = $FrontendPid
    frontend_start_time  = (Get-Date -Date $procFrontend.StartTime -Format "o")
    frontend_command     = "npm run dev -- --host 127.0.0.1 --port 5173"
    frontend_working_dir = $FrontendDir
    frontend_port        = 5173
    repo_root            = $RepoRoot
    started_at           = (Get-Date -Format "o")
    backend_log          = $backendLog
    frontend_log         = $frontendLog
}

$stateData | ConvertTo-Json -Depth 3 | Set-Content -Path $StateFile -Encoding UTF8

# -----------------------------------------------------------------------------
# 15. Launch Browser & Banner
# -----------------------------------------------------------------------------
Write-Host ""
Write-Host "=================================================================" -ForegroundColor Green
Write-Host "              AFET360 IS RUNNING AND READY!                      " -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend UI:   http://127.0.0.1:5173" -ForegroundColor Yellow
Write-Host "  Backend API:   http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  API Docs:      http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "  Logs:          $LogsDir" -ForegroundColor Gray
Write-Host ""
Write-Host "To stop the presentation demo cleanly, run:" -ForegroundColor White
Write-Host "  .\scripts\demo\stop.ps1" -ForegroundColor Yellow
Write-Host ""

if (-not $NoBrowser) {
    try {
        Start-Process "http://127.0.0.1:5173"
    } catch {
        Write-Warning "Could not automatically launch default web browser. Please open http://127.0.0.1:5173 manually."
    }
}
