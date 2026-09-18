param([int]$Limit = 5, [switch]$RetryFailed)
$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectPath '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    throw 'Instale primeiro: .\scripts\install.ps1 -WithOCR (no computador Intel).'
}
$taskArgs = @((Join-Path $projectPath 'run.py'), 'process', '--limit', "$Limit")
if ($RetryFailed) { $taskArgs += '--retry-failed' }
& $venvPython @taskArgs
exit $LASTEXITCODE

