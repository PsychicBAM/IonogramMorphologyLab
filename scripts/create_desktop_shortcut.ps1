# Create a desktop shortcut to Ionogram Morphology Lab (no admin required).
# Prefer the portable EXE when present; otherwise fall back to the Python module.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Ionogram Morphology Lab.lnk"
$exeCandidates = @(
    (Join-Path $root "dist\IonogramMorphologyLab\IonogramMorphologyLab.exe"),
    (Join-Path $root "IonogramMorphologyLab.exe"),
    (Join-Path $PSScriptRoot "..\IonogramMorphologyLab.exe")
)
$icon = Join-Path $root "assets\IonogramMorphologyLab.ico"
$target = $null
$arguments = ""
$workDir = $root
foreach ($candidate in $exeCandidates) {
    if (Test-Path $candidate) {
        $target = (Resolve-Path $candidate).Path
        $workDir = Split-Path -Parent $target
        break
    }
}
if (-not $target) {
    $python = (Get-Command python -ErrorAction Stop).Source
    $target = $python
    $arguments = "-m ionogram_morphology_lab"
}
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $target
$shortcut.Arguments = $arguments
$shortcut.WorkingDirectory = $workDir
$shortcut.Description = "Ionogram Morphology Lab"
if (Test-Path $icon) {
    $shortcut.IconLocation = "$icon,0"
} elseif ($target -like "*.exe") {
    $shortcut.IconLocation = "$target,0"
}
$shortcut.Save()
Write-Output "Created desktop shortcut: $shortcutPath"
Write-Output "Target: $target $arguments"
