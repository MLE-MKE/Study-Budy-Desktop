@echo off
setlocal

rem ---- STUDY BUDY WINDOWS BUILD SCRIPT ----
rem This file is meant to be double-clicked by a non-technical builder. It
rem creates a local virtual environment, installs dependencies, and runs the
rem maintained PowerShell build script.

cd /d "%~dp0"
set "VENV=.venv-build"
set "PYTHON=%VENV%\Scripts\python.exe"

echo.
echo Building Study Budy Desktop for Windows...
echo.

rem ---- CREATE OR REUSE VIRTUAL ENVIRONMENT ----
if not exist "%PYTHON%" (
  echo Creating build virtual environment...
  py -3 -m venv "%VENV%"
  if errorlevel 1 goto failed
)

rem ---- INSTALL RUNTIME AND BUILD DEPENDENCIES ----
echo Updating pip and installing dependencies...
"%PYTHON%" -m pip install --upgrade pip
if errorlevel 1 goto failed
"%PYTHON%" -m pip install -r requirements.txt -r requirements-build.txt
if errorlevel 1 goto failed

rem ---- RUN THE MAINTAINED PACKAGING SCRIPT ----
echo Running PyInstaller and creating release files...
powershell -NoProfile -ExecutionPolicy Bypass -File ".\packaging\build_windows.ps1" -Python "%PYTHON%"
if errorlevel 1 goto failed

echo.
echo Build succeeded. Release files are in:
echo %CD%\release
echo.
pause
exit /b 0

:failed
echo.
echo Build failed. Check the messages above for details.
echo.
pause
exit /b 1
