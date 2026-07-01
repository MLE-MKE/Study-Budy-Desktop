@echo off
setlocal

REM ---- STUDY BUDY PORTABLE ZIP SCRIPT ----
REM This script compresses the entire PyInstaller folder app into one ZIP file
REM that can be shared with testers.

cd /d "%~dp0"
set "APP_FOLDER=dist\Study Budy"
set "APP_EXE=%APP_FOLDER%\Study Budy.exe"
set "RELEASE_FOLDER=release"
set "ZIP_FILE=%RELEASE_FOLDER%\Study-Budy-Windows-Portable.zip"

echo.
echo Creating Study Budy portable ZIP...
echo.

REM ---- CONFIRM PACKAGED APP EXISTS ----
REM The ZIP should include the whole folder, not only the exe.
if not exist "%APP_EXE%" (
  echo Missing "%APP_EXE%".
  echo Run build_windows.bat first.
  goto failed
)

REM ---- PREPARE RELEASE FOLDER ----
REM Create the release folder and remove any older ZIP with the same name.
if not exist "%RELEASE_FOLDER%" mkdir "%RELEASE_FOLDER%"
if exist "%ZIP_FILE%" del /f /q "%ZIP_FILE%"

REM ---- CREATE PORTABLE ZIP ----
REM PowerShell's Compress-Archive handles folders with spaces reliably.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%APP_FOLDER%' -DestinationPath '%ZIP_FILE%' -Force"
if errorlevel 1 goto failed

REM ---- SHOW FINISHED ZIP LOCATION ----
if not exist "%ZIP_FILE%" (
  echo ZIP creation finished, but the ZIP file was not found.
  goto failed
)

echo.
echo Portable ZIP created:
echo %CD%\%ZIP_FILE%
echo.
exit /b 0

:failed
echo.
echo ZIP creation failed. The command window will stay open so you can read the error.
echo.
pause
exit /b 1
