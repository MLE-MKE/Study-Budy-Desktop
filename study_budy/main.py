"""Application entry point. Requires Python 3.11 or newer."""

from __future__ import annotations

import argparse
import ctypes
import logging
import sys
import traceback

from . import APP_VERSION
from .paths import prepare_user_data_dir


# ---- FATAL STARTUP ERROR HANDLING ----
# If the packaged app fails before the normal window appears, this writes the
# technical details to the user's log folder and shows a plain Windows message.
def show_startup_error(message: str, log_path) -> None:
    ctypes.windll.user32.MessageBoxW(
        None,
        f"{message}\n\nA technical log was saved here:\n{log_path}",
        "Study Budy Desktop could not start",
        0x10,
    )


def main() -> int:
    data_dir = prepare_user_data_dir()
    log_path = data_dir / "logs" / "startup-error.log"
    try:
        if sys.version_info < (3, 11):
            raise RuntimeError("Study Budy Desktop requires Python 3.11 or newer.")
        parser = argparse.ArgumentParser()
        parser.add_argument("--preview", action="store_true", help="Launch with clearly labelled sample data.")
        parser.add_argument("--version", action="version", version=f"Study Budy Desktop {APP_VERSION}")
        args = parser.parse_args()

        from .desktop import run_desktop

        return run_desktop(preview=args.preview)
    except Exception as exc:
        logging.basicConfig(filename=log_path, level=logging.ERROR)
        logging.error("Study Budy failed to start.\n%s", traceback.format_exc())
        show_startup_error(
            "Study Budy ran into a startup problem. Please restart the app. "
            "If it keeps happening, send the log file to support.",
            log_path,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
