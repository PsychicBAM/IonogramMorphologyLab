$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONPATH = Join-Path $Root "src"
python -m pip install -e . pyinstaller -q
$DistDir = Join-Path $Root "dist\IonogramMorphologyLab"
python scripts/generate_app_icon.py
$Icon = Join-Path $Root "assets\IonogramMorphologyLab.ico"
python -m PyInstaller `
  --noconfirm `
  --clean `
  --name IonogramMorphologyLab `
  --windowed `
  --icon $Icon `
  --paths src `
  --add-data "src/ionogram_morphology_lab/i18n;ionogram_morphology_lab/i18n" `
  --add-data "config;config" `
  --add-data "knowledge_base;knowledge_base" `
  --add-data "matlab_builtin;matlab_builtin" `
  --add-data "rule_packs;rule_packs" `
  --add-data "synthetic_data;synthetic_data" `
  --add-data "docs;docs" `
  --add-data "assets;assets" `
  --add-data "matlab_helpers;matlab_helpers" `
  --add-data "matlab_studio_library;matlab_studio_library" `
  src/ionogram_morphology_lab/app/main.py
# Normalize layout: prefer dist\IonogramMorphologyLab\IonogramMorphologyLab.exe
$OneDir = Join-Path $Root "dist\IonogramMorphologyLab"
$FlatExe = Join-Path $Root "dist\IonogramMorphologyLab.exe"
if ((Test-Path $FlatExe) -and -not (Test-Path (Join-Path $OneDir "IonogramMorphologyLab.exe"))) {
  New-Item -ItemType Directory -Force -Path $OneDir | Out-Null
  Move-Item -Force $FlatExe (Join-Path $OneDir "IonogramMorphologyLab.exe")
  Get-ChildItem (Join-Path $Root "dist") -Directory | Where-Object { $_.Name -eq "IonogramMorphologyLab" -or $_.Name -like "_internal*" } | ForEach-Object { }
}
if (Test-Path (Join-Path $Root "dist\IonogramMorphologyLab\_internal")) {
  # onedir already correct
}
Write-Host "Portable build attempted under dist/IonogramMorphologyLab/"
if (Test-Path (Join-Path $OneDir "IonogramMorphologyLab.exe")) {
  Write-Host "OK: $OneDir\IonogramMorphologyLab.exe"
} else {
  Write-Host "WARN: executable layout may differ; check dist/"
}
