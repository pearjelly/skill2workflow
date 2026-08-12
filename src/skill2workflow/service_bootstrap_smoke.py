"""Run the secure service-bootstrap real-process evidence drill."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict

from .service import load_service_config


def run_service_bootstrap_smoke(
    repo_root: Path, work_dir: Path, reset: bool = True
) -> Dict[str, object]:
    repo_root = Path(repo_root).resolve()
    work_dir = Path(work_dir).resolve()
    if reset:
        _reset_work_dir(repo_root, work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    workspace = work_dir / "service"
    port = _available_port()
    environment = os.environ.copy()
    source = str(repo_root / "src")
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = source if not existing else source + os.pathsep + existing
    initialize = subprocess.run(
        [
            sys.executable,
            "-m",
            "skill2workflow.cli",
            "service-init",
            "--root",
            str(workspace),
            "--port",
            str(port),
        ],
        cwd=str(repo_root),
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if initialize.returncode != 0:
        raise RuntimeError("service bootstrap initialization failed")
    summary = json.loads(initialize.stdout)
    config_path = Path(str(summary["config_file"]))
    secret_path = Path(str(summary["token_file"]))
    secret = secret_path.read_text(encoding="utf-8").strip()
    config = load_service_config(config_path)
    output_redacted = secret not in initialize.stdout and secret not in initialize.stderr
    owner_only = _owner_only(config_path) and _owner_only(secret_path)
    owner_only = owner_only and all(
        _owner_only(path)
        for path in (
            workspace,
            workspace / "config",
            workspace / "state",
            workspace / "secrets",
            workspace / "secrets" / "connectors",
        )
    )

    repeat = subprocess.run(
        [
            sys.executable,
            "-m",
            "skill2workflow.cli",
            "service-init",
            "--root",
            str(workspace),
            "--port",
            str(port),
        ],
        cwd=str(repo_root),
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    no_overwrite = (
        repeat.returncode == 1
        and repeat.stdout == ""
        and secret_path.read_text(encoding="utf-8").strip() == secret
    )

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "skill2workflow.cli",
            "service",
            "--config",
            str(config_path),
        ],
        cwd=str(repo_root),
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    graceful_exit = False
    try:
        ready = _wait_ready(port, process)
        unauthorized = _status(f"http://127.0.0.1:{port}/metrics") == 401
        metrics_status, metrics = _authenticated_metrics(port, secret)
        authenticated_metrics = (
            metrics_status == 200 and "skill2workflow_service_ready 1" in metrics
        )
        process.send_signal(signal.SIGTERM)
        graceful_exit = process.wait(timeout=10) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()

    state_initialized = (
        (config.state_dir / "state-layout.json").is_file()
        and (config.state_dir / "runs.sqlite3").is_file()
        and (config.state_dir / "control.sqlite3").is_file()
        and (config.state_dir / "scheduler.sqlite3").is_file()
    )
    checks = {
        "workspace_initialized": summary.get("status") == "initialized",
        "bootstrap_output_redacted": output_redacted,
        "owner_only_permissions": owner_only,
        "configuration_valid": config.port == port,
        "existing_workspace_preserved": no_overwrite,
        "service_ready": ready,
        "unauthenticated_metrics_denied": unauthorized,
        "authenticated_metrics_available": authenticated_metrics,
        "graceful_exit": graceful_exit,
        "durable_state_initialized": state_initialized,
    }
    if not all(checks.values()):
        raise RuntimeError("service bootstrap evidence checks failed")
    return {
        "schema_version": "skill2workflow-service-bootstrap-evidence-0.1.0",
        "status": "passed",
        "checks": checks,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the secure service-bootstrap real-process drill."
    )
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--no-reset", action="store_true")
    args = parser.parse_args(argv)
    result = run_service_bootstrap_smoke(
        args.repo_root, args.work_dir, reset=not args.no_reset
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _wait_ready(port: int, process: subprocess.Popen) -> bool:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        if _status(f"http://127.0.0.1:{port}/readyz") == 200:
            return True
        time.sleep(0.05)
    return False


def _status(url: str) -> int:
    try:
        with urllib.request.urlopen(url, timeout=0.5) as response:
            return int(response.status)
    except urllib.error.HTTPError as error:
        try:
            return int(error.code)
        finally:
            error.close()
    except (OSError, urllib.error.URLError):
        return 0


def _authenticated_metrics(port: int, secret: str):
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/metrics",
        headers={"Authorization": f"Bearer {secret}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=1) as response:
            return int(response.status), response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        try:
            return int(error.code), ""
        finally:
            error.close()


def _available_port() -> int:
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        return int(server.getsockname()[1])


def _owner_only(path: Path) -> bool:
    if os.name == "nt":
        return True
    return stat.S_IMODE(path.stat().st_mode) & 0o077 == 0


def _reset_work_dir(repo_root: Path, work_dir: Path) -> None:
    if work_dir == repo_root or repo_root in work_dir.parents:
        raise ValueError("service bootstrap smoke work_dir must be outside repository")
    if work_dir == Path(work_dir.anchor):
        raise ValueError("service bootstrap smoke work_dir cannot be a filesystem root")
    if work_dir.exists():
        shutil.rmtree(work_dir)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
