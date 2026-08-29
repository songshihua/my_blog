[CmdletBinding()]
param(
    [switch]$SkipTests
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $projectRoot

& .\.venv\Scripts\python.exe backend\manage.py check
& .\.venv\Scripts\python.exe backend\manage.py makemigrations --check --dry-run
& .\.venv\Scripts\python.exe -m ruff check backend

if (-not $SkipTests) {
    & .\.venv\Scripts\python.exe -m pytest backend\tests --cov=backend\apps
}

Push-Location -LiteralPath 'frontend'
try {
    & npm run lint
    & npm run typecheck
    & npm run build
}
finally {
    Pop-Location
}

& docker compose -f compose.yaml -f compose.dev.yaml config --quiet
Write-Host 'All requested checks completed.' -ForegroundColor Green
