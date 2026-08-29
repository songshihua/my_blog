[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $projectRoot

if (-not (Test-Path -LiteralPath '.env')) {
    $environmentText = Get-Content -LiteralPath '.env.example' -Raw
    $secretKey = & python -c "import secrets; print(secrets.token_urlsafe(64))"
    $databasePassword = & python -c "import secrets; print(secrets.token_urlsafe(32))"
    $rootPassword = & python -c "import secrets; print(secrets.token_urlsafe(32))"
    $environmentText = $environmentText.Replace('replace-with-a-random-value', $secretKey)
    $environmentText = $environmentText.Replace('replace-with-a-long-random-password', $databasePassword)
    $environmentText = $environmentText.Replace('replace-with-a-different-long-random-password', $rootPassword)
    Set-Content -LiteralPath '.env' -Value $environmentText -Encoding utf8NoBOM
    Write-Host 'Created .env with local random secrets.' -ForegroundColor Green
}

if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    & python -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r backend\requirements\development.txt

Push-Location -LiteralPath 'frontend'
try {
    & npm ci
}
finally {
    Pop-Location
}

& docker compose -f compose.yaml -f compose.dev.yaml config --quiet
& docker compose -f compose.yaml -f compose.dev.yaml up -d --wait db
& docker compose -f compose.yaml -f compose.dev.yaml exec -T db sh /docker-entrypoint-initdb.d/20-test-database.sh

& .\.venv\Scripts\python.exe backend\manage.py migrate
& .\.venv\Scripts\python.exe backend\manage.py seed_demo

Write-Host ''
Write-Host 'Local setup is ready.' -ForegroundColor Green
Write-Host 'Backend: .\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000'
Write-Host 'Frontend: Set-Location frontend; npm run dev'
Write-Host 'Admin:    .\.venv\Scripts\python.exe backend\manage.py createsuperuser'
