param(
  [string]$AppDir = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..")) "dist\Study Budy")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RequiredFiles = @(
  "Study Budy.exe",
  "_internal\study_budy\templates\overlay.html",
  "_internal\study_budy\overlay\checkin.html",
  "_internal\study_budy\overlay\checkin.css",
  "_internal\study_budy\overlay\checkin.js",
  "_internal\study_budy\overlay\timer.html",
  "_internal\study_budy\overlay\timer.css",
  "_internal\study_budy\overlay\timer.js",
  "_internal\study_budy\assets\study-budy-logo.png",
  "_internal\study_budy\assets\study-budy-icon.ico",
  "_internal\study_budy\assets\fonts\PressStart2P-Regular.ttf",
  "_internal\study_budy\assets\fonts\PressStart2P-OFL.txt"
)

foreach ($Relative in $RequiredFiles) {
  $Path = Join-Path $AppDir $Relative
  if (-not (Test-Path $Path)) {
    throw "Packaged smoke test failed. Missing: $Path"
  }
}

$QtPlatform = Get-ChildItem -Path $AppDir -Recurse -Filter "qwindows.dll" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $QtPlatform) {
  throw "Packaged smoke test failed. Qt qwindows.dll platform plugin was not found."
}

Write-Host "Packaged asset smoke test passed for $AppDir"
