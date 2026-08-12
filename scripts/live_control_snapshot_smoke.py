#!/usr/bin/env python3
"""Prove the authenticated bounded live Operator snapshot across real processes."""

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
from skill2workflow.dashboard import SNAPSHOT_SCHEMA_VERSION
from skill2workflow.service import SERVICE_SCHEMA_VERSION


AUTH_TOKEN = "live-snapshot-smoke-token-0123456789abcdef"
PRIVATE_WORKFLOW_ID = "workflow_private_live_snapshot_73921"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    work_dir = args.work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    state_dir = work_dir / "state"
    credential_dir = work_dir / "credentials"
    credential_dir.mkdir(exist_ok=True)
    credential_dir.chmod(0o700)
    token_file = work_dir / "ingress.token"
    token_file.write_text(AUTH_TOKEN, encoding="utf-8")
    token_file.chmod(0o600)
    snapshot_file = work_dir / "live-snapshot.json"
    port = _available_port()
    config_path = work_dir / "service.json"
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
            indent=2,
        ),
        encoding="utf-8",
    )
    control = LocalControlPlane(state_dir, storage="sqlite")
    control.publish_workflow(_workflow())
    control.run_published_workflow(PRIVATE_WORKFLOW_ID, "0.1.0")
    audit_count_before = len(control.list_audit_events())

    process = _start_service(config_path)
    stdout = stderr = ""
    try:
        _wait_until_ready(port, process)
        denied_status, _ = _request(
            f"http://127.0.0.1:{port}/api/v1/control-snapshot"
        )
        client = subprocess.run(
            [
                sys.executable,
                "-m",
                "skill2workflow.cli",
                "control-snapshot",
                "--service-url",
                f"http://127.0.0.1:{port}",
                "--auth-token-file",
                str(token_file),
                "--output",
                str(snapshot_file),
            ],
            cwd=str(ROOT),
            env=_environment(),
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        snapshot = json.loads(snapshot_file.read_text(encoding="utf-8"))
        metrics_status, metrics = _request(
            f"http://127.0.0.1:{port}/metrics",
            token=AUTH_TOKEN,
        )
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate(timeout=5)
            raise RuntimeError("service did not stop after SIGTERM")

    audit_count_after = len(
        LocalControlPlane(state_dir, storage="sqlite").list_audit_events()
    )
    events = [json.loads(line) for line in stdout.splitlines() if line.strip()]
    snapshot_requests = [
        event
        for event in events
        if event.get("event_type") == "http_request_completed"
        and event.get("route") == "control_snapshot"
    ]
    evidence = {
        "schema_version": "skill2workflow-live-control-snapshot-evidence-0.1.0",
        "status": "passed",
        "checks": {
            "unauthenticated_denied": denied_status == 401,
            "authenticated_cli_fetch": client.returncode == 0 and not client.stdout,
            "bounded_contract": (
                snapshot.get("schema_version") == SNAPSHOT_SCHEMA_VERSION
                and snapshot.get("window", {}).get("max_items") == 100
                and snapshot.get("summary", {}).get("workflow_count") == 1
            ),
            "persisted_state_unchanged": audit_count_after == audit_count_before,
            "owner_only_output": snapshot_file.stat().st_mode & 0o777 == 0o600,
            "fixed_observability": (
                metrics_status == 200
                and 'route="control_snapshot",status_class="2xx"} 1' in metrics
                and 'route="control_snapshot",status_class="4xx"} 1' in metrics
                and {event.get("status_class") for event in snapshot_requests}
                == {"2xx", "4xx"}
            ),
            "private_values_absent_from_operations": (
                AUTH_TOKEN not in stdout
                and PRIVATE_WORKFLOW_ID not in stdout
                and AUTH_TOKEN not in stderr
                and PRIVATE_WORKFLOW_ID not in stderr
            ),
            "graceful_exit": process.returncode == 0 and not stderr.strip(),
        },
        "snapshot_collection_count": 5,
        "operational_snapshot_request_count": len(snapshot_requests),
    }
    if not all(evidence["checks"].values()):
        evidence["status"] = "failed"
    (work_dir / "live-control-snapshot-smoke.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if evidence["status"] == "passed" else 1


def _start_service(config_path: Path):
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "skill2workflow.cli",
            "service",
            "--config",
            str(config_path),
        ],
        cwd=str(ROOT),
        env=_environment(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _environment():
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(SRC) + (
        os.pathsep + environment["PYTHONPATH"]
        if environment.get("PYTHONPATH")
        else ""
    )
    return environment


def _wait_until_ready(port: int, process) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("service stopped before readiness")
        status, payload = _request(f"http://127.0.0.1:{port}/readyz")
        if status == 200 and json.loads(payload).get("status") == "ready":
            return
        time.sleep(0.05)
    raise RuntimeError("service readiness timed out")


def _request(url: str, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        try:
            return error.code, error.read().decode("utf-8")
        finally:
            error.close()
    except urllib.error.URLError:
        return 0, ""


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": PRIVATE_WORKFLOW_ID,
            "name": "Private live snapshot workflow",
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "title": "Start", "on_success": "end"},
            {"id": "end", "type": "end", "title": "End"},
        ],
        "edges": [
            {"id": "edge_start_end", "from": "start", "to": "end", "label": "next"}
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
