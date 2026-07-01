@echo off
setlocal

REM ---- STUDY BUDY WINDOWS BUILD SCRIPT ----
REM This script builds Study Budy into a Windows folder app that a user can
REM open by double-clicking Study Budy.exe.

cd /d "%~dp0"

echo.
echo Building Study Budy Desktop for Windows...
echo.

REM ---- CHECK REQUIRED FILES ----
REM The launcher must live in the repository root, next to README.md.
if not exist "launch_study_budy.py" (
  echo Missing launch_study_budy.py.
  echo Make sure this script is running from the Study Budy repository root.
  goto failed
)

REM The package folder contains the real Study Budy application code.
if not exist "study_budy\" (
  echo Missing study_budy folder.
  echo Make sure this script is running from the Study Budy repository root.
  goto failed
)

REM ---- CHOOSE PYTHON ENVIRONMENT ----
REM Prefer the project's .venv if it exists. Otherwise use the system py launcher.
set "PYTHON=py -3"
if exist ".venv\Scripts\python.exe" (
  call ".venv\Scripts\activate.bat"
  set "PYTHON=python"
)

REM ---- INSTALL APP DEPENDENCIES ----
REM The packaged app needs the runtime packages available while PyInstaller
REM analyzes the program.
%PYTHON% -m pip install -r requirements.txt
if errorlevel 1 goto failed

REM ---- INSTALL PYINSTALLER IF NEEDED ----
REM PyInstaller is only needed on the builder's computer, not on the user's.
%PYTHON% -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
  echo Installing PyInstaller...
  %PYTHON% -m pip install --upgrade pip
  if errorlevel 1 goto failed
  %PYTHON% -m pip install -r requirements-build.txt
  if errorlevel 1 goto failed
)

REM ---- CLEAN OLD BUILD OUTPUT ----
REM Removing old folders avoids mixing stale files into the new app.
if exist "build\" rmdir /s /q "build"
if exist "dist\" rmdir /s /q "dist"

REM ---- RUN PYINSTALLER ----
REM Study Budy uses a one-directory build because it needs HTML, CSS,
REM JavaScript, images, icons, fonts, and Qt support files beside the exe.
%PYTHON% -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name "Study Budy" ^
  --icon "study_budy\assets\study-budy-icon.ico" ^
  --add-data "study_budy\templates;study_budy\templates" ^
  --add-data "study_budy\assets;study_budy\assets" ^
  --add-data "study_budy\overlay;study_budy\overlay" ^
  launch_study_budy.py
if errorlevel 1 goto failed

REM ---- SHOW FINISHED APPLICATION LOCATION ----
if not exist "dist\Study Budy\Study Budy.exe" (
  echo PyInstaller finished, but Study Budy.exe was not found.
  goto failed
)

echo.
echo Build succeeded.
echo Finished application:
echo %CD%\dist\Study Budy\Study Budy.exe
echo.
echo Distribute the entire "dist\Study Budy" folder, not only the exe.
echo.
exit /b 0

:failed
echo.
echo Build failed. The command window will stay open so you can read the error.
echo.
pause
exit /b 1
