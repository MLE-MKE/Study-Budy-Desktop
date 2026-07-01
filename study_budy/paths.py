"""Safe user-data paths; application data never belongs in the install folder."""

from __future__ import annotations

import os
from pathlib import Path


# ---- USER DATA DIRECTORY ----
# This keeps settings, logs, databases, uploads, and backups in the user's
# Windows profile instead of the application install folder.
def user_data_dir() -> Path:
    root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if root:
        return Path(root) / "Study Budy"
    return Path.home() / ".study-budy"


# ---- USER DATA FOLDER CREATION ----
# This creates the app's writable folders on startup, so a fresh install can
# save settings and logs immediately. Peepeepoo poo, now the folder exists.
def prepare_user_data_dir() -> Path:
    path = user_data_dir()
    for child in (path, path / "backups", path / "uploads", path / "logs"):
        child.mkdir(parents=True, exist_ok=True)
    return path
