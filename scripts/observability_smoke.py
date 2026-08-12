#!/usr/bin/env python3
"""Prove authenticated aggregate metrics and safe operational logs in a real process."""

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
from skill2workflow.telemetry import TELEMETRY_EVENT_SCHEMA_VERSION


AUTH_TOKEN = "observability-smoke-token-0123456789abcdef"
PRIVATE_WORKFLOW_ID = "workflow_observability_private_92841"
PRIVATE_INPUT = "private-customer-observability-value"


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
    port = _available_port()
    config_path = work_dir / "service.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": SERVICE_SCHEMA_VERSION,
                "service": {"host": "127.0.0.1", "port": port},
                "runtime": {"state_dir": str(state_dir), "storage": "sqlite"},
                "auth": {"provider": "bearer_token_file", "token_file": str(token_file)},
                "credentials": {"provider": "directory", "directory": str(credential_dir)},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    LocalControlPlane(state_dir, storage="sqlite").publish_workflow(_workflow())

    process = _start_service(config_path)
    stdout = ""
    stderr = ""
    try:
        _wait_until_ready(port, process)
        denied_status, _ = _metrics(port)
        first_status, first_metrics = _metrics(port, token=AUTH_TOKEN)
        trigger_status = _trigger(port)
        second_status, second_metrics = _metrics(port, token=AUTH_TOKEN)
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate(timeout=5)
            raise RuntimeError("service did not stop after SIGTERM")

    try:
        events = [json.loads(line) for line in stdout.splitlines() if line.strip()]
    except json.JSONDecodeError as error:
        raise RuntimeError("service emitted a non-NDJSON operational log") from error
    private_values = (AUTH_TOKEN, PRIVATE_WORKFLOW_ID, PRIVATE_INPUT, str(state_dir))
    serialized_logs = json.dumps(events, ensure_ascii=False)
    combined_metrics = first_metrics + second_metrics
    label_keys = _metric_label_keys(combined_metrics)
    lifecycle = {
        event.get("status")
        for event in events
        if event.get("event_type") == "service_lifecycle"
    }
    requests = [event for event in events if event.get("event_type") == "http_request_completed"]
    evidence = {
        "schema_version": "skill2workflow-observability-evidence-0.1.0",
        "status": "passed",
        "checks": {
            "unauthenticated_metrics_denied": denied_status == 401,
            "authenticated_metrics_exported": first_status == 200 and second_status == 200,
            "aggregate_state_visible": (
                trigger_status == 200
                and 'skill2workflow_workflows{status="published"} 1' in second_metrics
                and 'skill2workflow_runs{status="completed"} 1' in second_metrics
                and 'skill2workflow_http_requests_total{route="workflow_trigger",status_class="2xx"} 1'
                in second_metrics
            ),
            "low_cardinality_labels": label_keys <= {"status", "route", "status_class"},
            "private_values_absent": all(
                value not in combined_metrics and value not in serialized_logs
                for value in private_values
            ),
            "structured_lifecycle_logs": (
                process.returncode == 0
                and not stderr.strip()
                and lifecycle >= {"starting", "ready", "draining", "stopped"}
                and bool(requests)
                and all(
                    event.get("schema_version") == TELEMETRY_EVENT_SCHEMA_VERSION
                    for event in events
                )
            ),
        },
        "metric_label_key_count": len(label_keys),
        "operational_event_count": len(events),
    }
    if not all(evidence["checks"].values()):
        evidence["status"] = "failed"
    (work_dir / "observability-smoke.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if evidence["status"] == "passed" else 1


def _start_service(config_path: Path):
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(SRC) + (
        os.pathsep + environment["PYTHONPATH"] if environment.get("PYTHONPATH") else ""
    )
    return subprocess.Popen(
        [sys.executable, "-m", "skill2workflow.cli", "service", "--config", str(config_path)],
        cwd=str(ROOT),
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _wait_until_ready(port: int, process) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("service stopped before readiness")
        try:
            request = urllib.request.Request(f"http://127.0.0.1:{port}/readyz", method="GET")
            with urllib.request.urlopen(request, timeout=2) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.05)
    raise RuntimeError("service readiness timed out")


def _metrics(port: int, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/metrics", headers=headers, method="GET"
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        try:
            return error.code, error.read().decode("utf-8")
        finally:
            error.close()


def _trigger(port: int) -> int:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/webhooks/{PRIVATE_WORKFLOW_ID}/0.1.0",
        data=json.dumps(
            {
                "idempotency_key": "observability-smoke-run",
                "input": {"customer": PRIVATE_INPUT},
            }
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            response.read()
            return response.status
    except urllib.error.HTTPError as error:
        try:
            error.read()
            return error.code
        finally:
            error.close()


def _metric_label_keys(metrics: str):
    keys = set()
    for line in metrics.splitlines():
        if line.startswith("#") or "{" not in line:
            continue
        labels = line.split("{", 1)[1].split("}", 1)[0]
        for item in labels.split(","):
            if "=" in item:
                keys.add(item.split("=", 1)[0])
    return keys


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": PRIVATE_WORKFLOW_ID,
            "name": "Private observability fixture",
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
