$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$backendDir = Join-Path $root "friday-backend"
$frontendDir = Join-Path $root "friday-frontend"

if (-not (Test-Path $backendDir)) {
    throw "Backend directory not found: $backendDir"
}

if (-not (Test-Path $frontendDir)) {
    throw "Frontend directory not found: $frontendDir"
}

try {
    $modelsResponse = Invoke-RestMethod -Uri "http://localhost:1234/v1/models" -Method Get -TimeoutSec 3
    $loadedCount = @($modelsResponse.data).Count
    if ($loadedCount -eq 0) {
        Write-Warning "LM Studio is running but no models are loaded. Load one in LM Studio or run: lms load <model>."
    }
} catch {
    Write-Warning "Could not query LM Studio at http://localhost:1234. Start LM Studio local server before chatting."
}

$backendCommand = @'
Set-Location "__BACKEND_DIR__"
if (Test-Path ".\venv\Scripts\Activate.ps1") {
    & ".\venv\Scripts\Activate.ps1"
} elseif (Test-Path ".\.venv\Scripts\Activate.ps1") {
    & ".\.venv\Scripts\Activate.ps1"
} else {
    Write-Warning "No virtual environment found (.\\venv or .\\.venv). Running with system Python."
}
uvicorn main:app --reload --port 8000
'@.Replace("__BACKEND_DIR__", $backendDir)

$frontendCommand = @'
Set-Location "__FRONTEND_DIR__"
npm run dev
'@.Replace("__FRONTEND_DIR__", $frontendDir)

Start-Process -FilePath "pwsh" -WorkingDirectory $backendDir -ArgumentList @(
    "-NoExit",
    "-Command",
    $backendCommand
)

Start-Process -FilePath "pwsh" -WorkingDirectory $frontendDir -ArgumentList @(
    "-NoExit",
    "-Command",
    $frontendCommand
)

Write-Host "Started backend and frontend terminals." -ForegroundColor Green
