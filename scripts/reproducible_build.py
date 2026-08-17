#!/usr/bin/env python3
"""Prove that two fixed-epoch builds produce the same skill2workflow wheel."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

try:
    from release_manifest import build_release_manifest
except ImportError:  # pragma: no cover - exercised when imported as scripts.reproducible_build
    from scripts.release_manifest import build_release_manifest


REPRODUCIBLE_BUILD_SCHEMA_VERSION = "skill2workflow-reproducible-build-0.1.0"
DEFAULT_SOURCE_DATE_EPOCH = 946684800  # 2000-01-01T00:00:00Z
MAX_SOURCE_DATE_EPOCH = 4102444800  # 2100-01-01T00:00:00Z
DEFAULT_WORK_DIR = Path("/tmp/skill2workflow-reproducible-build")


def run_reproducible_build(
    repo_root: Path,
    work_dir: Path = DEFAULT_WORK_DIR,
    *,
    source_date_epoch: int = DEFAULT_SOURCE_DATE_EPOCH,
    reset: bool = True,
) -> Dict[str, object]:
    """Build the checkout twice under one fixed, value-free environment."""

    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    _validate_epoch(source_date_epoch)
    if not repo_root.is_dir():
        raise ValueError("repo_root must be a directory")
    if reset:
        _reset_work_dir(repo_root, work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    isolated_dir = work_dir / "isolated"
    build_venv_dir = work_dir / "build-venv"
    first_wheel_dir = work_dir / "build-1"
    second_wheel_dir = work_dir / "build-2"
    isolated_dir.mkdir(parents=True, exist_ok=True)
    first_wheel_dir.mkdir(parents=True, exist_ok=True)
    second_wheel_dir.mkdir(parents=True, exist_ok=True)

    venv.EnvBuilder(with_pip=True, clear=True).create(build_venv_dir)
    build_python = _venv_executable(build_venv_dir, "python")
    _run(
        [
            str(build_python),
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip",
            "setuptools>=77.0.1",
        ],
        cwd=isolated_dir,
    )
    build_command = [
        str(build_python),
        "-m",
        "pip",
        "wheel",
        "--no-deps",
        "--no-build-isolation",
        "--wheel-dir",
    ]
    build_environment = {
        "SOURCE_DATE_EPOCH": str(source_date_epoch),
        "PYTHONHASHSEED": "0",
        "TZ": "UTC",
        "LC_ALL": "C",
        "LANG": "C",
    }
    _run(
        [*build_command, str(first_wheel_dir), str(repo_root)],
        cwd=isolated_dir,
        extra_environment=build_environment,
    )
    _run(
        [*build_command, str(second_wheel_dir), str(repo_root)],
        cwd=isolated_dir,
        extra_environment=build_environment,
    )

    first_wheel = _built_wheel(first_wheel_dir)
    second_wheel = _built_wheel(second_wheel_dir)
    first_bytes = first_wheel.read_bytes()
    second_bytes = second_wheel.read_bytes()
    first_manifest = build_release_manifest(first_wheel)
    second_manifest = build_release_manifest(second_wheel)
    if first_bytes != second_bytes or first_manifest != second_manifest:
        raise RuntimeError("fixed-epoch wheel builds are not reproducible")

    artifact_sha256 = hashlib.sha256(first_bytes).hexdigest()
    created = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    evidence = {
        "schema_version": REPRODUCIBLE_BUILD_SCHEMA_VERSION,
        "created": created,
        "source_date_epoch": source_date_epoch,
        "source_date": datetime.fromtimestamp(
            source_date_epoch, timezone.utc
        ).isoformat().replace("+00:00", "Z"),
        "artifact": {
            "filename": first_wheel.name,
            "size_bytes": len(first_bytes),
            "sha256": artifact_sha256,
        },
        "file_count": len(first_manifest["files"]),
        "builds_compared": 2,
        "builds_equal": True,
        "environment": {
            "python_hash_seed": "0",
            "timezone": "UTC",
            "locale": "C",
        },
    }
    evidence_path = work_dir / "reproducible-build.json"
    write_reproducible_evidence(evidence_path, evidence)
    return {
        "ok": True,
        "work_dir": str(work_dir),
        "evidence_file": str(evidence_path),
        "schema_version": REPRODUCIBLE_BUILD_SCHEMA_VERSION,
        "source_date_epoch": source_date_epoch,
        "artifact_sha256": artifact_sha256,
        "file_count": len(first_manifest["files"]),
        "builds_compared": 2,
        "builds_equal": True,
    }


def write_reproducible_evidence(output: Path, evidence: Dict[str, object]) -> None:
    """Atomically write public reproducibility evidence with mode 0644."""

    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temporary = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{output.name}.", suffix=".tmp", dir=str(output.parent)
        )
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o644)
        os.replace(temporary, output)
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="reproducible_build",
        description="Prove two fixed-epoch wheel builds are byte-identical.",
    )
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--source-date-epoch", type=int, default=DEFAULT_SOURCE_DATE_EPOCH)
    parser.add_argument(
        "--no-reset", action="store_true", help="Keep existing work directory contents."
    )
    parser.add_argument("--format", choices=["text", "json"], default="json")
    args = parser.parse_args(argv)
    try:
        result = run_reproducible_build(
            args.repo_root,
            args.work_dir,
            source_date_epoch=args.source_date_epoch,
            reset=not args.no_reset,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, OverflowError, RuntimeError, ValueError, zipfile.BadZipFile) as error:
        print(str(error), file=sys.stderr)
        return 1


def _run(
    command: Sequence[str],
    *,
    cwd: Path,
    extra_environment: Optional[Dict[str, str]] = None,
) -> str:
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONNOUSERSITE"] = "1"
    if extra_environment:
        environment.update(extra_environment)
    completed = subprocess.run(
        list(command),
        cwd=str(cwd),
        env=environment,
        text=True,
        capture_output=True,
    )
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


def _built_wheel(wheel_dir: Path) -> Path:
    wheels = sorted(Path(wheel_dir).glob("skill2workflow-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(
            f"reproducible build must produce exactly one wheel, found {len(wheels)}"
        )
    return wheels[0]


def _venv_executable(venv_dir: Path, name: str) -> Path:
    scripts_dir = "Scripts" if os.name == "nt" else "bin"
    suffix = ".exe" if os.name == "nt" else ""
    return Path(venv_dir) / scripts_dir / f"{name}{suffix}"


def _validate_epoch(value: int) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > MAX_SOURCE_DATE_EPOCH
    ):
        raise ValueError(
            "source_date_epoch must be an integer between 0 and "
            f"{MAX_SOURCE_DATE_EPOCH}"
        )


def _reset_work_dir(repo_root: Path, work_dir: Path) -> None:
    if work_dir == repo_root or repo_root in work_dir.parents:
        raise ValueError("reproducible build work_dir must be outside the repository")
    if work_dir == Path(work_dir.anchor):
        raise ValueError("reproducible build work_dir cannot be a filesystem root")
    if work_dir.exists():
        shutil.rmtree(work_dir)


if __name__ == "__main__":
    raise SystemExit(main())
