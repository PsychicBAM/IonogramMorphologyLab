$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
# Requires Inno Setup (ISCC) on PATH. Otherwise document blocker.
$iscc = Get-Command ISCC -ErrorAction SilentlyContinue
if (-not $iscc) {
  Write-Host "BLOCKER: Inno Setup ISCC not found. Portable build may still be used."
  Write-Host "Prepared definition: packaging/IonogramMorphologyLab.iss"
  exit 0
}
& ./packaging/build_portable.ps1
& ISCC "packaging/IonogramMorphologyLab.iss"
