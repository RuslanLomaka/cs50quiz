$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$ruffPath = Join-Path $projectRoot ".venv\Scripts\ruff.exe"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Create .venv and install requirements-dev.txt first."
}

Push-Location $projectRoot
try {
    & $ruffPath check .
    if ($LASTEXITCODE -ne 0) { throw "Ruff lint failed." }
    & $ruffPath format --check .
    if ($LASTEXITCODE -ne 0) { throw "Ruff format check failed." }
    & $pythonPath manage.py makemigrations --check --dry-run
    if ($LASTEXITCODE -ne 0) { throw "Migration drift check failed." }
    & $pythonPath -m coverage run -m pytest
    if ($LASTEXITCODE -ne 0) { throw "Tests failed." }
    & $pythonPath -m coverage report
    if ($LASTEXITCODE -ne 0) { throw "Coverage threshold failed." }
    & $pythonPath manage.py check
    if ($LASTEXITCODE -ne 0) { throw "Django system check failed." }
} finally {
    Pop-Location
}
