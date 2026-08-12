#!/usr/bin/env python3
"""Exercise the Loop 41 runtime service boundary across a real process restart."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.service import SERVICE_SCHEMA_VERSION


AUTH_TOKEN = "service-boundary-smoke-token-0123456789abcdef"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    work_dir = args.work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    state_dir = work_dir / "state"
    config_path = work_dir / "service.json"
    evidence_path = work_dir / "service-boundary-smoke.json"
    token_file = work_dir / "ingress.token"
    credential_dir = work_dir / "credentials"
    token_file.write_text(AUTH_TOKEN, encoding="utf-8")
    token_file.chmod(0o600)
    credential_dir.mkdir(exist_ok=True)
    credential_dir.chmod(0o700)
    port = _available_port()
    config_path.write_text(
        json.dumps(
            {
                "schema_version": SERVICE_SCHEMA_VERSION,
                "service": {"host": "127.0.0.1", "port": port},
                "runtime": {"state_dir": str(state_dir), "storage": "sqlite"},
                "auth": {
                    "provider": "bearer_token_file",
                    "token_file": str(token_file),
                },
                "credentials": {
                    "provider": "directory",
                    "directory": str(credential_dir),
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    control = LocalControlPlane(state_dir, storage="sqlite")
    control.publish_workflow(_workflow())
    first, first_exit = _service_cycle(config_path, port, "restart-cycle-1")
    persisted_after_first = LocalControlPlane(state_dir, storage="sqlite").get_run(first["run_id"])
    second, second_exit = _service_cycle(config_path, port, "restart-cycle-2")
    reloaded = LocalControlPlane(state_dir, storage="sqlite")
    run_ids = sorted(run["run_id"] for run in reloaded.list_runs())

    evidence = {
        "schema_version": "skill2workflow-service-boundary-evidence-0.1.0",
        "status": "passed",
        "checks": {
            "health": True,
            "readiness": True,
            "graceful_sigterm": first_exit == 0 and second_exit == 0,
            "sqlite_restart_continuity": (
                persisted_after_first["status"] == "completed"
                and first["run_id"] in run_ids
                and second["run_id"] in run_ids
            ),
        },
        "cycles": 2,
        "persisted_run_count": len(run_ids),
    }
    if not all(evidence["checks"].values()):
        evidence["status"] = "failed"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if evidence["status"] == "passed" else 1


def _service_cycle(config_path: Path, port: int, idempotency_key: str):
    environment = dict(os.environ)
    existing_pythonpath = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = str(SRC) + (os.pathsep + existing_pythonpath if existing_pythonpath else "")
    process = subprocess.Popen(
        [sys.executable, "-m", "skill2workflow.cli", "service", "--config", str(config_path)],
        cwd=str(ROOT),
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_until_ready(port, process)
        health = _request_json(f"http://127.0.0.1:{port}/healthz")
        if health.get("status") != "ok":
            raise RuntimeError("health check failed")
        result = _request_json(
            f"http://127.0.0.1:{port}/webhooks/workflow_service_boundary/0.1.0",
            method="POST",
            payload={
                "source": "service-boundary-smoke",
                "idempotency_key": idempotency_key,
            },
        )
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            exit_code = process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
            raise RuntimeError("service did not stop after SIGTERM")
    if exit_code != 0:
        stderr = process.stderr.read().strip() if process.stderr else ""
        raise RuntimeError(f"service exited with {exit_code}: {stderr}")
    return result, exit_code


def _wait_until_ready(port: int, process: subprocess.Popen) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stderr = process.stderr.read().strip() if process.stderr else ""
            raise RuntimeError(f"service stopped before readiness: {stderr}")
        try:
            payload = _request_json(f"http://127.0.0.1:{port}/readyz")
            if payload.get("status") == "ready":
                return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.05)
    raise RuntimeError("service readiness timed out")


def _request_json(url: str, method: str = "GET", payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
        method=method,
    )
    if data is not None:
        request.add_header("Authorization", f"Bearer {AUTH_TOKEN}")
    with urllib.request.urlopen(request, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_service_boundary",
            "name": "Service boundary continuity",
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "end"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [{"id": "edge_start_end", "from": "start", "to": "end", "label": "next"}],
    }


if __name__ == "__main__":
    raise SystemExit(main())
