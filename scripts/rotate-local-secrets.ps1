[CmdletBinding()]
param(
    [switch]$RecoverFromContainer
)

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

    $prefix = "$Name="
    $line = [Regex]::Split($Text, '\r?\n') |
        Where-Object { $_.StartsWith($prefix) } |
        Select-Object -First 1
    if ($null -eq $line) {
        throw "Missing $Name in .env."
    }

    return $line.Substring($prefix.Length).Trim()
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

$environmentText = [System.IO.File]::ReadAllText(
    (Join-Path $projectRoot '.env'),
    [System.Text.Encoding]::UTF8
)
$databaseUser = Get-EnvironmentValue -Text $environmentText -Name 'MYSQL_USER'

# A running container is mandatory. Rotating only .env would make its password
# diverge from the existing MySQL data volume and lock the application out.
$containerId = [string](& docker compose -f compose.yaml -f compose.dev.yaml ps -q db)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($containerId)) {
    throw 'The MySQL container must be running before rotation. Start it or use recover-mysql-access.ps1.'
}

$containerEnvironmentJson = & docker inspect --format '{{json .Config.Env}}' $containerId
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to inspect the running MySQL container.'
}
$containerValues = @{}
foreach ($entry in ($containerEnvironmentJson | ConvertFrom-Json)) {
    $parts = [string]$entry -split '=', 2
    if ($parts.Count -eq 2) {
        $containerValues[$parts[0]] = $parts[1]
    }
}
if (-not $containerValues.ContainsKey('MYSQL_ROOT_PASSWORD') -or
    -not $containerValues.ContainsKey('MYSQL_USER')) {
    throw 'The running container does not contain the expected MySQL account settings.'
}
if ($RecoverFromContainer) {
    $databaseUser = [string]$containerValues['MYSQL_USER']
}
elseif ($databaseUser -ne [string]$containerValues['MYSQL_USER']) {
    throw 'MYSQL_USER differs from the running container. Retry with -RecoverFromContainer after inspection.'
}
if ($databaseUser -notmatch '^[A-Za-z0-9_]+$') {
    throw 'MYSQL_USER contains unsupported characters.'
}

$newDjangoSecret = New-UrlSafeSecret -ByteCount 64
$newDatabasePassword = New-UrlSafeSecret -ByteCount 32
$newRootPassword = New-UrlSafeSecret -ByteCount 32
$sql = "ALTER USER '$databaseUser'@'%' IDENTIFIED BY '$newDatabasePassword'; ALTER USER 'root'@'localhost' IDENTIFIED BY '$newRootPassword';"

# The old password comes from the container environment and the new passwords
# travel through standard input. No credential is placed in a process argument.
$sql | & docker compose -f compose.yaml -f compose.dev.yaml exec -T db `
    sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot'
if ($LASTEXITCODE -ne 0) {
    throw 'MySQL rejected the credential rotation; .env was not changed.'
}

$environmentText = Set-EnvironmentValue -Text $environmentText -Name 'DJANGO_SECRET_KEY' -Value $newDjangoSecret
$environmentText = Set-EnvironmentValue -Text $environmentText -Name 'MYSQL_PASSWORD' -Value $newDatabasePassword
$environmentText = Set-EnvironmentValue -Text $environmentText -Name 'MYSQL_ROOT_PASSWORD' -Value $newRootPassword

$temporaryPath = Join-Path $projectRoot '.env.rotate.tmp'
[System.IO.File]::WriteAllText(
    $temporaryPath,
    $environmentText,
    [System.Text.UTF8Encoding]::new($false)
)
Move-Item -LiteralPath $temporaryPath -Destination (Join-Path $projectRoot '.env') -Force

& docker compose -f compose.yaml -f compose.dev.yaml up -d --force-recreate --wait db
if ($LASTEXITCODE -ne 0) {
    throw 'Credentials were rotated and .env matches MySQL, but the container failed to restart.'
}

Write-Host 'Local Django and MySQL secrets were rotated successfully.' -ForegroundColor Green
Write-Host 'Restart any running Django process so it reloads .env.'
