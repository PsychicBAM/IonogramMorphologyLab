$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONPATH = Join-Path $Root "src"
python -m pip install -e ".[dev]" -q
python -m ionogram_morphology_lab.app.main @args
