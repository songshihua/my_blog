[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$environmentPath = Join-Path $projectRoot '.env'
$templatePath = Join-Path $projectRoot '.env.example'

if (-not (Test-Path -LiteralPath $environmentPath)) {
    throw 'Missing .env.'
}

function Read-EnvironmentMap {
    param([Parameter(Mandatory)][string]$Text)

    $map = @{}
    foreach ($line in [Regex]::Split($Text, '\r?\n')) {
        if ($line -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            $map[$Matches[1]] = $Matches[2]
        }
    }
    return $map
}

$encoding = [System.Text.UTF8Encoding]::new($false)
$currentText = [System.IO.File]::ReadAllText($environmentPath, [System.Text.Encoding]::UTF8)
$templateText = [System.IO.File]::ReadAllText($templatePath, [System.Text.Encoding]::UTF8)
$currentValues = Read-EnvironmentMap -Text $currentText

foreach ($requiredSecret in @('DJANGO_SECRET_KEY', 'MYSQL_PASSWORD', 'MYSQL_ROOT_PASSWORD')) {
    if (-not $currentValues.ContainsKey($requiredSecret) -or
        [string]::IsNullOrWhiteSpace([string]$currentValues[$requiredSecret]) -or
        [string]$currentValues[$requiredSecret] -match '^replace-with-') {
        throw "A valid $requiredSecret must exist before normalization."
    }
}

$normalizedLines = [System.Collections.Generic.List[string]]::new()
foreach ($line in [Regex]::Split($templateText, '\r?\n')) {
    if ($line -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
        $name = $Matches[1]
        if ($currentValues.ContainsKey($name)) {
            $normalizedLines.Add("$name=$($currentValues[$name])")
            continue
        }
    }
    $normalizedLines.Add($line)
}

$temporaryPath = Join-Path $projectRoot '.env.normalize.tmp'
[System.IO.File]::WriteAllText(
    $temporaryPath,
    [string]::Join([Environment]::NewLine, $normalizedLines),
    $encoding
)
Move-Item -LiteralPath $temporaryPath -Destination $environmentPath -Force
Write-Host '.env was normalized from .env.example while preserving local secrets.' -ForegroundColor Green
