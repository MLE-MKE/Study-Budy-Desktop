# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir build for Study Budy Desktop."""

from pathlib import Path

ROOT = Path.cwd()
PACKAGE = ROOT / "study_budy"
APP_NAME = "Study Budy"

# ---- PACKAGED RESOURCE PATHS ----
# These read-only folders are copied beside the packaged exe so the task,
# timer, and Check-In overlays can load their HTML, CSS, JavaScript, fonts,
# icons, and images after PyInstaller builds the app.
datas = [
    (str(PACKAGE / "assets"), "study_budy/assets"),
    (str(PACKAGE / "overlay"), "study_budy/overlay"),
    (str(PACKAGE / "templates"), "study_budy/templates"),
]

# ---- HIDDEN IMPORTS ----
# Keyring chooses credential backends dynamically, so the Windows credential
# backend is named here to keep secure Twitch token storage available.
hiddenimports = [
    "keyring.backends.Windows",
    "keyring.backends.fail",
    "keyring.backends.null",
]

a = Analysis(
    [str(ROOT / "launch_study_budy.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PACKAGE / "assets" / "study-budy-icon.ico"),
    version=str(ROOT / "packaging" / "version_info.txt"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
