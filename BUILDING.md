# Building Study Budy Desktop

This file explains how Study Budy is packaged for Windows.

## Program entry point

The app starts from:

```text
study_budy/main.py
```

For PyInstaller, the launcher is:

```text
packaging/pyinstaller_entry.py
```

The installed executable is named:

```text
Study Budy.exe
```

## Resource paths

Bundled read-only files are resolved through:

```text
study_budy/resources.py
```

Use `resource_path()` for images, icons, fonts, templates, HTML, CSS, and JavaScript. It works from source and from a PyInstaller build.

## User-data paths

Writable files are resolved through:

```text
study_budy/paths.py
```

The app stores writable user data under:

```text
%LOCALAPPDATA%\Study Budy
```

Do not write user settings, logs, uploads, backups, or databases into the install directory.

## Dependencies

Runtime dependencies are in:

```text
requirements.txt
```

Build/test dependencies are in:

```text
requirements-build.txt
```

## Build the portable app

Double-click:

```text
build_windows.bat
```

Or run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_windows.ps1 -Python .\.venv314\Scripts\python.exe
```

The build uses:

```text
packaging/study_budy.spec
```

The portable app is created at:

```text
release\Study-Budy-Desktop-v0.1.0-Windows-Portable.zip
```

## Create the installer

Double-click:

```text
create_installer.bat
```

Or compile either Inno Setup script:

```text
installer.iss
packaging/windows/StudyBudy.iss
```

The installer is created at:

```text
release\Study-Budy-Desktop-v0.1.0-Windows-Setup.exe
```

## Files that must never be distributed

Do not distribute:

- `.git`
- `.env`
- virtual environments
- `build`
- development logs
- local databases
- OAuth access tokens
- OAuth refresh tokens
- Twitch Client Secrets
- personal Twitch metadata
- test caches
- source-only prototype data unless it is intentionally sanitized

## Change the version number

Update all of these together:

- `pyproject.toml`
- `study_budy/__init__.py`
- `packaging/version_info.txt`
- `packaging/windows/StudyBudy.iss`
- `installer.iss`
- release filenames in scripts/docs

## Clean installation test

Before public release:

1. Test on Windows 10 or 11 without Python installed.
2. Install `Study-Budy-Desktop-v0.1.0-Windows-Setup.exe`.
3. Launch from the Start Menu.
4. Confirm the app opens without missing-DLL errors.
5. Start the overlay service.
6. Confirm `/overlay`, `/timer`, and `/checkin` load.
7. Connect Twitch test accounts.
8. Confirm chat commands work.
9. Restart Windows and confirm settings remain.
10. Uninstall and confirm app files are removed while user data is preserved.
