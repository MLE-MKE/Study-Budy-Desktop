Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Paths = @(
  (Join-Path $Root "build"),
  (Join-Path $Root "dist"),
  (Join-Path $Root "release")
)

foreach ($Path in $Paths) {
  if (Test-Path $Path) {
    Remove-Item -LiteralPath $Path -Recurse -Force
  }
}

Write-Host "Cleaned Windows packaging outputs."
