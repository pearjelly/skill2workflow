#!/usr/bin/env python3
"""Exercise durable cooperative cancellation against a real service process."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from contextlib import closing
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from skill2workflow.control_plane import LocalControlPlane
from skill2workflow.retention import apply_state_retention
from skill2workflow.service import SERVICE_SCHEMA_VERSION


AUTH_TOKEN = "cancellation-smoke-bearer-token-0123456789abcdef"
PRIVATE_SENTINEL = "private-cancellation-smoke-value-48392"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    work_dir = args.work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    state_dir = work_dir / "state"
    token_file = work_dir / "ingress.token"
    credential_dir = work_dir / "credentials"
    config_path = work_dir / "service.json"
    evidence_path = work_dir / "cancellation-smoke.json"
    token_file.write_text(AUTH_TOKEN, encoding="utf-8")
    token_file.chmod(0o600)
    credential_dir.mkdir(exist_ok=True)
    credential_dir.chmod(0o700)

    provider_started = threading.Event()
    provider_release = threading.Event()
    provider = HTTPServer(
        ("127.0.0.1", 0),
        _provider_handler(provider_started, provider_release),
    )
    provider_thread = threading.Thread(target=provider.serve_forever, daemon=True)
    provider_thread.start()
    provider_port = int(provider.server_address[1])

    control = LocalControlPlane(state_dir, storage="sqlite")
    control.publish_workflow(_connector_workflow(provider_port))
    control.publish_workflow(_waiting_workflow())
    service_port = _available_port()
    config_path.write_text(
        json.dumps(
            {
                "schema_version": SERVICE_SCHEMA_VERSION,
                "service": {"host": "127.0.0.1", "port": service_port},
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

    process = _start_service(config_path)
    trigger_result = {}
    trigger_thread = None
    try:
        _wait_until_ready(service_port, process)
        trigger_thread = threading.Thread(
            target=lambda: trigger_result.update(
                _request_json(
                    f"http://127.0.0.1:{service_port}/webhooks/workflow_cancel_running/0.1.0",
                    method="POST",
                    payload={
                        "source": "cancellation-smoke",
                        "idempotency_key": "running-cancel",
                        "input": {"private": PRIVATE_SENTINEL},
                    },
                    token=AUTH_TOKEN,
                )[1]
            ),
            daemon=True,
        )
        trigger_thread.start()
        if not provider_started.wait(timeout=3):
            raise RuntimeError("provider request did not start")
        run_id = _only_running_run(state_dir)
        denied_status, _ = _request_json(
            f"http://127.0.0.1:{service_port}/runs/{run_id}/cancel",
            method="POST",
            payload={},
        )
        cancel_status, cancel_result = _request_json(
            f"http://127.0.0.1:{service_port}/runs/{run_id}/cancel",
            method="POST",
            payload={},
            token=AUTH_TOKEN,
        )
        provider_release.set()
        trigger_thread.join(timeout=5)
        if trigger_thread.is_alive():
            raise RuntimeError("trigger did not finish after provider release")

        waiting_status, waiting_result = _request_json(
            f"http://127.0.0.1:{service_port}/webhooks/workflow_cancel_waiting/0.1.0",
            method="POST",
            payload={"source": "cancellation-smoke", "idempotency_key": "waiting"},
            token=AUTH_TOKEN,
        )
        waiting_run_id = str(waiting_result["run_id"])
        first_waiting_cancel = _request_json(
            f"http://127.0.0.1:{service_port}/runs/{waiting_run_id}/cancel",
            method="POST",
            payload={},
            token=AUTH_TOKEN,
        )
        second_waiting_cancel = _request_json(
            f"http://127.0.0.1:{service_port}/runs/{waiting_run_id}/cancel",
            method="POST",
            payload={},
            token=AUTH_TOKEN,
        )
    finally:
        provider_release.set()
        _stop_service(process)
        provider.shutdown()
        provider.server_close()
        provider_thread.join(timeout=3)

    restarted = _start_service(config_path)
    try:
        _wait_until_ready(service_port, restarted)
    finally:
        _stop_service(restarted)

    reloaded = LocalControlPlane(state_dir, storage="sqlite")
    running_state = reloaded.get_run(str(trigger_result["run_id"]))
    waiting_state = reloaded.get_run(waiting_run_id)
    audit = reloaded.list_audit_events()
    cancellation_audit = [
        event
        for event in audit
        if event.get("type") in {"run_cancel_requested", "run_cancelled"}
    ]
    serialized_audit = json.dumps(audit, ensure_ascii=False)
    serialized_cancellation_audit = json.dumps(cancellation_audit, ensure_ascii=False)
    running_events = [
        str(event.get("type", ""))
        for event in running_state.get("events", [])
        if isinstance(event, dict)
    ]
    with closing(sqlite3.connect(state_dir / "runs.sqlite3")) as connection:
        connection.execute(
            "update runs set updated_at = '2025-01-01 00:00:00' where run_id = ?",
            (running_state["run_id"],),
        )
        connection.commit()
    retained_dir = work_dir / "retained"
    retention = apply_state_retention(
        state_dir,
        retained_dir,
        {
            "schema_version": "skill2workflow-retention-policy-0.2.0",
            "retention": {
                "delete_before": "2026-01-01T00:00:00Z",
                "terminal_run_statuses": ["completed", "failed", "cancelled"],
                "terminal_dispatch_statuses": [
                    "completed",
                    "failed",
                    "skipped",
                    "uncertain",
                ],
            },
        },
    )
    with closing(sqlite3.connect(retained_dir / "runs.sqlite3")) as connection:
        retained_running_count = int(
            connection.execute(
                "select count(*) from runs where run_id = ?",
                (running_state["run_id"],),
            ).fetchone()[0]
        )
    with closing(sqlite3.connect(state_dir / "runs.sqlite3")) as connection:
        source_running_count = int(
            connection.execute(
                "select count(*) from runs where run_id = ?",
                (running_state["run_id"],),
            ).fetchone()[0]
        )
    evidence = {
        "schema_version": "skill2workflow-cancellation-evidence-0.1.0",
        "status": "passed",
        "checks": {
            "unauthenticated_denied": denied_status == 401,
            "concurrent_request_persisted": (
                cancel_status == 200
                and cancel_result.get("status") == "cancel_requested"
            ),
            "external_attempt_recorded": "connector_completed" in running_events,
            "successor_suppressed": (
                running_state.get("status") == "cancelled"
                and "end" not in running_state.get("node_results", {})
            ),
            "waiting_cancel_immediate": (
                waiting_status == 200
                and first_waiting_cancel[1].get("status") == "cancelled"
                and waiting_state.get("status") == "cancelled"
            ),
            "idempotent": second_waiting_cancel[1].get("status") == "cancelled",
            "restart_durable": (
                running_state.get("status") == "cancelled"
                and waiting_state.get("status") == "cancelled"
                and restarted.returncode == 0
            ),
            "compact_audit": (
                PRIVATE_SENTINEL not in serialized_audit
                and "reason" not in serialized_cancellation_audit
            ),
            "retention_v2_compatible": (
                retention.get("deleted_terminal_runs") == 1
                and retention.get("deleted_run_cancellations") == 1
                and retained_running_count == 0
                and source_running_count == 1
            ),
            "graceful_exit": process.returncode == 0,
        },
        "cancelled_run_count": sum(
            run.get("status") == "cancelled" for run in reloaded.list_runs()
        ),
        "cancellation_audit_count": len(cancellation_audit),
    }
    if not all(evidence["checks"].values()):
        evidence["status"] = "failed"
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))
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
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


def _stop_service(process) -> None:
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


def _wait_until_ready(port: int, process) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stderr = process.stderr.read().strip() if process.stderr else ""
            raise RuntimeError(f"service stopped before readiness: {stderr}")
        try:
            status, payload = _request_json(f"http://127.0.0.1:{port}/readyz")
            if status == 200 and payload.get("status") == "ready":
                return
        except OSError:
            pass
        time.sleep(0.05)
    raise RuntimeError("service readiness timed out")


def _request_json(url: str, method="GET", payload=None, token=""):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=6) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read().decode("utf-8"))
        finally:
            error.close()


def _only_running_run(state_dir: Path) -> str:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        running = [
            run for run in LocalControlPlane(state_dir, storage="sqlite").list_runs()
            if run.get("status") == "running"
        ]
        if len(running) == 1:
            return str(running[0]["run_id"])
        time.sleep(0.02)
    raise RuntimeError("running workflow was not visible")


def _provider_handler(started, release):
    class ProviderHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            self.rfile.read(length)
            started.set()
            if not release.wait(timeout=5):
                self.send_response(504)
                self.end_headers()
                return
            body = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format, *_args):
            return

    return ProviderHandler


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _connector_workflow(provider_port: int):
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_cancel_running",
            "name": "Running cancellation smoke",
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "on_success": "call"},
            {
                "id": "call",
                "type": "tool_call",
                "connector": {
                    "id": "http",
                    "kind": "http",
                    "request": {
                        "method": "POST",
                        "url": f"http://127.0.0.1:{provider_port}/slow",
                        "body": {"private": PRIVATE_SENTINEL},
                        "timeout_ms": 5000,
                    },
                },
                "on_success": "end",
                "on_failure": "failure",
            },
            {"id": "failure", "type": "failure"},
            {"id": "end", "type": "end"},
        ],
        "edges": [
            {"id": "edge_start_call", "from": "start", "to": "call", "label": "next"},
            {"id": "edge_call_end", "from": "call", "to": "end", "label": "success"},
            {"id": "edge_call_failure", "from": "call", "to": "failure", "label": "failure"},
        ],
    }


def _waiting_workflow():
    return {
        "schema_version": "0.1.0",
        "workflow": {
            "id": "workflow_cancel_waiting",
            "name": "Waiting cancellation smoke",
            "version": "0.1.0",
            "status": "draft",
        },
        "entry": "start",
        "nodes": [
            {"id": "start", "type": "start", "on_success": "review"},
            {
                "id": "review",
                "type": "human_gate",
                "connector": {"id": "manual", "kind": "manual"},
                "on_success": "end",
                "on_failure": "failure",
            },
            {"id": "failure", "type": "failure"},
            {"id": "end", "type": "end"},
        ],
        "edges": [
            {"id": "edge_start_review", "from": "start", "to": "review", "label": "next"},
            {"id": "edge_review_end", "from": "review", "to": "end", "label": "approved"},
            {"id": "edge_review_failure", "from": "review", "to": "failure", "label": "rejected"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
