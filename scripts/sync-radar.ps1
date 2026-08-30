[CmdletBinding()]
param(
    [ValidateSet('all', 'github', 'huggingface', 'deepseek', 'arxiv', 'openreview')]
    [string]$Source = 'all',
    [ValidateRange(1, 100)]
    [int]$Limit = 20,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$managePath = Join-Path $projectRoot 'backend\manage.py'

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Virtual environment is missing. Run scripts/setup.ps1 first.'
}

$commandArguments = @($managePath, 'ingest_sources', '--limit', $Limit)
if ($Source -ne 'all') {
    $commandArguments += @('--source', $Source)
}
if ($DryRun) {
    $commandArguments += '--dry-run'
}

& $pythonPath @commandArguments
exit $LASTEXITCODE
