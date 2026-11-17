#!/usr/bin/env python3
"""Qualify input-aware quickstart using only the selected installed CLI."""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.skill2workflow_testing.quickstart_smoke import _qualify_input_quickstart


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', required=True, type=Path)
    parser.add_argument('--work-dir', required=True, type=Path)
    args = parser.parse_args()
    environment = dict(os.environ)
    environment.pop('PYTHONPATH', None)
    environment['PYTHONNOUSERSITE'] = '1'
    result = _qualify_input_quickstart(args.executable.resolve(), args.work_dir.resolve(), environment)
    print(json.dumps(result, sort_keys=True))
    return 0 if all(result.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
