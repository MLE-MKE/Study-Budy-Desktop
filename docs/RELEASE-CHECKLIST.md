# Study Budy Desktop release checklist

Use this checklist before publishing a GitHub release or sharing a public installer.

## Build identity

- [ ] `pyproject.toml` version is correct.
- [ ] `study_budy.__version__` matches the project version.
- [ ] About dialog shows the same version.
- [ ] Sidebar shows the same version.
- [ ] PyInstaller version metadata uses the same version.
- [ ] Installer filename uses the same version.
- [ ] Portable ZIP filename uses the same version.
- [ ] Git tag is `v0.1.0` or the matching release version.

## Secret and data safety

- [ ] No `.env` file is included.
- [ ] No local database is included.
- [ ] No logs are included.
- [ ] No Twitch Client Secret is included.
- [ ] No access tokens, refresh tokens, device codes, or authorization codes are included.
- [ ] Credential storage uses Windows Credential Manager through `keyring`.
- [ ] Writable data is stored under `%LOCALAPPDATA%\Study Budy`.

## Automated checks

- [ ] `python -m pytest` passes.
- [ ] `python -m compileall -q study_budy tests` passes.
- [ ] `packaging/smoke_packaged.ps1` passes.
- [ ] Portable ZIP is created.
- [ ] Installer is created, or the missing Inno Setup dependency is documented.
- [ ] SHA-256 checksums are recorded.

## Live acceptance tests

- [ ] Streamer OAuth completes.
- [ ] Streamer chat listener reaches Listening.
- [ ] Commands work while the Twitch channel is offline.
- [ ] Bot OAuth completes separately.
- [ ] Bot sends responses in the streamer channel.
- [ ] Automatic response mode falls back to streamer.
- [ ] Task commands work: `!addtask`, `!tasklist`, `!done`, `!clear`, `!clearall`.
- [ ] Timer commands work for streamer and moderators.
- [ ] Check-In commands work: `!checkin`, `!checkout`, `!dance`.
- [ ] `/overlay`, `/timer`, and `/checkin` load in OBS Browser Sources.
- [ ] Appearance settings survive restart.
- [ ] Secure credentials survive restart.
- [ ] Logs do not reveal tokens or private account data.
- [ ] Closing the app stops the overlay server and chat listener.

## Clean-machine test

- [ ] Test on Windows 10 or 11 without Python installed.
- [ ] Installer launches by double-click.
- [ ] Portable ZIP launches by double-click.
- [ ] No missing-DLL or Python-required error appears.
- [ ] First-run setup works.
- [ ] OBS overlay URLs work.
- [ ] Restarting Windows preserves settings and credentials.
- [ ] Uninstall removes app files.
- [ ] Uninstall preserves user data unless a future explicit delete-data option is added.

## Release warning

The `0.1.0` build is unsigned unless HotKey LLC signs it. Unsigned builds may trigger SmartScreen or antivirus warnings. Do not claim the build is warning-free.
