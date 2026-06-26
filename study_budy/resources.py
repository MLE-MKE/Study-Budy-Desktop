"""Runtime resource paths for source and packaged builds."""

from __future__ import annotations

import sys
from pathlib import Path


def package_root() -> Path:
    """Return the directory containing bundled Study Budy runtime files."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        bundled = base / "study_budy"
        return bundled if bundled.exists() else base
    return Path(__file__).resolve().parent


def resource_path(relative_path: str | Path) -> Path:
    """Resolve a runtime resource from the Study Budy package root."""
    return package_root() / Path(relative_path)
