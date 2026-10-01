<#
.SYNOPSIS
    Builds and starts the Pulse login stack (PostgreSQL + FastAPI backend + nginx/frontend)
    locally with Docker, then opens the sign-in page in your browser.

.DESCRIPTION
    - Verifies Docker Desktop is running (starts it and waits if it's not).
    - Creates .env from .env.example on first run, with a random JWT secret.
    - Runs `docker compose up --build -d`.
    - Waits for the backend health check and the frontend to respond.
    - Opens http://localhost:8080 in the default browser.

.PARAMETER Rebuild
    Force a full rebuild without Docker's layer cache.

.PARAMETER Down
    Stop and remove the containers (add -Volumes to also wipe the database).

.PARAMETER Volumes
    Used with -Down: also removes the named database volume (full reset).

.EXAMPLE
    ./start.ps1
    ./start.ps1 -Rebuild
    ./start.ps1 -Down
    ./start.ps1 -Down -Volumes
#>
[CmdletBinding()]
param(
    [switch]$Rebuild,
    [switch]$Down,
    [switch]$Volumes
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "    $msg" -ForegroundColor Red }

# ---------------------------------------------------------------- teardown

if ($Down) {
    Write-Step "Stopping the Pulse stack"
    if ($Volumes) {
        docker compose down --volumes
        Write-Ok "Containers and database volume removed."
    } else {
        docker compose down
        Write-Ok "Containers stopped (database volume kept)."
    }
    exit 0
}

# ---------------------------------------------------------------- docker

function Test-DockerRunning {
    docker info *> $null
    return $LASTEXITCODE -eq 0
}

Write-Step "Checking Docker Desktop"
if (-not (Test-DockerRunning)) {
    Write-Warn "Docker daemon is not responding — trying to start Docker Desktop..."
    $dockerExe = @(
        "$Env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "$Env:LOCALAPPDATA\Docker\Docker Desktop.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1

    if (-not $dockerExe) {
        Write-Err "Could not find Docker Desktop. Install it from https://www.docker.com/products/docker-desktop/ and run this script again."
        exit 1
    }
    Start-Process $dockerExe

    $deadline = (Get-Date).AddMinutes(3)
    while (-not (Test-DockerRunning)) {
        if ((Get-Date) -gt $deadline) {
            Write-Err "Docker Desktop did not become ready within 3 minutes. Start it manually and re-run this script."
            exit 1
        }
        Start-Sleep -Seconds 3
    }
}
Write-Ok "Docker is running."

# ---------------------------------------------------------------- .env

if (-not (Test-Path ".env")) {
    Write-Step "Creating .env from .env.example"
    Copy-Item ".env.example" ".env"
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $secret = [Convert]::ToBase64String($bytes) -replace '[+/=]', ''
    (Get-Content ".env") -replace '^JWT_SECRET=.*', "JWT_SECRET=$secret" | Set-Content ".env"
    Write-Ok ".env created with a random JWT_SECRET."
} else {
    Write-Ok ".env already exists, keeping it."
}

# ---------------------------------------------------------------- build & run

Write-Step "Building and starting containers (db, backend, frontend)"
if ($Rebuild) {
    docker compose build --no-cache
    if ($LASTEXITCODE -ne 0) { Write-Err "Build failed."; exit 1 }
    docker compose up -d
} else {
    docker compose up -d --build
}
if ($LASTEXITCODE -ne 0) {
    Write-Err "docker compose failed to start the stack. See the output above."
    exit 1
}
Write-Ok "Containers started."

# ---------------------------------------------------------------- wait for health

function Wait-Http($url, $label, $timeoutSec = 90) {
    Write-Step "Waiting for $label ($url)"
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3
            if ($resp.StatusCode -eq 200) { Write-Ok "$label is up."; return $true }
        } catch { }
        Start-Sleep -Seconds 2
    }
    Write-Err "$label did not respond within $timeoutSec seconds."
    Write-Warn "Check logs with: docker compose logs -f"
    return $false
}

$envVars = Get-Content ".env" | Where-Object { $_ -match '^\s*([A-Z_]+)=(.*)$' } | ForEach-Object {
    $null = $_ -match '^\s*([A-Z_]+)=(.*)$'; @{ $matches[1] = $matches[2] }
}
$backendPort  = ($envVars | Where-Object { $_.ContainsKey("BACKEND_PORT") }  | Select-Object -Last 1)."BACKEND_PORT"
$frontendPort = ($envVars | Where-Object { $_.ContainsKey("FRONTEND_PORT") } | Select-Object -Last 1)."FRONTEND_PORT"
if (-not $backendPort)  { $backendPort  = 8000 }
if (-not $frontendPort) { $frontendPort = 8080 }

$backendOk  = Wait-Http "http://localhost:$backendPort/api/health" "backend API"
$frontendOk = Wait-Http "http://localhost:$frontendPort/" "frontend (nginx)"

if (-not ($backendOk -and $frontendOk)) {
    Write-Warn "The stack came up but did not pass its health checks in time. It may still finish shortly — check 'docker compose ps'."
    exit 1
}

# ---------------------------------------------------------------- open browser

$url = "http://localhost:$frontendPort/"
Write-Step "Opening $url"
Start-Process $url

Write-Host ""
Write-Ok "Pulse is running."
Write-Host "    Sign-in page : http://localhost:$frontendPort/"
Write-Host "    Backend API  : http://localhost:$backendPort/api/docs"
Write-Host ""
Write-Host "    Demo accounts (password: Pulse#2026):" -ForegroundColor DarkGray
Write-Host "      student  240103083"
Write-Host "      faculty  faculty@sdu.edu.kz"
Write-Host "      manager  manager@sdu.edu.kz"
Write-Host "      admin    admin@sdu.edu.kz"
Write-Host ""
Write-Host "    Stop the stack any time with: ./start.ps1 -Down" -ForegroundColor DarkGray
