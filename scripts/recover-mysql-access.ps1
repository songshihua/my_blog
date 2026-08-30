[CmdletBinding()]
param(
    [switch]$ConfirmDataPreservingReset
)

$ErrorActionPreference = 'Stop'
if (-not $ConfirmDataPreservingReset) {
    throw 'Pass -ConfirmDataPreservingReset after explicitly approving local credential recovery.'
}

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $projectRoot

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

function Read-EnvironmentMap {
    param([Parameter(Mandatory)][string]$Text)

    $map = [ordered]@{}
    foreach ($line in [Regex]::Split($Text, '\r?\n')) {
        if ($line -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            $map[$Matches[1]] = $Matches[2]
        }
    }
    return $map
}

function Set-EnvironmentLine {
    param(
        [Parameter(Mandatory)][string]$Text,
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Value
    )

    $lines = [System.Collections.Generic.List[string]]::new()
    $replaced = $false
    foreach ($line in [Regex]::Split($Text, '\r?\n')) {
        if ($line.StartsWith("$Name=")) {
            $lines.Add("$Name=$Value")
            $replaced = $true
        }
        else {
            $lines.Add($line)
        }
    }
    if (-not $replaced) {
        $lines.Add("$Name=$Value")
    }
    return [string]::Join([Environment]::NewLine, $lines)
}

$environmentPath = Join-Path $projectRoot '.env'
if (-not (Test-Path -LiteralPath $environmentPath)) {
    throw 'Missing .env.'
}
$environmentText = [System.IO.File]::ReadAllText(
    $environmentPath,
    [System.Text.Encoding]::UTF8
)
$environmentMap = Read-EnvironmentMap -Text $environmentText
$databaseUser = [string]$environmentMap['MYSQL_USER']
if ($databaseUser -notmatch '^[A-Za-z0-9_]+$') {
    throw 'MYSQL_USER contains unsupported characters.'
}

$containerId = [string](& docker compose -f compose.yaml -f compose.dev.yaml ps -q --all db)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($containerId)) {
    throw 'The existing MySQL container could not be resolved.'
}
$containerInspectionJson = & docker inspect $containerId
if ($LASTEXITCODE -ne 0) {
    throw 'The MySQL container could not be inspected.'
}
$containerInspection = $containerInspectionJson | ConvertFrom-Json
$dataMount = $containerInspection[0].Mounts |
    Where-Object { $_.Destination -eq '/var/lib/mysql' -and $_.Type -eq 'volume' } |
    Select-Object -First 1
$volumeName = [string]$dataMount.Name
if ($volumeName -notmatch '^[A-Za-z0-9_.-]+$') {
    throw 'The MySQL data volume could not be resolved safely.'
}

$recoveryContainer = 'song-blog-db-recovery'
$existingRecovery = [string](& docker ps -a -q --filter "name=^/${recoveryContainer}$")
if (-not [string]::IsNullOrWhiteSpace($existingRecovery)) {
    throw "Temporary container $recoveryContainer already exists; inspect it before retrying."
}

$newDjangoSecret = New-UrlSafeSecret -ByteCount 64
$newDatabasePassword = New-UrlSafeSecret -ByteCount 32
$newRootPassword = New-UrlSafeSecret -ByteCount 32
$pendingEnvironment = Set-EnvironmentLine -Text $environmentText -Name 'DJANGO_SECRET_KEY' -Value $newDjangoSecret
$pendingEnvironment = Set-EnvironmentLine -Text $pendingEnvironment -Name 'MYSQL_PASSWORD' -Value $newDatabasePassword
$pendingEnvironment = Set-EnvironmentLine -Text $pendingEnvironment -Name 'MYSQL_ROOT_PASSWORD' -Value $newRootPassword
$pendingPath = Join-Path $projectRoot '.env.recovery.pending'
[System.IO.File]::WriteAllText(
    $pendingPath,
    $pendingEnvironment,
    [System.Text.UTF8Encoding]::new($false)
)

$normalDatabaseStopped = $false
$recoveryStarted = $false
$credentialsReset = $false
$environmentPromoted = $false
try {
    & docker compose -f compose.yaml -f compose.dev.yaml stop db
    if ($LASTEXITCODE -ne 0) {
        throw 'Unable to stop the normal MySQL container.'
    }
    $normalDatabaseStopped = $true

    & docker run -d --rm --name $recoveryContainer --network none `
        -v "${volumeName}:/var/lib/mysql" mysql:8.4 `
        --skip-grant-tables --skip-networking
    if ($LASTEXITCODE -ne 0) {
        throw 'Unable to start the isolated MySQL recovery container.'
    }
    $recoveryStarted = $true

    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        & docker exec $recoveryContainer mysqladmin ping --silent 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $ready = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) {
        throw 'The isolated MySQL recovery server did not become ready.'
    }

    $sql = "FLUSH PRIVILEGES; ALTER USER '$databaseUser'@'%' IDENTIFIED BY '$newDatabasePassword'; ALTER USER 'root'@'localhost' IDENTIFIED BY '$newRootPassword';"
    $sql | & docker exec -i $recoveryContainer mysql -uroot
    if ($LASTEXITCODE -ne 0) {
        throw 'MySQL rejected the data-preserving account reset.'
    }
    $credentialsReset = $true

    & docker stop $recoveryContainer | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Unable to stop the isolated recovery container.'
    }
    $recoveryStarted = $false

    Move-Item -LiteralPath $pendingPath -Destination $environmentPath -Force
    $environmentPromoted = $true

    & docker compose -f compose.yaml -f compose.dev.yaml up -d --force-recreate --wait db
    if ($LASTEXITCODE -ne 0) {
        throw 'Credentials were reset, but the normal MySQL container failed to restart.'
    }
    $normalDatabaseStopped = $false
}
catch {
    $recoveryError = $_
    if ($recoveryStarted) {
        & docker stop $recoveryContainer | Out-Null
        $recoveryStarted = $false
    }
    # Once ALTER USER succeeds, promote the matching pending environment before
    # attempting restart. This prevents a half-rotated, inaccessible data volume.
    if ($credentialsReset -and -not $environmentPromoted -and (Test-Path -LiteralPath $pendingPath)) {
        try {
            Move-Item -LiteralPath $pendingPath -Destination $environmentPath -Force
            $environmentPromoted = $true
        }
        catch {
            # Keep the pending file for manual recovery; it is ignored by Git.
        }
    }
    if ($normalDatabaseStopped) {
        if (-not $credentialsReset -or $environmentPromoted) {
            & docker compose -f compose.yaml -f compose.dev.yaml up -d --force-recreate --wait db
        }
        else {
            # The old container can still be restarted for inspection even when
            # its health check cannot authenticate with the newly reset account.
            & docker compose -f compose.yaml -f compose.dev.yaml start db
        }
    }
    throw $recoveryError
}
finally {
    if ($recoveryStarted) {
        & docker stop $recoveryContainer | Out-Null
    }
    if (-not $credentialsReset -and (Test-Path -LiteralPath $pendingPath)) {
        Remove-Item -LiteralPath $pendingPath -Force
    }
}

Write-Host 'MySQL access recovered, secrets rotated, and the existing data volume preserved.' -ForegroundColor Green
