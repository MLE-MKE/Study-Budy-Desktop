# Windows packaging

Study Budy Desktop targets Windows 10 and Windows 11, 64-bit. End users should receive either the installer or portable ZIP and should not need Python, Git, a compiler, or a virtual environment.

## Current release status

Version `0.1.0` is packaged as an unsigned internal test build. Do not describe it as production-ready until the live Twitch acceptance tests and a clean-machine Windows test both pass.

## User data and credentials

- Writable app data is stored under `%LOCALAPPDATA%\Study Budy`.
- Logs are stored under `%LOCALAPPDATA%\Study Budy\logs`.
- SQLite data is stored outside the installation folder.
- OAuth access and refresh tokens remain in Windows Credential Manager through `keyring`.
- Build outputs must not include local databases, logs, `.env` files, authorization codes, access tokens, refresh tokens, or personal Twitch metadata.

## Client ID strategy

The initial release is bring-your-own Twitch Client ID:

- Do not package a personal developer Client ID.
- Do not package a Client Secret.
- Users register their own Twitch application as a public/native-style app and paste only the public Client ID into Study Budy.
- Changing the Client ID should require reauthorizing accounts if existing OAuth tokens were issued for a different Twitch application.

## Build prerequisites

- Windows 10 or Windows 11, 64-bit
- Python 3.11 or newer for the build machine
- Inno Setup 6 if you want the installer
- Project dependencies installed in the build Python environment

Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-packaging.txt
```

## Build command

From the repository root:

```powershell
.\packaging\build_windows.ps1 -Python .\.venv314\Scripts\python.exe
```

Useful options:

```powershell
.\packaging\build_windows.ps1 -SkipInstaller
.\packaging\build_windows.ps1 -SkipTests
```

The script:

1. Confirms Windows and Python 3.11+.
2. Runs tests unless skipped.
3. Cleans old build output.
4. Runs `packaging/study_budy.spec`.
5. Verifies required packaged assets.
6. Creates `release\Study-Budy-Desktop-v0.1.0-Windows-Portable.zip`.
7. Builds `release\Study-Budy-Desktop-v0.1.0-Windows-Setup.exe` if Inno Setup is installed.
8. Prints SHA-256 checksums.

## PyInstaller resources

The maintained spec includes:

- Application icon and logo assets
- SVG UI icons
- Overlay template HTML
- Task overlay HTML/CSS/JavaScript
- Timer overlay HTML/CSS/JavaScript
- Check-In overlay HTML/CSS/JavaScript
- Bundled fonts and font license
- Keyring backend hidden imports
- PySide/Qt dependencies collected by PyInstaller hooks

Runtime file lookup is centralized in `study_budy.resources.resource_path()` so source execution and packaged execution use the same code path.

## Installer behavior

The Inno Setup script installs per-user under:

```text
%LOCALAPPDATA%\Programs\Study Budy Desktop
```

It creates a Start Menu shortcut and offers an optional Desktop shortcut. Normal uninstall removes application files but preserves `%LOCALAPPDATA%\Study Budy` so users do not accidentally lose unfinished tasks or settings.

## Required manual acceptance tests

Before public release, verify:

1. Streamer OAuth completes.
2. Streamer chat listener reaches Listening.
3. Commands work while the Twitch channel is offline.
4. Bot OAuth completes separately.
5. Bot sends responses in the streamer channel.
6. Automatic response mode falls back to streamer.
7. `!addtask`, `!tasklist`, `!done`, `!clear`, and `!clearall` work.
8. `!ttimer` commands work for streamer and moderators.
9. `!checkin`, `!checkout`, and `!dance` work.
10. `/overlay`, `/timer`, and `/checkin` work in OBS Browser Sources.
11. Appearance settings save and survive restart.
12. Secure credentials survive restart.
13. No token or private account data appears in logs.
14. The program closes cleanly without leaving the overlay server or chat listener running.
15. A clean Windows machine without Python can install/extract, launch, use overlays, restart, and uninstall as documented.

## Known warnings

- The current build is unsigned and may trigger Windows SmartScreen or antivirus warnings.
- The build script skips installer creation when Inno Setup is not installed.
- Do not tag a production release until clean-machine and live Twitch tests pass.
