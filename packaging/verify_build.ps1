$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$exe = Join-Path $Root "dist\IonogramMorphologyLab\IonogramMorphologyLab.exe"
if (Test-Path $exe) {
  Write-Host "OK: $exe exists"
} else {
  Write-Host "MISSING: $exe (run build_portable.ps1)"
  exit 1
}
# Ensure no Article3 secret paths packaged
$bad = Get-ChildItem -Path (Join-Path $Root "dist") -Recurse -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -match "09_blinded_review_package\\secret|11_rendered_frames|21_review_progress" }
if ($bad) { Write-Host "FAIL: forbidden paths in dist"; exit 2 }
Write-Host "verify_build OK"
