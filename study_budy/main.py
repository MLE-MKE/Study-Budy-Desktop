"""Application entry point. Requires Python 3.11 or newer."""

from __future__ import annotations

import sys
import argparse

from .desktop import run_desktop


def main() -> int:
    if sys.version_info < (3, 11):
        raise RuntimeError("Study Budy Desktop requires Python 3.11 or newer.")
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true", help="Launch with clearly labelled sample data.")
    args = parser.parse_args()
    return run_desktop(preview=args.preview)


if __name__ == "__main__":
    raise SystemExit(main())
