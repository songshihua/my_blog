[CmdletBinding()]
param(
    [string]$SqlFile = '',
    [string]$AdminUser = 'root',
    [string]$MySqlExe = 'D:\360Downloads\mysql\MYSQL\bin\mysql.exe'
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$environmentFile = Join-Path $projectRoot '.env'
if (-not $SqlFile) {
    $SqlFile = Join-Path $projectRoot 'backups\song_blog.sql'
}
$resolvedSqlFile = (Resolve-Path -LiteralPath $SqlFile).Path

if (-not (Test-Path -LiteralPath $environmentFile)) {
    throw "Missing $environmentFile. Copy .env.example to .env and configure it first."
}
if (-not (Test-Path -LiteralPath $MySqlExe)) {
    $discoveredMySql = Get-Command mysql.exe -ErrorAction SilentlyContinue
    if (-not $discoveredMySql) {
        throw 'mysql.exe was not found. Pass its path with -MySqlExe.'
    }
    $MySqlExe = $discoveredMySql.Source
}

$settings = @{}
foreach ($line in [System.IO.File]::ReadAllLines($environmentFile)) {
    if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
    $name, $value = $line -split '=', 2
    $settings[$name.Trim()] = $value.Trim()
}

$requiredNames = @('MYSQL_DATABASE', 'MYSQL_TEST_DATABASE', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_HOST', 'MYSQL_PORT')
foreach ($name in $requiredNames) {
    if (-not $settings[$name]) { throw "Missing $name in $environmentFile." }
}
if ($settings.MYSQL_HOST -notin @('127.0.0.1', 'localhost')) {
    throw 'This script only permits a local MySQL server.'
}
if ($settings.MYSQL_PORT -ne '3306') {
    throw 'Set MYSQL_PORT=3306 before importing into Windows MySQL80.'
}
foreach ($identifierName in @('MYSQL_DATABASE', 'MYSQL_TEST_DATABASE', 'MYSQL_USER')) {
    if ($settings[$identifierName] -notmatch '^[A-Za-z0-9_]+$') {
        throw "$identifierName contains unsupported characters."
    }
}

$service = Get-Service -Name MySQL80 -ErrorAction SilentlyContinue
if (-not $service -or $service.Status -ne 'Running') {
    throw 'Windows service MySQL80 is not running.'
}

Write-Host "Target: $($settings.MYSQL_HOST):$($settings.MYSQL_PORT)/$($settings.MYSQL_DATABASE)" -ForegroundColor Cyan
Write-Host "Dump:   $resolvedSqlFile" -ForegroundColor Cyan
Write-Warning 'Importing the dump replaces tables of the same name in the local song_blog database.'
$confirmation = Read-Host 'Type IMPORT to continue'
if ($confirmation -cne 'IMPORT') {
    Write-Host 'Import cancelled; no database changes were made.'
    exit 0
}

$secureAdminPassword = Read-Host "Password for local MySQL administrator '$AdminUser'" -AsSecureString
$adminPasswordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureAdminPassword)
$adminPassword = $null
$temporaryDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ("song-blog-mysql-" + [guid]::NewGuid().ToString('N'))

try {
    $adminPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($adminPasswordPointer)
    [void](New-Item -ItemType Directory -Path $temporaryDirectory)
    $clientConfig = Join-Path $temporaryDirectory 'client.cnf'
    $bootstrapSql = Join-Path $temporaryDirectory 'bootstrap.sql'

    $escapedAdminPassword = $adminPassword.Replace('\', '\\').Replace('"', '\"')
    [System.IO.File]::WriteAllText(
        $clientConfig,
        "[client]`r`nuser=$AdminUser`r`npassword=`"$escapedAdminPassword`"`r`n",
        [System.Text.UTF8Encoding]::new($false)
    )

    & $MySqlExe "--defaults-extra-file=$clientConfig" --protocol=TCP `
        -h $settings.MYSQL_HOST -P $settings.MYSQL_PORT `
        -e 'SELECT VERSION() AS mysql_version, CURRENT_USER() AS connected_as;'
    if ($LASTEXITCODE -ne 0) { throw 'Unable to authenticate to local MySQL.' }

    # Do not pipe SQL text through Windows PowerShell. Its native-command pipe
    # encoding can corrupt UTF-8 Chinese text and even adjacent quote bytes.
    $importProcess = Start-Process -FilePath $MySqlExe -ArgumentList @(
        "--defaults-extra-file=$clientConfig",
        '--protocol=TCP',
        '-h', $settings.MYSQL_HOST,
        '-P', $settings.MYSQL_PORT
    ) -RedirectStandardInput $resolvedSqlFile -NoNewWindow -Wait -PassThru
    if ($importProcess.ExitCode -ne 0) { throw 'The SQL dump import failed.' }

    $databaseName = $settings.MYSQL_DATABASE
    $testDatabaseName = $settings.MYSQL_TEST_DATABASE
    $applicationUser = $settings.MYSQL_USER
    $applicationPassword = $settings.MYSQL_PASSWORD.Replace('\', '\\').Replace("'", "''")
    $accountHosts = @('localhost', '127.0.0.1')
    $sqlLines = @(
        "CREATE DATABASE IF NOT EXISTS ``$databaseName`` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;",
        "CREATE DATABASE IF NOT EXISTS ``$testDatabaseName`` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
    )
    foreach ($accountHost in $accountHosts) {
        $sqlLines += "CREATE USER IF NOT EXISTS '$applicationUser'@'$accountHost' IDENTIFIED BY '$applicationPassword';"
        $sqlLines += "ALTER USER '$applicationUser'@'$accountHost' IDENTIFIED BY '$applicationPassword';"
        $sqlLines += "GRANT ALL PRIVILEGES ON ``$databaseName``.* TO '$applicationUser'@'$accountHost';"
        $sqlLines += "GRANT ALL PRIVILEGES ON ``$testDatabaseName``.* TO '$applicationUser'@'$accountHost';"
    }
    $sqlLines += 'FLUSH PRIVILEGES;'
    [System.IO.File]::WriteAllLines($bootstrapSql, $sqlLines, [System.Text.UTF8Encoding]::new($false))
    $bootstrapProcess = Start-Process -FilePath $MySqlExe -ArgumentList @(
        "--defaults-extra-file=$clientConfig",
        '--protocol=TCP',
        '-h', $settings.MYSQL_HOST,
        '-P', $settings.MYSQL_PORT
    ) -RedirectStandardInput $bootstrapSql -NoNewWindow -Wait -PassThru
    if ($bootstrapProcess.ExitCode -ne 0) { throw 'Creating the application database account failed.' }

    $env:MYSQL_PWD = $settings.MYSQL_PASSWORD
    try {
        $tableCount = & $MySqlExe --protocol=TCP -h $settings.MYSQL_HOST `
            -P $settings.MYSQL_PORT -u $applicationUser -N `
            -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$databaseName';"
        if ($LASTEXITCODE -ne 0) { throw 'Application-account verification failed.' }
    }
    finally {
        Remove-Item Env:MYSQL_PWD -ErrorAction SilentlyContinue
    }

    Write-Host "Local MySQL is ready. Tables found in ${databaseName}: $tableCount" -ForegroundColor Green
}
finally {
    if ($adminPasswordPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($adminPasswordPointer)
    }
    $adminPassword = $null
    if (Test-Path -LiteralPath $temporaryDirectory) {
        Remove-Item -LiteralPath $temporaryDirectory -Recurse -Force
    }
}
