#!/usr/bin/env python3
"""Verify editable install and console-script packaging from a source checkout."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path
from typing import Dict, List


DEFAULT_WORK_DIR = Path("/tmp/skill2workflow-package-smoke")


def run_package_smoke(repo_root: Path, work_dir: Path = DEFAULT_WORK_DIR, reset: bool = True) -> Dict[str, object]:
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    if reset:
        _reset_work_dir(repo_root, work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    venv_dir = work_dir / "venv"
    venv.EnvBuilder(with_pip=True, clear=True).create(venv_dir)

    python_bin = _venv_executable(venv_dir, "python")
    console_script = _venv_executable(venv_dir, "skill2workflow")

    tooling = _run(
        [str(python_bin), "-m", "pip", "install", "--upgrade", "pip", "setuptools>=68"],
        cwd=repo_root,
    )
    install = _run(
        [str(python_bin), "-m", "pip", "install", "--no-build-isolation", "-e", str(repo_root)],
        cwd=repo_root,
    )
    version = _run(
        [
            str(python_bin),
            "-c",
            "import importlib.metadata as metadata; print(metadata.version('skill2workflow'))",
        ],
        cwd=repo_root,
    ).strip()
    help_output = _run([str(console_script), "--help"], cwd=repo_root)
    if "usage:" not in help_output:
        raise RuntimeError("installed skill2workflow --help did not print usage text")
    validate_output = _run(
        [
            str(console_script),
            "validate",
            str(repo_root / "examples" / "workflows" / "approval-flow.workflow.json"),
            "--format",
            "json",
        ],
        cwd=repo_root,
    )
    validate_result = json.loads(validate_output)
    if not validate_result.get("valid"):
        raise RuntimeError(f"installed skill2workflow validate returned invalid result: {validate_output}")

    return {
        "ok": True,
        "work_dir": str(work_dir),
        "venv": str(venv_dir),
        "python": str(python_bin),
        "console_script": str(console_script),
        "package": "skill2workflow",
        "version": version,
        "tooling_command": tooling.splitlines()[-1] if tooling.splitlines() else "",
        "install_command": install.splitlines()[-1] if install.splitlines() else "",
        "help_contains_usage": True,
        "validate_status": True,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="package_smoke", description="Verify editable package install locally.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--no-reset", action="store_true", help="Keep existing package smoke work directory contents.")
    args = parser.parse_args(argv)

    result = run_package_smoke(args.repo_root, args.work_dir, reset=not args.no_reset)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _run(command: List[str], cwd: Path) -> str:
    completed = subprocess.run(command, cwd=str(cwd), text=True, capture_output=True)
    if completed.returncode != 0:
        raise RuntimeError(
            "command failed: {command}\nexit: {code}\nstdout:\n{stdout}\nstderr:\n{stderr}".format(
                command=" ".join(command),
                code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        )
    return completed.stdout


def _venv_executable(venv_dir: Path, name: str) -> Path:
    scripts_dir = "Scripts" if os.name == "nt" else "bin"
    suffix = ".exe" if os.name == "nt" and name != "python" else ""
    return venv_dir / scripts_dir / f"{name}{suffix}"


def _reset_work_dir(repo_root: Path, work_dir: Path) -> None:
    if work_dir == repo_root or repo_root in work_dir.parents:
        raise ValueError("package smoke work_dir must be outside the repository when reset is enabled")
    if work_dir == Path(work_dir.anchor):
        raise ValueError("package smoke work_dir cannot be a filesystem root")
    if work_dir.exists():
        shutil.rmtree(work_dir)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
