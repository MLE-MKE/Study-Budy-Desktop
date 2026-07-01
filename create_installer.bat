@echo off
setlocal

rem ---- STUDY BUDY INSTALLER SCRIPT ----
rem This file compiles the Inno Setup installer after the PyInstaller app has
rem already been built into dist\Study Budy.

cd /d "%~dp0"
set "APP_EXE=dist\Study Budy\Study Budy.exe"
set "INNO="

echo.
echo Creating Study Budy Desktop installer...
echo.

rem ---- CONFIRM THE PACKAGED APP EXISTS ----
if not exist "%APP_EXE%" (
  echo The packaged app was not found at "%APP_EXE%".
  echo Run build_windows.bat first.
  pause
  exit /b 1
)

rem ---- LOCATE INNO SETUP COMPILER ----
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "INNO=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined INNO if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "INNO=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined INNO if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "INNO=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

if not defined INNO (
  echo Inno Setup 6 was not found.
  echo Install it from https://jrsoftware.org/isinfo.php and run this again.
  pause
  exit /b 1
)

rem ---- COMPILE INSTALLER ----
"%INNO%" "installer.iss"
if errorlevel 1 goto failed

echo.
echo Installer created:
echo %CD%\release\Study-Budy-Desktop-v0.1.0-Windows-Setup.exe
echo.
pause
exit /b 0

:failed
echo.
echo Installer creation failed. Check the messages above for details.
echo.
pause
exit /b 1
