$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONPATH = Join-Path $Root "src"
python -m pip install -e ".[dev]" -q
python scripts/_bootstrap_kb_docs.py
python -c "from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library; write_synthetic_mat_library()"
python -m pytest -q
python scripts/validate_mvp.py
