# scripts/demo/stop.ps1
# AFET360 — Controlled Presentation Demo Stop Script
# Reads runtime ownership state, validates strong process identity fingerprints,
# safely terminates only AFET360 backend and frontend processes, and leaves database data intact.

$ErrorActionPreference = "Stop"

$StateDir = Join-Path $env:LOCALAPPDATA "AFET360\demo"
$StateFile = Join-Path $StateDir "state.json"

if (-not (Test-Path $StateFile)) {
    Write-Host "AFET360 is not running." -ForegroundColor Yellow
    exit 0
}

try {
    $state = Get-Content $StateFile -Raw | ConvertFrom-Json
} catch {
    Write-Warning "Could not parse state file. Removing corrupt state..."
    Remove-Item -Path $StateFile -Force -ErrorAction SilentlyContinue
    Write-Host "AFET360 is not running." -ForegroundColor Yellow
    exit 0
}

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

    # Strict multi-factor fingerprint:
    # 1. Must contain uvicorn and app.main:app
    $hasUvicorn = ($cmd -match "uvicorn") -and ($cmd -match "app\.main:app")

    # 2. Must reference port 8000, backend directory, or virtual environment
    $hasPortOrDir = ($cmd -match "8000") -or ($cmd -match [regex]::Escape($state.backend_working_dir)) -or ($cmd -match "\.venv")

    # 3. Creation timestamp verification (tolerance 15 seconds)
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

    # Strict multi-factor fingerprint:
    # 1. Must match project-local npm run dev or vite launch
    $hasDevOrVite = ($cmd -match "npm" -and $cmd -match "dev") -or ($cmd -match "vite") -or ($cmd -match "5173")

    # 2. Must match frontend directory, repo root, or port 5173
    $hasDir = ($cmd -match [regex]::Escape($state.frontend_working_dir)) -or ($cmd -match "frontend") -or ($cmd -match "5173")

    # 3. Creation timestamp verification (tolerance 15 seconds)
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
    # Recursively find and terminate child processes of verified parent
    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $targetPid" -ErrorAction SilentlyContinue
    if ($children) {
        foreach ($child in $children) {
            Stop-VerifiedProcessTree -targetPid $child.ProcessId
        }
    }

    try {
        $proc = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
        Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "  Stopped PID $targetPid ($($proc.ProcessName))." -ForegroundColor Gray
        } else {
            Write-Host "  Stopped PID $targetPid." -ForegroundColor Gray
        }
    } catch {
        Write-Warning "Could not stop PID $targetPid : $_"
    }
}

Write-Host "Stopping AFET360 demo processes..." -ForegroundColor Cyan

# Stop Backend API
if ($state.backend_pid) {
    Write-Host "[1/2] Verifying Backend API (PID: $($state.backend_pid))..." -ForegroundColor Yellow
    if (Test-BackendIdentity -targetPid $state.backend_pid -state $state) {
        Stop-VerifiedProcessTree -targetPid $state.backend_pid
    } else {
        Write-Warning "PID $($state.backend_pid) does NOT match the verified AFET360 backend signature. Refusing to terminate to protect unrelated processes."
    }
}

# Stop Frontend UI
if ($state.frontend_pid) {
    Write-Host "[2/2] Verifying Frontend UI (PID: $($state.frontend_pid))..." -ForegroundColor Yellow
    if (Test-FrontendIdentity -targetPid $state.frontend_pid -state $state) {
        Stop-VerifiedProcessTree -targetPid $state.frontend_pid
    } else {
        Write-Warning "PID $($state.frontend_pid) does NOT match the verified AFET360 frontend signature. Refusing to terminate to protect unrelated processes."
    }
}

# Clean up runtime state file
Remove-Item -Path $StateFile -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "AFET360 stopped successfully." -ForegroundColor Green
Write-Host "Note: PostgreSQL database and data volumes remain intact in Docker." -ForegroundColor Gray
Write-Host ""
