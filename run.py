#!/usr/bin/env python3
"""JobbLoot -- just run it.

Starts all four services (Django, CV Engine, Cover Letter Engine, frontend)
with no install or wizard steps.  Run:  python run.py

Everything must already be set up -- if the project venv is missing, run
``python setup.py`` once first. To start Django only, use:
    .venv\\Scripts\\python.exe manage.py run_all
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IS_WIN = sys.platform == "win32"


def main() -> None:
    venv_python = ROOT / ".venv" / ("Scripts" if IS_WIN else "bin") / "python.exe"
    if not venv_python.exists():
        print("[FAIL] Project venv not found -- run `python setup.py` once first.")
        sys.exit(1)

    from setup import run_app

    run_app()


if __name__ == "__main__":
    main()
