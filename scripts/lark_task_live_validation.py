#!/usr/bin/env python3
"""Run guarded Lark/Feishu task live validation from a source checkout."""

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scripts.skill2workflow_testing.lark_task_live_validation import main


if __name__ == "__main__":
    raise SystemExit(main())
