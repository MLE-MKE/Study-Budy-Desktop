# Study Budy Desktop

Study Budy is a Windows-first desktop task manager for Twitch study, coworking, productivity, and body-doubling streams. It gives streamers a local OBS or Streamlabs Desktop Browser Source overlay and a desktop control panel for streamer and viewer tasks.

![Study Budy desktop mockup](docs/design/desktop-shell-mockup.svg)

## Current foundation

- Native PySide6 desktop window with Dashboard, Tasks, Connections, Appearance, Timer, Check-In, and Help screens.
- SQLite-backed participant, task, completion, ordering, settings, backup, export, and import data.
- One-time migration of the prototype `data/tasks.json` file.
- Local-only (`127.0.0.1`) Browser Source overlays for tasks, timer, and Check-In.
- Cycling and Streamer-on-top task layout modes.
- Overlay URL copying, preview, start/stop/restart controls, and explicit status text.
- Appearance settings for layout, font, text/background color, opacity, and Check-In themes.
- Official Twitch commands: `!addtask`, `!tasklist`, `!done`, `!clear`, `!clearall`, `!checkin`, `!checkout`, `!dance`, and moderator/streamer `!ttimer`.
- Viewers can add several tasks at once with `!addtask task one | task two | task three`.

## Quick start for developers

Study Budy requires Python 3.11 or newer. See [Windows build instructions](docs/WINDOWS-BUILD.md).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m study_budy.main
```

## Windows test packaging

The maintained Windows packaging flow creates an unsigned internal test build:

```powershell
.\packaging\build_windows.ps1 -Python .\.venv314\Scripts\python.exe
```

Expected artifacts:

- `release\Study-Budy-Desktop-v0.1.0-Windows-Portable.zip`
- `release\Study-Budy-Desktop-v0.1.0-Windows-Setup.exe` when Inno Setup 6 is installed

See [the release checklist](docs/RELEASE-CHECKLIST.md) before sharing a public build.

## OBS and Streamlabs Desktop

Start the task system, copy the `http://127.0.0.1:5155/overlay` URL, and add it as a Browser Source. Use 1920 × 1080 at 30 FPS as a starting point, then resize it in your scene. The overlay background is transparent outside its task cards.

Additional local overlay URLs:

- Task overlay: `/overlay`
- Timer overlay: `/timer`
- Check-In overlay: `/checkin`

## Data, backups, and privacy

Application data is stored under `%LOCALAPPDATA%\Study Budy`. Export task data with **File → Export tasks**. Twitch OAuth tokens are stored through Windows Credential Manager via `keyring`, not in the install folder. The Browser Source binds only to localhost by default.

Never place Twitch tokens, authorization codes, Client Secrets, local databases, or debug logs in source files or commits.

## Current limitations

- The Windows build is currently unsigned and should be treated as an internal test build until live Twitch and clean-machine release tests pass.
- Optional OBS WebSocket integration remains a future enhancement.
- Image upload/asset controls and advanced rollover choices need more release-hardening.
- The legacy prototype Flask endpoints remain for compatibility while the new local overlay service is adopted.

See [the architecture audit and implementation plan](docs/architecture-audit.md) for the original prototype assessment and phased plan.
