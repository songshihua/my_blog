[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $projectRoot

if (-not (Test-Path -LiteralPath '.env')) {
    throw 'Missing .env. Run scripts/setup.ps1 first.'
}

function New-UrlSafeSecret {
    param([Parameter(Mandatory)][int]$ByteCount)

    $bytes = New-Object byte[] $ByteCount
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($bytes)
    }
    finally {
        $generator.Dispose()
    }

    return [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

function Get-EnvironmentValue {
    param(
        [Parameter(Mandatory)][string]$Text,
        [Parameter(Mandatory)][string]$Name
    )

    $pattern = '(?m)^' + [Regex]::Escape($Name) + '=(.*)$'
    $match = [Regex]::Match($Text, $pattern)
    if (-not $match.Success) {
        throw "Missing $Name in .env."
    }

    return $match.Groups[1].Value.Trim()
}

function Set-EnvironmentValue {
    param(
        [Parameter(Mandatory)][string]$Text,
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Value
    )

    $pattern = '(?m)^' + [Regex]::Escape($Name) + '=.*$'
    return [Regex]::Replace($Text, $pattern, "$Name=$Value")
}

$environmentText = Get-Content -LiteralPath '.env' -Raw
$databaseUser = Get-EnvironmentValue -Text $environmentText -Name 'MYSQL_USER'
$currentRootPassword = Get-EnvironmentValue -Text $environmentText -Name 'MYSQL_ROOT_PASSWORD'

if ($databaseUser -notmatch '^[A-Za-z0-9_]+$') {
    throw 'MYSQL_USER contains unsupported characters.'
}

$newDjangoSecret = New-UrlSafeSecret -ByteCount 64
$newDatabasePassword = New-UrlSafeSecret -ByteCount 32
$newRootPassword = New-UrlSafeSecret -ByteCount 32

$containerId = [string](& docker compose -f compose.yaml -f compose.dev.yaml ps -q db)
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to inspect the MySQL container.'
}

if (-not [string]::IsNullOrWhiteSpace($containerId)) {
    # Secrets are URL-safe random strings, so quoting them as SQL string literals is safe.
    $sql = "ALTER USER '$databaseUser'@'%' IDENTIFIED BY '$newDatabasePassword'; ALTER USER 'root'@'localhost' IDENTIFIED BY '$newRootPassword';"
    $mysqlArguments = @(
        'compose', '-f', 'compose.yaml', '-f', 'compose.dev.yaml',
        'exec', '-T', '-e', "MYSQL_PWD=$currentRootPassword",
        'db', 'mysql', '-uroot', '-e', $sql
    )
    & docker @mysqlArguments
    if ($LASTEXITCODE -ne 0) {
        throw 'MySQL rejected the credential rotation; .env was not changed.'
    }
}

$environmentText = Set-EnvironmentValue -Text $environmentText -Name 'DJANGO_SECRET_KEY' -Value $newDjangoSecret
$environmentText = Set-EnvironmentValue -Text $environmentText -Name 'MYSQL_PASSWORD' -Value $newDatabasePassword
$environmentText = Set-EnvironmentValue -Text $environmentText -Name 'MYSQL_ROOT_PASSWORD' -Value $newRootPassword

$temporaryPath = Join-Path $projectRoot '.env.rotate.tmp'
[System.IO.File]::WriteAllText($temporaryPath, $environmentText, [System.Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $temporaryPath -Destination (Join-Path $projectRoot '.env') -Force

if (-not [string]::IsNullOrWhiteSpace($containerId)) {
    & docker compose -f compose.yaml -f compose.dev.yaml up -d --force-recreate --wait db
    if ($LASTEXITCODE -ne 0) {
        throw 'Secrets were rotated, but the MySQL container failed to restart. Inspect docker compose logs db.'
    }
}

Write-Host 'Local Django and MySQL secrets were rotated successfully.' -ForegroundColor Green
Write-Host 'Restart any running Django process so it reloads .env.'
