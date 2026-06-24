# Study Budy Desktop: Initial Architecture Audit

## Repository at inspection

The repository is a small Python prototype, not yet a packaged desktop application.

| Area | Current implementation | Assessment |
| --- | --- | --- |
| Desktop UI | None | Missing. The only entry point is a console demonstration script. |
| Web/overlay service | Flask (`app/app.py`) | Basic proof of concept; serves a rotating overlay and JSON endpoints. |
| Twitch chat | Raw Twitch IRC socket (`app/bot/twitch_bot.py`) | Basic command loop, but it contains hard-coded channel details and an exposed token. |
| Commands | `!addtask`, `!tasklist`, `!done`, `!clear` | Functional logic for a simple numbered list, with a streamer/mod allow-list for clearing another user. |
| Storage | `data/tasks.json` | Persists simple task text and completion state but has no IDs, timestamps, ordering controls, backups, recovery, or session model. |
| Overlay | Two HTML templates polling the Flask API | The rotating template is functional in principle; styling and accessibility are prototype-level. |
| Tests/dependencies | No test suite; `requirements.txt` is empty | Incomplete. |

## Working features preserved as product behavior

- Viewer task submission via `!addtask` with `|` as a multiple-task separator.
- Viewer task lists via `!tasklist`.
- Numbered completion via `!done N`.
- Numbered and full-list clearing via `!clear`.
- A rotating participant overlay concept, including prioritizing a participant after `!tasklist`.
- Disk-backed task persistence as a migration source for the new database.

## Incomplete, outdated, or unsafe areas

- There is no desktop application, navigation, menu bar, packaging, first-run setup, or settings.
- `app/main.py` is a hard-coded console demo rather than an application launcher.
- Flask imports in `app/app.py` use an execution-path-sensitive `storage` import.
- The local service binds to every network interface and runs in debug mode; the production overlay must bind to `127.0.0.1` by default.
- The raw Twitch IRC implementation hard-codes a Twitch OAuth token, bot nickname, channel, and a private LAN overlay address. The token must be revoked/rotated and removed from the repository history where possible.
- The overlay has prototype wording and does not have the required two layouts, appearance settings, shared preview rendering, or robust status handling.
- JSON storage does not safely support structured tasks, archives, backups, import/export, or concurrent access.
- No dependencies are declared, and no automated tests exist.
- The local Python launcher is unavailable in this workspace, so the original program could not be run here. The installed `python` command points to Python 2.7, while the Windows Python launcher points to an unavailable Microsoft Store installation.

## Architecture decision

Keep Python to preserve the existing task and command logic, and evolve it into a Windows-first **PySide6 desktop app** with a local Flask overlay service and SQLite storage. This is the smallest reliable step from the current repository: it avoids a wholesale cross-language rewrite while adding a real native desktop shell, testable data layer, and packaging path through PyInstaller.

The desktop UI and overlay will be deliberately separate clients over a small local service boundary:

```text
PySide6 desktop shell ─┬─ SQLite repository (tasks, settings, sessions)
                       ├─ Twitch service (OAuth/device flow and chat reconnect)
                       └─ localhost overlay service ── Browser Source / live preview
```

The task repository owns all mutations. Both the desktop controls and Twitch commands call the same task service; the overlay only reads sanitized task snapshots and settings.

## Implementation plan

1. Secure the prototype: remove credentials and LAN addresses, add runtime configuration and a proper dependency/test baseline.
2. Add the SQLite data layer, migration from the legacy JSON file, backups, import/export, and unit tests.
3. Build the PySide6 shell: saved window state, native menus, Dashboard/Tasks/Connections/Appearance/Help navigation, status controller, and first-run guide.
4. Replace the prototype overlay API with localhost-only, status-aware endpoints and a shared configuration/rendering model; implement Cycling and Streamer-on-top layouts.
5. Implement task management controls, search/filter/reorder/confirmation flows, and rollover behavior.
6. Add Twitch OAuth/secure credential storage and resilient chat connection. Preserve the existing command grammar while tightening validation.
7. Add optional OBS WebSocket support plus in-app OBS/Streamlabs Browser Source guidance.
8. Finish appearance editing, asset management, diagnostics, logs, end-to-end testing, documentation, and PyInstaller installer build instructions.

Each phase will be run and tested before the next one, once a supported Python runtime is available.
