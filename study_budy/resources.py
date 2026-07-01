"""Runtime resource paths for source and packaged builds."""

from __future__ import annotations

import sys
from pathlib import Path


# ---- RESOURCE PATH HANDLING ----
# This section keeps bundled read-only files working after PyInstaller moves
# them into its packaged app folder. It also keeps normal source-code runs using
# the regular study_budy package directory.
def package_root() -> Path:
    """Return the directory containing bundled Study Budy runtime files."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        bundled = base / "study_budy"
        return bundled if bundled.exists() else base
    return Path(__file__).resolve().parent


# ---- RESOURCE FILE LOOKUP ----
# This helper is the one place the rest of the app should use for bundled
# images, icons, fonts, HTML, CSS, and JavaScript files.
def resource_path(relative_path: str | Path) -> Path:
    """Resolve a runtime resource from the Study Budy package root."""
    return package_root() / Path(relative_path)
