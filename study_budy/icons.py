"""Small SVG icon helper for the Study Budy desktop UI."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon

ASSETS_DIR = Path(__file__).with_name("assets")
LOGO_PATH = ASSETS_DIR / "study-budy-logo.png"
ICON_DIR = ASSETS_DIR / "icons"


def icon_path(name: str) -> Path:
    return ICON_DIR / f"{name}.svg"


def icon(name: str) -> QIcon:
    return QIcon(str(icon_path(name)))
