[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $projectRoot

if (-not (Test-Path -LiteralPath '.env')) {
    $environmentText = [System.IO.File]::ReadAllText(
        (Join-Path $projectRoot '.env.example'),
        [System.Text.Encoding]::UTF8
    )
    $secretKey = & python -c "import secrets; print(secrets.token_urlsafe(64))"
    if ($LASTEXITCODE -ne 0) { throw 'Unable to generate DJANGO_SECRET_KEY.' }
    $databasePassword = & python -c "import secrets; print(secrets.token_urlsafe(32))"
    if ($LASTEXITCODE -ne 0) { throw 'Unable to generate MYSQL_PASSWORD.' }
    $rootPassword = & python -c "import secrets; print(secrets.token_urlsafe(32))"
    if ($LASTEXITCODE -ne 0) { throw 'Unable to generate MYSQL_ROOT_PASSWORD.' }
    $environmentText = $environmentText.Replace('replace-with-a-random-value', $secretKey)
    $environmentText = $environmentText.Replace('replace-with-a-long-random-password', $databasePassword)
    $environmentText = $environmentText.Replace('replace-with-a-different-long-random-password', $rootPassword)
    Set-Content -LiteralPath '.env' -Value $environmentText -Encoding utf8NoBOM
    Write-Host 'Created .env with local random secrets.' -ForegroundColor Green
}

if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    & python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Unable to create the Python virtual environment.' }
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'Unable to upgrade pip.' }
& .\.venv\Scripts\python.exe -m pip install -r backend\requirements\development.txt
if ($LASTEXITCODE -ne 0) { throw 'Unable to install backend dependencies.' }

Push-Location -LiteralPath 'frontend'
try {
    & npm ci
    if ($LASTEXITCODE -ne 0) { throw 'Unable to install frontend dependencies.' }
}
finally {
    Pop-Location
}

& docker compose -f compose.yaml -f compose.dev.yaml config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose configuration is invalid.' }
& docker compose -f compose.yaml -f compose.dev.yaml up -d --wait db
if ($LASTEXITCODE -ne 0) { throw 'Unable to start the local MySQL container.' }
& docker compose -f compose.yaml -f compose.dev.yaml exec -T db sh /docker-entrypoint-initdb.d/20-test-database.sh
if ($LASTEXITCODE -ne 0) { throw 'Unable to prepare the isolated test database.' }

& .\.venv\Scripts\python.exe backend\manage.py migrate
if ($LASTEXITCODE -ne 0) { throw 'Django migrations failed.' }
& .\.venv\Scripts\python.exe backend\manage.py seed_demo
if ($LASTEXITCODE -ne 0) { throw 'Unable to seed local sample data.' }

Write-Host ''
Write-Host 'Local setup is ready.' -ForegroundColor Green
Write-Host 'Backend: .\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000'
Write-Host 'Frontend: Set-Location frontend; npm run dev'
Write-Host 'Admin:    .\.venv\Scripts\python.exe backend\manage.py createsuperuser'
