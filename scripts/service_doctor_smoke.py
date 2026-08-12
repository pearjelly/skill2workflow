#!/usr/bin/env python3
"""Exercise the read-only self-hosted service Doctor through the real CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from skill2workflow.service_bootstrap import initialize_service_workspace


DEFAULT_WORK_DIR = Path("/tmp/skill2workflow-service-doctor-loop53")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run the service Doctor evidence drill.")
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--no-reset", action="store_true")
    args = parser.parse_args(argv)

    repo_root = REPO_ROOT
    work_dir = args.work_dir.resolve()
    _prepare_work_dir(repo_root, work_dir, reset=not args.no_reset)
    port = _available_port()
    workspace = work_dir / "runtime"
    initialized = initialize_service_workspace(workspace, port=port)
    config_file = Path(initialized["config_file"])
    credential_dir = Path(initialized["credential_directory"])
    token_file = Path(initialized["token_file"])
    token_value = token_file.read_text(encoding="utf-8").strip()
    before = _snapshot(workspace)

    ready_process, ready = _run_doctor(repo_root, config_file)
    after_ready = _snapshot(workspace)

    credential_dir.chmod(0o755)
    permission_process, unsafe_permissions = _run_doctor(repo_root, config_file)
    credential_dir.chmod(0o700)

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", port))
    listener.listen(1)
    try:
        busy_process, busy = _run_doctor(repo_root, config_file)
    finally:
        listener.close()

    ready_checks = {item["id"]: item for item in ready["checks"]}
    permission_checks = {item["id"]: item for item in unsafe_permissions["checks"]}
    busy_checks = {item["id"]: item for item in busy["checks"]}
    serialized = "\n".join(
        (ready_process.stdout, permission_process.stdout, busy_process.stdout)
    )
    checks = {
        "ready_exit_zero": ready_process.returncode == 0 and ready["status"] == "ready",
        "fixed_check_set": list(ready_checks) == [
            "config",
            "auth",
            "credentials",
            "state",
            "bind",
        ],
        "workspace_unchanged": before == after_ready,
        "credential_permissions_detected": permission_checks["credentials"] == {
            "id": "credentials",
            "status": "failed",
            "code": "unsafe_permissions",
        },
        "busy_address_detected": busy_checks["bind"] == {
            "id": "bind",
            "status": "failed",
            "code": "address_unavailable",
        },
        "failure_exit_nonzero": permission_process.returncode == 1
        and busy_process.returncode == 1,
        "values_redacted": token_value not in serialized,
    }
    if not all(checks.values()):
        raise RuntimeError("service Doctor evidence checks failed")
    print(
        json.dumps(
            {
                "schema_version": "skill2workflow-service-doctor-evidence-0.1.0",
                "status": "passed",
                "checks": checks,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _run_doctor(repo_root: Path, config_file: Path):
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(repo_root / "src")
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "skill2workflow.cli",
            "service-doctor",
            "--config",
            str(config_file),
        ],
        cwd=repo_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if process.stderr:
        raise RuntimeError("service Doctor wrote unexpected stderr")
    return process, json.loads(process.stdout)


def _snapshot(root: Path):
    result = []
    for path in sorted([root, *root.rglob("*")], key=lambda item: str(item)):
        details = path.lstat()
        digest = ""
        if stat.S_ISREG(details.st_mode):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        result.append(
            (
                str(path.relative_to(root)),
                stat.S_IMODE(details.st_mode),
                details.st_size,
                details.st_mtime_ns,
                digest,
            )
        )
    return result


def _available_port() -> int:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])
    finally:
        listener.close()


def _prepare_work_dir(repo_root: Path, work_dir: Path, *, reset: bool) -> None:
    if work_dir == Path(work_dir.anchor) or work_dir == repo_root or repo_root in work_dir.parents:
        raise ValueError("service Doctor work directory must be outside the repository")
    if work_dir.exists():
        if not reset:
            raise ValueError("service Doctor work directory already exists")
        shutil.rmtree(work_dir)
    work_dir.mkdir(mode=0o700, parents=True)


if __name__ == "__main__":
    raise SystemExit(main())
