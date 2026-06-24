"""Application entry point. Requires Python 3.11 or newer."""

from __future__ import annotations

import sys

from .desktop import run_desktop


def main() -> int:
    if sys.version_info < (3, 11):
        raise RuntimeError("Study Budy Desktop requires Python 3.11 or newer.")
    return run_desktop()


if __name__ == "__main__":
    raise SystemExit(main())
