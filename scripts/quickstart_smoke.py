#!/usr/bin/env python3
"""Run the installed-wheel controlled quickstart drill from a checkout."""

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from skill2workflow.quickstart_smoke import main


if __name__ == "__main__":
    raise SystemExit(main())
