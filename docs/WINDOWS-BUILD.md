# Building Study Budy for Windows

Study Budy requires Python 3.11 or newer for development. End users receive the packaged application and do not need Python or developer tools installed.

## Development setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest
python -m study_budy.main
```

## Portable Windows build

```powershell
py -3.11 -m PyInstaller --noconfirm --windowed --name "Study Budy" --add-data "study_budy/templates;study_budy/templates" --add-data "study_budy/assets;study_budy/assets" -m study_budy.main
```

The portable build is created at `dist\Study Budy\Study Budy.exe`. The application stores its database, uploads, backups, and logs under `%LOCALAPPDATA%\Study Budy`, outside its installation folder.

For an installer, package the resulting folder with an installer tool such as Inno Setup. Include an uninstall entry and preserve `%LOCALAPPDATA%\Study Budy` by default so users do not lose unfinished tasks.
