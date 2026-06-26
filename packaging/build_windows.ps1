param(
  [switch]$SkipTests,
  [switch]$SkipInstaller,
  [string]$Python = "python"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Version = "0.1.0"
$ReleaseDir = Join-Path $Root "release"
$DistDir = Join-Path $Root "dist"
$AppDir = Join-Path $DistDir "Study Budy"
$ExePath = Join-Path $AppDir "Study Budy.exe"
$PortableZip = Join-Path $ReleaseDir "Study-Budy-Desktop-v$Version-Windows-Portable.zip"
$InstallerPath = Join-Path $ReleaseDir "Study-Budy-Desktop-v$Version-Windows-Setup.exe"

$IsRunningOnWindows = [System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform(
  [System.Runtime.InteropServices.OSPlatform]::Windows
)
if (-not $IsRunningOnWindows) {
  throw "Windows packaging must be run on Windows."
}

Push-Location $Root
try {
  $pythonVersion = & $Python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
  $majorMinor = $pythonVersion.Split(".")
  if ([int]$majorMinor[0] -lt 3 -or ([int]$majorMinor[0] -eq 3 -and [int]$majorMinor[1] -lt 11)) {
    throw "Study Budy packaging requires Python 3.11 or newer. Found $pythonVersion."
  }

  if (-not $SkipTests) {
    & $Python -m pytest
  }

  & $PSScriptRoot\clean_windows.ps1
  New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null

  & $Python -m PyInstaller --noconfirm (Join-Path $Root "packaging\study_budy.spec")

  $RequiredFiles = @(
    $ExePath,
    (Join-Path $AppDir "_internal\study_budy\templates\overlay.html"),
    (Join-Path $AppDir "_internal\study_budy\overlay\checkin.js"),
    (Join-Path $AppDir "_internal\study_budy\overlay\timer.js"),
    (Join-Path $AppDir "_internal\study_budy\assets\study-budy-logo.png"),
    (Join-Path $AppDir "_internal\study_budy\assets\fonts\PressStart2P-Regular.ttf")
  )

  foreach ($File in $RequiredFiles) {
    if (-not (Test-Path $File)) {
      throw "Packaged build is missing required runtime file: $File"
    }
  }
  & $PSScriptRoot\smoke_packaged.ps1 -AppDir $AppDir

  $zipCreated = $false
  for ($attempt = 1; $attempt -le 6; $attempt++) {
    try {
      Compress-Archive -Path (Join-Path $AppDir "*") -DestinationPath $PortableZip -Force
      $zipCreated = $true
      break
    } catch {
      if ($attempt -eq 6) {
        throw
      }
      Write-Warning "Portable ZIP creation was blocked by a temporary file lock. Retrying in 2 seconds..."
      Start-Sleep -Seconds 2
    }
  }
  if (-not $zipCreated) {
    throw "Portable ZIP was not created."
  }

  $InnoCompiler = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
  if (-not (Test-Path $InnoCompiler)) {
    $InnoCompiler = "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
  }
  if (-not (Test-Path $InnoCompiler)) {
    $InnoCompiler = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
  }
  if (-not $SkipInstaller -and (Test-Path $InnoCompiler)) {
    & $InnoCompiler (Join-Path $Root "packaging\windows\StudyBudy.iss")
  } elseif (-not $SkipInstaller) {
    Write-Warning "Inno Setup 6 was not found. Portable ZIP was created; installer was skipped."
  }

  $Artifacts = @($PortableZip)
  if (Test-Path $InstallerPath) {
    $Artifacts += $InstallerPath
  }

  foreach ($Artifact in $Artifacts) {
    $hash = Get-FileHash -Algorithm SHA256 $Artifact
    Write-Host "$($hash.Hash)  $Artifact"
  }
} finally {
  Pop-Location
}
